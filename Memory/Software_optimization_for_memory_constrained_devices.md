# Software optimization for DSP and ML - Making the most out of the memory system in microcontroller devices

## Introduction

The use of Digital Signal Processing (DSP) and Machine Learning (ML) in microcontroller devices is getting increasingly common. This has been accelerated by the availability of Helium technology, which is available in the Arm Cortex-M85, Cortex-M55 and Cortex-M52 processors. With the availability of the Helium instructions and the highly efficient pipeline designs of the Cortex-M processors, the DSP and ML capabilities of new microcontroller products has been significantly increased.  However, the memory systems of microcontrollers are often constrained. To maximize the benefits of the Helium technology and to get the best performance, chip designers and software developers therefore need to take the memory constraint into account.

## The constraints in microcontrollers

Typically, the following areas can be considered as key constraints in microcontroller applications:

- The size of the instruction and data caches inside the processors: In Cortex-M processors that support caches, the maximum size for the Instruction and data caches is 64KB. The typical cache size is between 16KB to 32KB.
- The size of the Tightly Coupled Memories (TCMs): TCMs are SRAM blocks that are connected directly to the processor to minimize the access latency (usually TCM accesses are single cycle). In the Cortex-M85, Cortex-M55 and Cortex-M52 processors, there are often Instruction and Data TCMs, which each have fixed address ranges in the memory map. Theoretically, the maximum TCM size supported by these processors is 16MB. However, because the maximum clock speed of large SRAM blocks is usually limited, typically the actual TCM size ranges from 128KB to 512KB.  In Cortex-M processors with TCMs, the processors also support an additional bus interface to allow other bus managers (e.g. a DMA controller) to access the TCMs. This feature avoids the need to copy data between the TCMs and other memories (e.g. main system memory) using software.
- The size of the on-chip system SRAM: On-chip system SRAMs are connected to the processor and other bus managers via bus interconnect components. Usually, the size of the system SRAM is larger than the caches and the TCMs.  For example, in microcontroller devices the on-chip system SRAM is usually in the range of 256KB to 2MB. Due to the larger memory size of the system SRAM, access to the SRAM blocks usually takes multiple processor clock cycles. Combining the multi-cycle access with the additional latency in the bus interconnect, the latency of a read access to the system SRAM could range from 4 to 10 clock cycles. However, because the processors support caches, the reads to the system SRAM only occurs when there is a cache miss or when the cache is disabled. Because of this cache feature, the average access cycle to the system SRAM is still close to single cycle.
- The lack of additional caches: In most cases, apart from level 1 caches inside the processor, the overall memory system does not have additional level 2 and level 3 caches. So, if there is a cache miss in the level 1 cache, the access would have to be carried out by the memory controller, which can take a longer time.
- Access latency in embedded flash memories and external serial flash memories. These types of memories are usually much slower than the processor speed.
- Memory access bandwidth. Helium technology is based on the Single Instruction Multiple Data (SIMD) concept with a vector (consisting of multiple data elements of the same data type) width of 128-bit. However, the memory interface of the buses, TCMs and RAM blocks are narrower than that, usually 64-bit or 32-bit. As a result, a bottleneck might be observed, caused by the memory bandwidth limitations.
- Many microcontrollers include a small retention memory. In applications where the device can sleep for a long period of time, the retention memory can be used to hold system states to allow the application to be resumed quickly, even though the rest of the memory system are powered down. Retention memories are optimized for low power, can be quite small in memory size, and are not optimized for performance. As a result, retention memories are less likely to be used by DSP and ML processing.

In addition to these constraints, designers also need to consider other factors such as:

- If appliable, real-time requirements of the applications.
- Optimizing the application(s) for low power.

## Understanding the workloads in the applications

When optimizing the chip designs and the software, one of the key tasks for designers is to understand the memory usages and the behaviours of the memory access in the workloads. Some of the typical characteristics of DSP and ML processing codes are as follows:

### Low-level DSP processing functions

