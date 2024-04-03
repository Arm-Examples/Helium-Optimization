
# Helium optimization topics #1 - the basics

## What is the Helium Technology

Arm Helium Technology is an optional architecture extension in the Armv8.1-M architecture. It contains a range of instructions to enable better signal processing and machine learning processing performance with a relatively small increase in the hardware cost of the processor design. The Helium technology is currently supported in the following processors:

- Arm Cortex®-M85
- Arm Cortex-M55
- Arm Cortex-M52

In Armv8.1-M architecture, Helium technology is referred as M-Profile Vector Extension (MVE). Helium is a brand name that is specific to Arm implementation of MVE.

MVE brings over 150 new instructions to Cortex-M processors, most of them are vector processing instructions. In the context of MVE, a vector is 128-bit wide and can contain data elements of either:

- sixteen 8-bit data (e.g. int8_t), or
- eight 16-bit data (e.g. int16_t, _Float16), or
- four 32-bit data (e.g. int32_t, float)

Using the concept of Single-Instruction, Multiple-Data (SIMD), MVE instructions allows more data to be processed in each instruction. But of course, having a 128-bit ALU in the Cortex-M processor can be a bit expensive in terms of power and silicon area. Therefore in both Cortex-M55 and Cortex-M85 processors, the MVE data path is only 64-bit wide. It means each vector processing takes two clock cycles.

To enable the best possible performance and efficiency, Armv8.1-M processors (e.g. Cortex-M55, Cortex-M85) allows the execution cycles of MVE instructions to be partially overlapped, providing that the instructions are in different instruction groups (i.e. no hardware resource conflict). By interleaving MVE instructions from different instruction groups, the processor can get to a processing bandwidth of 1 instruction per cycle.

In addition to vector processing instructions, MVE instruction set also cover various forms of memory read/write instructions, including variants of read/write with packing, unpacking, interleaving, etc. To enable best performance, Armv8.1-M also support a Low-Overhead-Branch (LOB) extension, which provide loop instructions that have minimal loop overhead.

To make the most out of an Arm Cortex-M processor with the Helium technology, we can start our journey with the following areas:

- Initialization of the processor’s hardware
- Toolchain
- Selection of data types
- Use of optimized software libraries
- Utilizing auto-vectorization feature in C compiler

