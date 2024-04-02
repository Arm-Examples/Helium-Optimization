#!/usr/bin/python
# -*- coding: utf-8 -*-

# * ----------------------------------------------------------------------
# * Project:      arm tiny tarmac profiling tool
# * Title:        arm_tarmac_profiler.py
# * Description:  Extract timeline (flame-graph) from a given tarmac trace
# *               per-function statistics generation
#                 Can be used in complement of the tarmac trace utilities
#                 https://community.arm.com/arm-community-blogs/b/tools-software-ides-blog/posts/tarmac-trace-utilities
#                 https://github.com/ARM-software/tarmac-trace-utilities
# *
# * $Date:        20 Mar 2024
# *
# * $Revision:    V1.0.0
# *
# * Target Processor: Cortex-M and Cortex-A cores
# * -------------------------------------------------------------------- */
# /*
# * Copyright (C) 2010-2024 ARM Limited or its affiliates. All rights reserved.
# *
# * SPDX-License-Identifier: Apache-2.0
# *
# * Licensed under the Apache License, Version 2.0 (the License); you may
# * not use this file except in compliance with the License.
# * You may obtain a copy of the License at
# *
# * www.apache.org/licenses/LICENSE-2.0
# *
# * Unless required by applicable law or agreed to in writing, software
# * distributed under the License is distributed on an AS IS BASIS, WITHOUT
# * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# * See the License for the specific language governing permissions and
# * limitations under the License.
# */

import sys
import re
import os
import signal
from collections import defaultdict

# globals
abort = False
verbose = False
coverageDetails = False

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Regexp's
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# fromelf -s output parser (text section with and without size reporting)
fromelfRe = re.compile(
    ".*\s+[0-9]+\s+(.*)\s(0x[0-9a-fA-F]+)\s+.*Code\s+.*(0x[0-9a-fA-F]+)"
)
fromelfReNoSize = re.compile(".*\s+[0-9]+\s+(.*)\s(0x[0-9a-fA-F]+)\s+.*Code\s+.*")

# multi-line fromelf entries regexp
# GCC could insert .constprop naming
fromelfPartial1Re = re.compile(r"\s+[0-9]+\s+([a-zA-Z0-9_\.]+)\s*$")
fromelfPartial2Re = re.compile(r"\s+(0x[0-9a-fA-F]+)\s+.*Code\s+.*(0x[0-9a-fA-F]+)")

# MDK ETM CSV trace
parseMdkEtmRe = re.compile('"[0-9a-fA-F]+","(.*)",X : 0x([0-9a-fA-F]+),.*,"(.*)"')

# FVP/VHT/IPSS
parseFVPRe = re.compile(
    "([0-9]+)\s+ps.*IT\s+\(.*\)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+T\s+(thread|hdlr).*\s+(.*)"
)

# discard functions starting with $
exp = re.compile("\$.*")

MemLDmatch = re.compile("^\s+LD\s+.*")
MemSTmatch = re.compile("^\s+ST\s+.*")

MemSTmatchEx = r"(?P<time>[0-9]+)\s+(clk|ps)\s+MW4\s+(?P<addr>[0-9a-fA-F]+)\s+(?P<val>[0-9a-fA-F]+)"
MemLDmatchEx = r"(?P<time>[0-9]+)\s+(clk|ps)\s+MR4\s+(?P<addr>[0-9a-fA-F]+)\s+(?P<val>[0-9a-fA-F]+)"