- The functions have a small code size. As a result, the program codes cache very well in the processor caches.
- The functions might need coefficients that are read-only data. In some cases, the coefficient data could require a considerable memory size.
- The data being processed is different in every iteration. As a result, designers cannot rely on the caching of input data. However, input data is often accessed sequentially and therefore after a cache miss, the cache linefill would cache the required data as well as the subsequence data within the same cacheline (which is 8 words in size). As a result, cache misses usually only take place at the beginning of a cacheline.

### Neural Network (NN) inference in ML applications

- The NN weights in a ML model can be quite large.  Although the model weight in each NN layer could be grouped together and arranged so that they are accessed sequentially, the overall size of the NN weight data could be much larger than the data cache and therefore the data might not fit into the cache. As a result, in each iteration, the previous cached weight data may have been evicted from the cache and resulted in cache misses at the beginning of each cacheline.
- Activation data can range from small to large depending on the ML model and application. For example, inference of images has a much larger memory usage than keyword spotting or vibration analysis.
- Potentially a large program size.  Some ML runtime libraries (e.g. TensorFlow Lite for microcontrollers) often contain a lot of code. This is because these libraries include many low-level functions for different ML operators, as well as the code for interpretating the ML models. However, this does not mean that we need a very big instruction cache. This is because during inference processing, only a few operators would be used for each layer and the code size for each operator can be quite small. As a result, most of the ML runtime libraries work very well with a cached program memory system.

In addition to the characteristics of the DSP and ML processing, designers should also look at the characteristics of other software components in the application. For example, software developers need to identify what data in the main system memory should be cached and what should not. For example, a bitmap image for a user interface might only need to be accessed once in a while and therefore should not be cached.

## Considerations for chip designers

Unlike traditional control applications, DSP and ML applications often have a much larger data memory requirement. In addition, microcontrollers designed for IoT applications often include the TrustZone feature, which means the memories (including the TCMs) can be partitioned into Secure and Non-secure address ranges and be utilized by both secure firmware and normal applications. As a result, the cache and TCM size required are usually larger than traditional devices designed for control applications.

To enable efficient usage of the TCMs, chip designs should include DMA controller(s) to enable data transfers between the TCMs and the main memories and for traditional DMA usage. By having a DMA controller, data can be transferred between the main memories and the TCMs while the processor is handing other processing tasks.

For the best performance, TCM access should be designed as single cycle. That said, the TCM interfaces in Cortex-M85, Cortex-M55 and Cortex-M52 support waitstates. If necessary, to support a larger TCM size which cannot be single cycle at the maximum clock speed, it is possible to create a TCM memory system, with part of the TCM address range supporting single cycle access and the remaining address range(s) supporting multi-cycle access.

It is not necessary to keep the Instruction cache and Data cache the same size. In some instances, for certain DSP/ML applications, the whole program code can be copied into the I-TCM and when that is the case, there is no need for an Instruction cache. However, the program size for most microcontroller applications is larger than the Instruction TCM and therefore copying the whole program codes to the I-TCM is not feasible. At the same time, the non-volatile program storage (e.g. embedded flash) has a slow access speed. In such cases, both Instruction caches and Data caches are needed because the program codes contain various constant values that are cached via the Data cache.

For low-cost microcontrollers designed with the Cortex-M52 processor, there is a configuration option of having a unified cache. This is suitable for designs where R/W data is mostly placed in the SRAM connected to the D-TCM, and hence a full data cache could be overkill. When the unified cache configuration is used there is no data cache in the processor.

## Considerations for software developers

### Utilizing the TCMs

Tightly Coupled Memories (TCMs) provide low latency instruction and data access. Usually the data in D-TCM can be accessed in a single clock cycle. Therefore, placing codes and data in the TCMs often provides the best performance. However, the main usage of the TCMs is to provide real-time capabilities; this is because accesses to the TCMs bypass the caches. As a result, normally the TCMs are prioritized for the usage of codes and data that are needed for real-time responses.  For example:

