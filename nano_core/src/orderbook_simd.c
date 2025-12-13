#include <stdint.h>
#include <stdint.h>
#include <stddef.h>

// SIMD placeholder: gerçek orderbook bellek düzeni netleşince AVX/NEON optimize edilir.
// Şimdilik sadece derlenebilir iskelet.

typedef struct {
    double bid;
    double ask;
    int64_t microtimestamp;
} OrderBookLevel;

double process_orderbook_scalar(const OrderBookLevel* levels, size_t n) {
    double acc = 0.0;
    for (size_t i = 0; i < n; i++) {
        acc += (levels[i].ask - levels[i].bid);
    }
    return acc;
}
