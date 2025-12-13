#ifndef GODBRAIN_PERF_H
#define GODBRAIN_PERF_H

#include <stdint.h>
#include <stdio.h>

#ifndef CPU_FREQ_HZ
#define CPU_FREQ_HZ 3000000000.0 // default 3 GHz (istersen güncelle)
#endif

static inline uint64_t rdtsc(void) {
    unsigned int lo, hi;
    __asm__ __volatile__("rdtsc" : "=a"(lo), "=d"(hi));
    return ((uint64_t)hi << 32) | lo;
}

static inline void measure_latency(const char* label, void (*fn)(void)) {
    uint64_t start = rdtsc();
    fn();
    uint64_t end = rdtsc();
    uint64_t cycles = end - start;
    double ns = cycles * (1e9 / CPU_FREQ_HZ);

    printf("%s: %llu cycles (%.2f ns)\n",
           label,
           (unsigned long long)cycles,
           ns);
}

#endif // GODBRAIN_PERF_H