- Exception vector table(s) and interrupt service routines that are real-time critical should be placed in the I-TCM.
- The data required by real-time critical software components should be placed in the D-TCM. If the D-TCM size allows, it would be good to put the Main stack into the D-TCM. However, generally placing stacks in cacheable on-chip SRAM does not result in noticeable performance drop. Because most stack POP operations read recently accesses stacked data, cache misses on stack POP are relatively rare for interrupt handlers. However, if the application contains critical real-time interrupt services that where cache misses are undesirable, then it is best to place the Main stack on to the D-TCM.

After the real-time critical code and data is placed in the TCM, the rest of the TCM spaces can be utilized for DSP and ML workloads. Since the size of the TCM is limited, software developers need to decide how to best utilize the TCM space based on the requirements of their applications. As explained earlier, the low-level codes for DSP and ML (excluding the data being processed) can usually be placed in a cacheable memory. Data placement can be more challenging because the input data values being processed are different for each iteration. Instead of using software to copy the input data from the main memory to the D-TCM for processing, software developers should utilize DMA controllers to handle this copying operation while the previous processing is still on going. This reduces the software overhead, but the software developer must then allocate two sets of input data buffer within the D-TCM so that when one buffer is being used for processing, the other can be used for the DMA transfer.

Similarly, you can place output data buffers in the D-TCM and use a DMA controller to copy the output data back to the main memory after processing. However, due to the store buffers inside the processor’s bus interface, writing out data to the main memory (which has an access latency) does not always cause delay (i.e. stall cycles) in the processor’s pipeline, especially when the Data cache is enabled, and the write-back cache scheme is used. As a result, the output data buffers can be placed in the main system memory for most of the DSP and ML applications.

To reduce the D-TCM usage further, we can move the I/O buffers out of the D-TCMs into the system SRAM, leaving only an input data buffer and, optionally, an output data buffer in the D-TCM for each block of data processing. To process a block of data, the steps are:

1. Use a DMA channel to copy a block of data from the system SRAM to the input buffer in the D-TCM.
2. Data processing receiving an interrupt that indicates step 1 is completed.
3. If the output buffer is in the D-TCM, use a DMA channel to copy the result into system SRAM. (As mentioned earlier, putting output data buffer in system SRAM might not result in a large performance penalty).

This arrangement might increase the overall memory usage because the ping-pong I/O buffers and the data processing buffers are separated. However, the D-TCM usage can be reduced. If the DMA controller can handle concurrent operations of multiple concurrent DMA channels, potentially step 1 and step 3 can overlap.

One additional method to reduce data memory usage is to overlay memory buffers used by different processing stages. Many data processing tasks contain multiple stages that are handled sequentially and cannot overlap. In such cases, the data buffers used by different stages can potentially be placed in the same SRAM location, for example, by setting up pointers to the buffers specifically to overlay them. Combining the use of DMA and overlaying buffers in TCM, it is possible to reduce overall memory usage. However, software developers need to be aware of the implications:

- The processing stages that share the same overlay memory must not execute at the same time. If an RTOS is used, for example, they can be placed in the same OS thread so that they must be executed sequentially.
- The debugger accessing the overlayed memory is not aware of which context is being executed and therefore it can be harder to debug the application.
- If an RTOS is used, it is not possibly to provide processing isolation on the shared overlayed memory. However, if the multiple processing stage is in the same OS thread there is no need for process isolation anyway.
- Depending on how the overlaying is achieved in the toolchain, this might result in toolchain dependency.

Nevertheless, memory overlaying can be a handy solution for reducing memory footprint for some processing threads. Memory overlaying can be applied to program codes too, for example, by placing certain time critical code in the I-TCM dynamically. However, in most cases DSP and ML processing routines usually has small program sizes and work well with I-caches, so overlaying of codes is less common.

### Caches and the main memory system

The Cortex-M85, Cortex-M55 and Cortex-M52 support optional I-cache and D-cache (up to 64KB each). In addition, the Cortex-M52 supports a unified cache configuration for low-cost microcontrollers. The cache designs are based on the following:

