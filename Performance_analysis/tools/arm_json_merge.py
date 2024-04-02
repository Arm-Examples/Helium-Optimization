#!/usr/bin/python
# -*- coding: utf-8 -*-

#!/usr/bin/python
# -*- coding: utf-8 -*-

# * ----------------------------------------------------------------------
# * Project:      arm tiny tarmac profiling tool
# * Title:        arm_json_merge.py
# * Description:  merge 2 json containing timeline timeline information
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
import json


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# functions
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# printf for C programmers
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def printf(formatStr, *args):
    sys.stdout.write(formatStr % args)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# usage message
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def usage():

    printf(
        """
\033[4musage\033[0m : \033[31;1m arm_json_merge.py\033[00m symbol occurrence merged.json files...
"""
    )
    printf(" where : \n")
    printf(" symbol             : symbol to merge\n")
    printf(" occurrence         : occurrence\n")
    printf(" out.[json|csv]     : processed csv or json trace output\n")
    printf(" files ....         : files list\n")
    exit(2)


def filterAndAjustGen(dic, ts, dur, id):
    for obj in dic:
        if obj["ts"] >= ts and obj["ts"] <= ts + dur:
            obj["ts"] = obj["ts"] - ts
            obj["tid"] = id
            yield obj


def readJson(fileName):
    with open(fileName) as source:
        json_source = source.read()
        data = json.loads("[{}]".format(json_source))

    return data[0]


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# entry
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def main(argv):

    if len(sys.argv) < 6:
        usage()

    sym = sys.argv[1]
    occurence = int(sys.argv[2])
    jsonOut = sys.argv[3]

    jsonFile = []
    dataJson = []

    for i in range(4, len(sys.argv)):
        jsonFile.append(sys.argv[i])

    for file in jsonFile:
        dataJson.append(readJson(file))

    jsonBoundaries = []
    for file in dataJson:
        jsonBoundaries.append(
            [
                (obj["ts"], obj["dur"])
                for obj in file
                if (sym in obj["name"] and obj.get("dur", None))
            ]
        )

    for file in jsonBoundaries:
        if file == [] and file == []:
            printf("symbol %s not found\n", sym)
            return

    timeDur = []
    for item in jsonBoundaries:
        (ts, dur) = item[occurence]
        timeDur.append((ts, dur))

    timeDurData = zip(timeDur, dataJson)

    i = 0
    jsonFiltered = []
    for item in timeDurData:

        (tsDur, jsonAr) = item
        (ts, dur) = tsDur

        jsonFiltered += [obj for obj in filterAndAjustGen(jsonAr, ts, dur, jsonFile[i])]
        i += 1

    # write json with merged content
    with open(jsonOut, "w") as json_file:
        json.dump(jsonFiltered, json_file)


if __name__ == "__main__":
    main(sys.argv[1:])
