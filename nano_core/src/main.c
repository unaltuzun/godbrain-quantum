#include <stdio.h>
#include <time.h>

#include "market.h"
#include "risk.h"
#include "perf.h"

static LockFreeRing tick_ring;

static void fake_tick_producer(void) {
    MarketTick t;
    t.price = 100000; // 1000.00 * 100
    t.volume = 1000;
    t.timestamp_ns = (uint64_t)time(NULL) * 1000000000ULL;
    ring_push(&tick_ring, &t);
}

static void fake_tick_consumer(void) {
    MarketTick t;
    if (ring_pop(&tick_ring, &t)) {
        double price = (double)t.price / 100.0;
        Position pos = {
            .entry_price = 995.0,
            .quantity = 1.0,
            .stop_loss = 10.0,
            .take_profit = 15.0
        };
        risk_level_t r = check_risk(&pos, price);
        printf("Tick consumed: price=%.2f, risk_level=%d\n", price, (int)r);
    }
}

static void measure_demo(void) {
    measure_latency("fake_tick_producer", fake_tick_producer);
    measure_latency("fake_tick_consumer", fake_tick_consumer);
}

int main(void) {
    printf("GODBRAIN Nano Core Demo starting...\n");
    ring_init(&tick_ring);

    for (int i = 0; i < 5; i++) {
        measure_demo();
    }

    printf("GODBRAIN Nano Core Demo finished.\n");
    return 0;
}