If you are new to Helium technology and Armv8.1-M architecture, the following paper provides a good starting point:
[Introduction to Armv8.1-M Architecture](https://armkeil.blob.core.windows.net/developer/Files/pdf/white-paper/introduction-to-armv8-1-m-architecture.pdf)

## Processor initialization

Several steps are involved in the processor’s initialization. These are:

- Enabling the Low-overhead branch feature
- Enabling the Helium hardware
- If needed, enabled the instruction and data caches – if the software is executed from memories with wait state, both instruction and data caches should be enabled because program image contains various read-only data which can benefit from caching.
- Enable branch predication if you are using the Cortex-M85 processor.
- Potentially, you need to adjust the power control settings in the Core Power Domain Low Power State Register (CPBLPSTATE).

The details of these processor initialization steps are covered in the following blog: [Getting started with Armv8.1-M based processor: software development hints and tips](https://community.arm.com/arm-community-blogs/b/architectures-and-processors-blog/posts/armv8_2d00_m-based-processor-software-development-hints-and-tips)

## Using the right command line options in compilation toolchain

Because Helium and Floating-point unit (FPU) are optional features, the support for these features in the compiler can be enabled / disabled during compilation. As a result, software developers need to ensure that correct compilation options (or command line options if using the compiler in Command Line Interface)
For Arm Compiler 6.22, please refer to the following page for available options for Armv8.1-M processors: [Supported architecture feature combinations for specific processors](
https://developer.arm.com/documentation/101754/0622/armclang-Reference/Other-Compiler-specific-Features/Supported-architecture-feature-combinations-for-specific-processors)

Commonly used command line options are included here:

|Processor configuration|armclang / GCC option (-mcpu) | Armlink/fromelf options (--cpu)|
|---|---|---|
|No Helium, no FPU |# Cortex-M52 | # Cortex-M52 |
||-mcpu=cortex-m52+nomve+nofp|--cpu=cortex-m52.no_mve.no_fp|
||# Cortex-M55 | # Cortex-M55 |
||-mcpu=cortex-m55+nomve+nofp|--cpu=cortex-m55.no_mve.no_fp|
||# Cortex-M85 | # Cortex-M85 |
||-mcpu=cortex-m85+nomve+nofp|--cpu=cortex-m85.no_mve.no_fp|
|No Helium, have FPU |# Cortex-M52 | # Cortex-M52 |
||-mcpu=cortex-m52+nomve|--cpu=cortex-m52.no_mve|
||# Cortex-M55 | # Cortex-M55 |
||-mcpu=cortex-m55+nomve|--cpu=cortex-m55.no_mve|
||# Cortex-M85 | # Cortex-M85 |
||-mcpu=cortex-m85+nomve|--cpu=cortex-m85.no_mve|
|Full feature |# Cortex-M52 | # Cortex-M52 |
||-mcpu=cortex-m52|--cpu=cortex-m52|
||# Cortex-M55 | # Cortex-M55 |
||-mcpu=cortex-m55|--cpu=cortex-m55|
||# Cortex-M85 | # Cortex-M85 |
||-mcpu=cortex-m85|--cpu=cortex-m85|

Additional GCC options for Arm processors can be found in https://gcc.gnu.org/onlinedocs/gcc/ARM-Options.html.

## Selection of data types

Helium technology supports the following data types:

- 8-bit integer
- 16-bit integer
- 32-bit integer
- 64-bit integer – limited to a few shift instructions (SQRSHRL, UQRSHLL), predication operations and memory accesses.
16-bit floating-point (Note: IEEE-754 version, not bfloat)
- 32-bit single floating-point

While current Armv8.1-M processor supports double precision floating-point data processing, it is for scalar operations only and not in form of vector processing / SIMD. Typically, using a small data type can give better performance because Helium instructions can process more data elements at the same time.
For some software developers, the half precision floating-point data type could be new to them. In C programming, half precision floating-point data are declared as _Float16. More information on this topics can be found near the end of this page [Getting started with Armv8.1-M based processor: software development hints and tips](https://community.arm.com/arm-community-blogs/b/architectures-and-processors-blog/posts/armv8_2d00_m-based-processor-software-development-hints-and-tips).

## Using optimized software libraries

Arm provides [CMSIS-DSP](https://github.com/ARM-software/CMSIS-DSP), [CMSIS-NN](https://github.com/ARM-software/CMSIS-NN) and [Arm-2D](https://github.com/ARM-software/Arm-2D)  libraries that are already optimized for Helium instructions. Recent releases of CMSIS-DSP libraries are delivered as source code. For best performance with Arm toolchains (e.g. Keil Studio, Keil MDK, Arm DS) please compile the CMSIS-DSP with -Ofast optimization level.
In addition, when porting applications from previous Cortex-M projects, please visit [CMSIS-DSP library documentation](https://arm-software.github.io/CMSIS-DSP/latest/index.html) to check:

1) if the DSP functions you are using have Helium specific variant. For example, the biquad initialization function “arm_biquad_cascade_df1_init_f32” has a Helium variant “arm_biquad_cascade_df1_mve_init_f32”
2) if the DSP functions you are using have specific recommendations for data alignment.

CMSIS-DSP is optimized to work on block of data. Those blocks must be big enough so that most of the cycles are spent in the main body of the function. If you work with too small blocks, there won't be any acceleration. In that case, it is probably better to manually write a dedicated function.

If you can't find the needed feature in the existing libraries, you'll need to vectorize the code yourself.
The source codes in the CMSIS-DSP libraries are written with intrinisic functions. In some cases, additional performance gain is possible using inline assembly. Arm provides a selection of optimized DSP functions in the following location: https://github.com/ARM-software/EndpointAI/tree/master/Kernels/ARM-Optimized/DSP/Source

The CMSIS-NN libraries are used by ML software runtime such as TensorFlow Lite for Microcontroller. It is very unlikely that the CMSIS-NN library functions are being called in application code directly. To use CMSIS-NN, you need to ensure that the ML runtime libraries are compiled with CMSIS-NN option enabled. For example, [this page](https://github.com/tensorflow/tflite-micro/tree/main/tensorflow/lite/micro/cortex_m_corstone_300) contains information about compiling TensorFlow Lite Micro with CMSIS-NN enabled (Note the " OPTIMIZED_KERNEL_DIR=cmsis_nn " option).