vecLDRe = re.compile(".*cc\-\-.*VLD.*")
vecSTRe = re.compile(".*cc\-\-.*VST.*")
sclLDRe = re.compile(".*\:\s+V?LD.*")
sclSTRe = re.compile(".*\:\s+V?ST.*")
pushRe = re.compile(".*\:\s+V?PUSH.*")
popRe = re.compile(".*\:\s+V?POP.*")

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# functions
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def printf(formatStr, *args):
    sys.stdout.write(formatStr % args)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# progress bar
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def update_progress(progress, total=100):
    # return
    sys.stdout.write(
        "\r[{0:10}]{1:>2}%".format("#" * int(progress * 10 / total), progress)
    )
    sys.stdout.flush()


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# CTRL C handler
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def keyAbort(signum, frame):
    global abort
    printf("Aborting !!\n\n")
    abort = True


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# usage message
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def usage():

    printf(
        """
\033[4musage\033[0m : \033[31;1m armProfiler.py\033[00m image.sym pipe.log out.[json|csv]
"""
    )
    printf(" where : \n")
    printf(" image.sym          : image symbols (fromelf -s)\n")
    printf(" pipe.log           : pipeline model output\n")
    printf(" out.[json|csv]     : processed csv or json trace output\n")
    exit(2)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# entry
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def main(argv):
    global abort
    global verbose
    # trace format discovery
    parsePipeTraceReFound = False
    parsePipeTraceRe = [parseMdkEtmRe, parseFVPRe]
    PipeTraceStr = ["MDK ETM", "IpssFVP"]
    pipeTraceScal = [1.0 / 10000000.0, 10000]

    parsePipeTraceReIdx = 0
    parsePipeTraceReMax = len(pipeTraceScal)
    parsePipeTraceReUnknown = 0
    timeScale = 1000

    T32_INST_MIN_SIZE = 2
    partialFromelfEntry = ""

    printf("ARM profiler\n")

    if len(sys.argv) != 4:
        usage()

    try:
        axfImage = open(sys.argv[1], "r")
    except IOError:
        printf("Cannot open symbol file\n")
        sys.exit(2)

    pcLog = sys.argv[2]

    if "json" in sys.argv[3]:
        outTyp = "json"
    else:
        outTyp = "csv"

    try:
        outFile = open(sys.argv[3], "w")
    except IOError:
        printf("Cannot open output file\n")
        sys.exit(2)

    if outTyp == "json":
        outFile.write("[\n")

    # intercept CTRL + C to perform graceful exit
    signal.signal(signal.SIGINT, keyAbort)

    codecov_dict = {}
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # parse symbol table
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    symbArray = []
    symArr = []
    nbSym = 0
    for line in axfImage:
        current_entry = line.rstrip("\n")

        # handle multi-line fromelf output
        if partialFromelfEntry != "":
            m = fromelfPartial2Re.match(current_entry)
            if m:
                base = m.group(1)
                size = m.group(2)
                sym = partialFromelfEntry

                symbArray.append((int(base, 16), int(size, 16), sym, set()))
                symArr.append(sym)
                codecov_dict[sym.strip()] = (defaultdict(int), int(size, 16), set())
                nbSym += 1
                partialFromelfEntry = ""
                continue

        m = fromelfRe.match(current_entry)
        if m:
            base = m.group(2)
            size = m.group(3)
            sym = m.group(1)

            symbArray.append((int(base, 16), int(size, 16), sym, set()))
            symArr.append(sym)
            codecov_dict[sym.strip()] = (defaultdict(int), int(size, 16), set())
            nbSym += 1

        else:
            # multi-line fromelf output
            m = fromelfPartial1Re.match(current_entry)
            if m:
                partialFromelfEntry = m.group(1)
                continue

            m = fromelfReNoSize.match(current_entry)
            if m:
                base = m.group(2)
                size = T32_INST_MIN_SIZE
                sym = m.group(1)

                symbArray.append((int(base, 16), 2, sym, set()))
                symArr.append(sym)
                codecov_dict[sym.strip()] = (defaultdict(int), T32_INST_MIN_SIZE, set())
                nbSym += 1
                continue

    emptyList = [0] * nbSym
    funcTrack = dict(zip(symArr, emptyList))
    if outTyp == "csv":
        # extended memory statistics structure when csv output is selected
        funcIOReadTrack = dict(zip(symArr, emptyList))
        funcIOWriteTrack = dict(zip(symArr, emptyList))
        funcLDTrack = dict(zip(symArr, emptyList))
        funcSTTrack = dict(zip(symArr, emptyList))
        funcInstrCntTrack = dict(zip(symArr, emptyList))
        funcVecLDTrack = dict(zip(symArr, emptyList))
        funcVecSTTrack = dict(zip(symArr, emptyList))
        funcSclLDTrack = dict(zip(symArr, emptyList))
        funcSclSTTrack = dict(zip(symArr, emptyList))
        IFetchTrack = dict(zip(symArr, emptyList))

        outFile.write(
            "function, start time, duration, instructions count, DTCM LD, DTCM ST, Vec LD count, Vec ST count, Sc LD count, Sc ST count, I Fetch Count, IO Read, IO Write\n"
        )
        if (
            PipeTraceStr[parsePipeTraceReIdx] == "PipeMod"
            or PipeTraceStr[parsePipeTraceReIdx] == "basic"
        ):
            printf("/!\ statistics are not reliable on SW model\n")

    pcLogFile = open(pcLog, "r")

    count = sum(1 for line in open(pcLog))
    printf("Process %d instructions\n", count)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # track function coverage
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    prevSym = ""
    limitHit = 0
    pcCount = 0
    nextPercStep = 0
    pcPrev = 0
    clock = 0
    stack = []
    prevSymb = (0, 0, None, set())

    for item in pcLogFile:
        if limitHit:
            update_progress(100)
            printf("\n")
            break

        if abort:
            printf("Abort after %0.1f %%\n", curPerc)
            break

        curPerc = int(pcCount / float(count) * 100.0)
        pcCount += 1

        # progress bar
        if curPerc >= nextPercStep:
            update_progress(curPerc)
            nextPercStep += 1

        # trace format discovery
        if not parsePipeTraceReFound:
            while parsePipeTraceReIdx < parsePipeTraceReMax:
                m = parsePipeTraceRe[parsePipeTraceReIdx].match(item)
                if not m:
                    parsePipeTraceReIdx += 1
                    continue
                else:
                    parsePipeTraceReFound = True
                    timeScale = pipeTraceScal[parsePipeTraceReIdx]
                    if verbose:
                        printf(
                            "found trace format %s scale %d\n",
                            PipeTraceStr[parsePipeTraceReIdx],
                            timeScale,
                        )
                    break

            if parsePipeTraceReIdx == parsePipeTraceReMax:
                parsePipeTraceReIdx = 0
                parsePipeTraceReUnknown += 1
                if parsePipeTraceReUnknown == 100:
                    printf("unknown format, giving up... \n")
                continue

        m = parsePipeTraceRe[parsePipeTraceReIdx].match(item)
        if m:
            clock = float(m.group(1))
            pc = int(m.group(2), 16)
            instr = m.group(3)

            dbg_mrkr = " ".join(re.split("\s+", item)[-3:])

            if "DBG" in item:
                if outTyp == "json":
                    outFile.write(
                        '{"cat": "dbg", "pid": 1, "ts": %d, "ph": "I", "s": "p",  "name": "%s", "args": {}},\n'
                        % (clock / timeScale, dbg_mrkr)
                    )
                else:
                    outFile.write("//  <- %s -> //\n" % (dbg_mrkr))

            for symb in [prevSymb] + symbArray:
                # for symb in symbArray:
                (base, size, sym, myset) = symb

                base = base & 0xFFFFFFFE

                if pc >= base and pc < base + size - 1 and not re.search(exp, sym):
                    offset = pc - base
                    prevSymb = symb
                    codecov_dict[sym.strip()][0][hex(pc)] += 1
                    codecov_dict[sym.strip()][2].add((hex(pc), len(instr) / 2))

                    # function start (relative offset = 0)
                    if offset < 2:
                        # function start detection (PC offset = 0)
                        funcTrack[sym] = clock
                        if outTyp == "csv":
                            funcIOReadTrack[sym] = 0
                            funcIOWriteTrack[sym] = 0

                            # outFile.write('// !! IO clear %s//\n' % (sym))
                            funcLDTrack[sym] = 0
                            funcSTTrack[sym] = 0
                            funcInstrCntTrack[sym] = 0
                            funcVecSTTrack[sym] = 0
                            funcVecLDTrack[sym] = 0
                            funcSclSTTrack[sym] = 0
                            funcSclLDTrack[sym] = 0
                            IFetchTrack[sym] = 0

                    # skip 2nd beat
                    if outTyp == "csv":
                        if "[--cc]" not in item:
                            funcInstrCntTrack[sym] += 1

                        # track I fetch
                        # ignore 2nd pair of 2 consecutive T16 fetch
                        if pc & 0xFFFFFFFC != pcPrev & 0xFFFFFFFC:
                            IFetchTrack[sym] += 1

                    if sym != prevSym:
                        if verbose:
                            printf("%% %s %%\n", sym)
                        if sym in stack:
                            while True:
                                item = stack.pop()

                                if item == sym:
                                    break

                                prevSym = item
                                if verbose:
                                    printf("%s is returning\n", prevSym)

                                if funcTrack[prevSym] == 0:
                                    # force 0 (2 consecutive ret)
                                    diff = 0
                                else:
                                    diff = clock - funcTrack[prevSym]

                                    if outTyp == "json":
                                        outFile.write(
                                            '{"name": "%s", "cat": "arm", "ph": "X", "ts": %.10f, "dur": %.10f, "pid": %d, "tid": %d,  "args": {}},\n'
                                            % (
                                                prevSym,
                                                funcTrack[prevSym] / timeScale,
                                                diff / timeScale,
                                                1,
                                                1,
                                            )
                                        )
                                    else:
                                        outFile.write(
                                            "%s, %f, %f, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d\n"
                                            % (
                                                prevSym.strip(),
                                                funcTrack[prevSym] / timeScale,
                                                diff / timeScale,
                                                funcInstrCntTrack[prevSym],
                                                funcLDTrack[prevSym],
                                                funcSTTrack[prevSym],
                                                funcVecLDTrack[prevSym],
                                                funcVecSTTrack[prevSym],
                                                funcSclLDTrack[prevSym],
                                                funcSclSTTrack[prevSym],
                                                IFetchTrack[prevSym],
                                                funcIOReadTrack[prevSym],
                                                funcIOWriteTrack[prevSym],
                                            )
                                        )

                                    funcTrack[prevSym] = 0

                        stack.append(sym)
                        if verbose:
                            print(stack)

                        for i in stack:
                            if stack.count(i) > 1 and verbose:
                                printf("Warning : duplicate elts in stack\n\n")

                    pcPrev = pc
                    prevSym = sym
                    break

        if outTyp == "csv":
            if prevSym != "":

                m = re.search(MemLDmatchEx, item)
                if m:
                    clock = float(m.group("time"))
                    addr = int(m.group("addr"), 16)

                m = re.search(MemSTmatchEx, item)
                if m:
                    clock = float(m.group("time"))
                    addr = int(m.group("addr"), 16)
                    val = int(m.group("val"), 16)

                m = MemLDmatch.match(item)
                if m:
                    funcLDTrack[prevSym] = funcLDTrack[prevSym] + 1
                    continue

                m = MemSTmatch.match(item)
                if m:
                    funcSTTrack[prevSym] = funcSTTrack[prevSym] + 1
                    continue

                m = vecLDRe.match(item)
                if m:
                    funcVecLDTrack[prevSym] = funcVecLDTrack[prevSym] + 1
                    continue

                m = vecSTRe.match(item)
                if m:
                    funcVecSTTrack[prevSym] = funcVecSTTrack[prevSym] + 1
                    continue

                m = popRe.match(item)
                if m:
                    funcSclLDTrack[prevSym] = funcSclLDTrack[prevSym] + 1
                    continue

                m = pushRe.match(item)
                if m:
                    funcSclSTTrack[prevSym] = funcSclSTTrack[prevSym] + 1
                    continue

                m = sclLDRe.match(item)
                if m:
                    funcSclLDTrack[prevSym] = funcSclLDTrack[prevSym] + 1
                    continue

                m = sclSTRe.match(item)
                if m:
                    funcSclSTTrack[prevSym] = funcSclSTTrack[prevSym] + 1
                    continue
        else:
            if prevSym != "":

                m = re.search(MemLDmatchEx, item)
                if m:
                    clock = float(m.group("time"))
                    addr = int(m.group("addr"), 16)
                    val = int(m.group("val"), 16)

                m = re.search(MemSTmatchEx, item)
                if m:
                    clock = float(m.group("time"))
                    addr = int(m.group("addr"), 16)
                    val = int(m.group("val"), 16)

    # Add json end marker
    if outTyp == "json":
        outFile.seek(0, os.SEEK_END)
        outFile.seek(outFile.tell() - 2, os.SEEK_SET)
        outFile.write(
            """
        ]
        """
        )

    try:
        covFile = open("coverage", "w")
    except IOError:
        printf("Cannot open output file\n")
        sys.exit(2)

    covFile.write("func, size, size covered, coverage (%), inst\n")
    for key, value in codecov_dict.items():
        if bool(value[2]):
            cov = 0
            t16 = 0
            t32 = 0

            for pc, s in value[2]:
                if s == 2:
                    cov += 2
                    t16 += 1
                elif s == 4:
                    cov += 4
                    t32 += 1
                else:
                    print(f"error len={s}")
            if value[1] > 8:
                covFile.write(
                    '%s, %d, %d, %.2f, %d, (%d, %d), "'
                    % (
                        key,
                        value[1],
                        cov,
                        100 * float(cov) / float(value[1]),
                        len(value[0]),
                        t16,
                        t32,
                    )
                )

                if coverageDetails:
                    prev = 0
                    prev_s = 0
                    for i, s in sorted(value[2], key=lambda x: x[0]):
                        if prev != 0:
                            diff = int(i, 16) - prev
                            cnt = value[0][i]
                            if diff > prev_s:
                                covFile.write(f"({i}, {cnt}) [<-jump {diff}->], ")
                            else:
                                covFile.write(f"({i}, {cnt}), ")
                        prev = int(i, 16)
                        prev_s = int(s)
                else:
                    covFile.write("..no details..")
                covFile.write('"\n')


if __name__ == "__main__":
    main(sys.argv[1:])
