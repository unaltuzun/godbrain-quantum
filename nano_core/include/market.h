#ifndef GODBRAIN_MARKET_H
#define GODBRAIN_MARKET_H

#include <stdatomic.h>
#include <stdint.h>
#include <string.h>

#define CACHE_LINE_SIZE 64
#define RING_SIZE 4096  // 2^n olmalı

// Tick data: ring içinde plain struct (atomic değil); atomic head/tail yeterli.
typedef struct __attribute__((aligned(64))) {
    uint64_t price;        // örn: 1000.00 * 100
    uint64_t volume;
    uint64_t timestamp_ns;
} MarketTick;

typedef struct __attribute__((aligned(CACHE_LINE_SIZE))) {
    MarketTick buffer[RING_SIZE];
    _Atomic uint64_t head;
    _Atomic uint64_t tail;
} LockFreeRing;

static inline void ring_init(LockFreeRing* ring) {
    memset(ring, 0, sizeof(*ring));
}

static inline int ring_push(LockFreeRing* ring, const MarketTick* tick) {
    uint64_t head = atomic_load_explicit(&ring->head, memory_order_relaxed);
    uint64_t next_head = (head + 1) & (RING_SIZE - 1);

    uint64_t tail = atomic_load_explicit(&ring->tail, memory_order_acquire);
    if (next_head == tail) return 0; // full

    ring->buffer[head] = *tick;
    atomic_store_explicit(&ring->head, next_head, memory_order_release);
    return 1;
}

static inline int ring_pop(LockFreeRing* ring, MarketTick* out) {
    uint64_t tail = atomic_load_explicit(&ring->tail, memory_order_relaxed);
    uint64_t head = atomic_load_explicit(&ring->head, memory_order_acquire);
    if (tail == head) return 0; // empty

    *out = ring->buffer[tail];
    uint64_t next_tail = (tail + 1) & (RING_SIZE - 1);
    atomic_store_explicit(&ring->tail, next_tail, memory_order_release);
    return 1;
}

#endif // GODBRAIN_MARKET_H