- I-cache/Unified cache: Two way set associative cache.
- D-cache: Four-way set associative cache.

By default, the D-cache uses a write-back (WB) cache scheme, which provides the best performance. However, you can select the Write-Through (WT) cache scheme using one of the following methods:

- By configuring the Memory Protection Unit (MPU) to use WT for certain memory regions.
- By setting the FORCEWT bit in the Memory System Control Register (MSCR) to 1 so that all cacheable memory accesses are using the write through cache scheme.

Please note, when the write-back cache scheme is used the write data might stay in the D-cache for a period of time. As a result, after filling the output data buffer, other bus managers in the system might not be able to observe the new data unless the software also carries out a cache clean operation. So, instead of using the write-back cache (default cache scheme), software developers could select the write-through cache scheme instead. Using the write-through cache scheme has a lower performance, but it has the benefit that other bus managers will be able to see the output data from the processors without any additional software steps.

An additional solution that will enable the software running on the processor and other bus manager(s) to have a coherent data view is to set the memory region as either Sharable or Non-cacheable. This can be done by configuring the MPU. In both cases, the data within the region will not be cached in the level 1 data cache. However, there is a difference between the two memory attributes:

- If Shareable attribute is used, the data might, if present, still be cached in a system level cache.
- If Non-shareable attribute is used, the data will not be cached in a system level cache unless the MPU region is configured to utilize separate inner and outer cacheability attributes.

When optimizing software, data used by the intermediate stages of the DSP/ML functions can stay in the main memory and can still perform well. When the write-back cache scheme is used, the write and subsequent read of the intermediate state data is less likely to cause a delay because the data is usually still in the Data cache. And because the intermediate data is only read by the processor there is no need to add cache clean operations or to use the write-through cache scheme.

### Other considerations

The TCM interface designs in the Cortex-M processors support both instruction and data access. So, theoretically Read/Write data can be put in the I-TCM and program codes can be put in the D-TCM. However, the processor designs are not optimized for such an arrangement. If the D-TCM space is limited, it might be an acceptable trade-off to put some constant data (e.g. DSP coefficients) in the I-TCM. However, by doing so the processing performance can be lower than when using the D-TCM due to the following factors:

- If the program code is executing from the I-TCM at the same time, the instruction fetches and data accesses are competing for bandwidth, therefore reducing the performance.
- For the Cortex-M55 and Cortex-M52 processors, the I-TCM data width is 32-bit, which means fetching Helium vector data from the I-TCM would take 4 clock cycles and would therefore reduce performance.

Please note:

1) It is not always necessary to put input data in the D-TCM for the best performance because the Data caches in the Cortex-M85 and the Cortex-M55 processors support data prefetching. This means that if there are sequential data accesses or when the data access pattern is recognized by the data prefetcher, the Data cache can prefetch additional data from the main memory to reduce the chance of cache misses. The prefetch behaviour is software controllable through the Prefetch Control Register (PFCR). Data prefetching is not implemented in revision 0 of the Cortex-M52 processor.
2) In Armv8-M architecture, the MPU allows MPU regions to be marked as “transient”. When the Data cache controller needs to evict a cacheline (for example, when a cacheline is needed to store different data), the cache controller prioritises the eviction of the transient data.

One area to consider when optimizing software is to look at other ways of reducing the use of data memory. Areas to consider:

- The Armv8.1-M architecture supports the half precision floating-point data format (16-bit). If a floating-point data array is switched from single-precision (32-bit) to half-precision, the array memory size is halved. At the same time, you might benefit from higher data processing performance because each Helium instruction can process eight half-precision data instead of four for single precision data.
- Some DSP data is symmetrical by nature (e.g. Finite Impulse Response (FIR) filter coefficients). This means that storage size of the constant data can be reduced by half. For pre-calculated Fast Fourier Transform (FFT) twiddle factors, the data storage can be ¼ of the full array size by creating the other ¾ of data using reversing and negating.
