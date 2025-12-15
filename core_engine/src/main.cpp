/**
 * @file main.cpp
 * @brief GODBRAIN Engine Entry Point
 *
 * Main executable demonstrating the C++ trading engine.
 *
 * @author GODBRAIN Team
 * @version 1.0.0
 */

#include <atomic>
#include <chrono>
#include <csignal>
#include <iostream>
#include <thread>


#include "godbrain/godbrain.hpp"

using namespace godbrain;

std::atomic<bool> running{true};

void signal_handler(int) { running = false; }

void event_callback(const ExecutionEvent &event) {
  const char *type_str = nullptr;
  switch (event.type) {
  case EventType::ORDER_SUBMITTED:
    type_str = "ORDER_SUBMITTED";
    break;
  case EventType::ORDER_ACCEPTED:
    type_str = "ORDER_ACCEPTED";
    break;
  case EventType::ORDER_REJECTED:
    type_str = "ORDER_REJECTED";
    break;
  case EventType::ORDER_PARTIALLY_FILLED:
    type_str = "ORDER_PARTIAL";
    break;
  case EventType::ORDER_FILLED:
    type_str = "ORDER_FILLED";
    break;
  case EventType::ORDER_CANCELLED:
    type_str = "ORDER_CANCELLED";
    break;
  case EventType::POSITION_OPENED:
    type_str = "POSITION_OPENED";
    break;
  case EventType::POSITION_UPDATED:
    type_str = "POSITION_UPDATED";
    break;
  case EventType::POSITION_CLOSED:
    type_str = "POSITION_CLOSED";
    break;
  case EventType::RISK_ALERT:
    type_str = "RISK_ALERT";
    break;
  }

  printf(
      "[EVENT] %s | Order: %lu | Symbol: %s | Price: %.6f | Qty: %.2f | %s\n",
      type_str, event.order_id, event.symbol.view().data(),
      from_price_micro(event.price), from_quantity_nano(event.quantity),
      event.message);
}

void benchmark_queue() {
  printf("\n=== Queue Benchmark ===\n");

  SPSCQueue<MarketTick, 8192> queue;
  constexpr size_t N = 1'000'000;

  // Measure push latency
  auto start = std::chrono::high_resolution_clock::now();

  for (size_t i = 0; i < N; ++i) {
    MarketTick tick;
    tick.timestamp = now_ns();
    tick.bid = to_price_micro(0.32);
    tick.ask = to_price_micro(0.321);
    tick.sequence = i;
    queue.push(tick);
    queue.pop();
  }

  auto end = std::chrono::high_resolution_clock::now();
  auto duration =
      std::chrono::duration_cast<std::chrono::nanoseconds>(end - start);

  printf("Push/Pop latency: %.1f ns/op\n",
         static_cast<double>(duration.count()) / N);
}

void benchmark_orderbook() {
  printf("\n=== Orderbook Benchmark ===\n");

  Orderbook book;
  constexpr size_t N = 1'000'000;

  PriceLevel bids[25], asks[25];
  for (int i = 0; i < 25; ++i) {
    bids[i].price = to_price_micro(0.32 - i * 0.0001);
    bids[i].quantity = to_quantity_nano(10000 + i * 100);
    asks[i].price = to_price_micro(0.321 + i * 0.0001);
    asks[i].quantity = to_quantity_nano(8000 + i * 100);
  }

  auto start = std::chrono::high_resolution_clock::now();

  for (size_t i = 0; i < N; ++i) {
    book.update_snapshot(bids, 25, asks, 25, i, now_ns());
    volatile auto mid = book.mid_price();
    volatile auto imb = book.imbalance();
    (void)mid;
    (void)imb;
  }

  auto end = std::chrono::high_resolution_clock::now();
  auto duration =
      std::chrono::duration_cast<std::chrono::nanoseconds>(end - start);

  printf("Update + analysis latency: %.1f ns/op\n",
         static_cast<double>(duration.count()) / N);

  printf("Spread: %.6f%%\n", book.spread_percent());
  printf("Imbalance: %.4f\n", book.imbalance());
}

void benchmark_simd() {
  printf("\n=== SIMD Benchmark ===\n");

  constexpr size_t N = 10'000;
  std::vector<double> data(N);
  for (size_t i = 0; i < N; ++i) {
    data[i] = 0.001 * (static_cast<double>(rand()) / RAND_MAX - 0.5);
  }

  constexpr size_t ITERS = 10'000;

  auto start = std::chrono::high_resolution_clock::now();

  volatile double result = 0;
  for (size_t i = 0; i < ITERS; ++i) {
    result = simd::mean(data.data(), N);
    result = simd::variance(data.data(), N);
    result = simd::stddev(data.data(), N);
  }
  (void)result;

  auto end = std::chrono::high_resolution_clock::now();
  auto duration =
      std::chrono::duration_cast<std::chrono::microseconds>(end - start);

  printf("Mean/Var/Stddev (%zu elements): %.2f us/iter\n", N,
         static_cast<double>(duration.count()) / ITERS);

  printf("Sharpe ratio: %.4f\n", simd::sharpe_ratio(data.data(), N));
}

void demo_trading() {
  printf("\n=== Trading Demo ===\n");

  RiskParams risk;
  risk.max_position_size = 0.1;
  risk.max_open_orders = 10;

  ExecutionEngine engine(risk);
  engine.register_callback(event_callback);

  // Setup orderbook
  Orderbook book;
  PriceLevel bids[5] = {
      {to_price_micro(0.3199), to_quantity_nano(100000), 5},
      {to_price_micro(0.3198), to_quantity_nano(200000), 8},
      {to_price_micro(0.3197), to_quantity_nano(300000), 12},
      {to_price_micro(0.3196), to_quantity_nano(400000), 15},
      {to_price_micro(0.3195), to_quantity_nano(500000), 20},
  };
  PriceLevel asks[5] = {
      {to_price_micro(0.3201), to_quantity_nano(80000), 4},
      {to_price_micro(0.3202), to_quantity_nano(150000), 7},
      {to_price_micro(0.3203), to_quantity_nano(220000), 10},
      {to_price_micro(0.3204), to_quantity_nano(280000), 13},
      {to_price_micro(0.3205), to_quantity_nano(350000), 16},
  };
  book.update_snapshot(bids, 5, asks, 5, 1, now_ns());
  engine.update_orderbook(Symbol("DOGE/USDT"), book);

  printf("Orderbook mid: %.6f, spread: %.4f%%\n",
         from_price_micro(book.mid_price()), book.spread_percent());

  // Submit orders
  printf("\n--- Submitting orders ---\n");

  OrderId id1 = engine.submit_order(Symbol("DOGE/USDT"), Side::BUY,
                                    OrderType::MARKET, to_quantity_nano(5000));
  printf("Order 1 ID: %lu\n", id1);

  OrderId id2 = engine.submit_order(Symbol("DOGE/USDT"), Side::SELL,
                                    OrderType::MARKET, to_quantity_nano(3000));
  printf("Order 2 ID: %lu\n", id2);

  // Check position
  const Position *pos = engine.get_position(Symbol("DOGE/USDT"));
  if (pos) {
    printf("\n--- Position ---\n");
    printf("Quantity: %.4f\n", from_quantity_nano(pos->quantity));
    printf("Avg entry: %.6f\n", from_price_micro(pos->avg_entry_price));
    printf("Notional: $%.2f\n", pos->notional_value());
  }

  printf("\nEquity: $%.2f\n", from_price_micro(engine.equity()));
}

int main() {
  std::signal(SIGINT, signal_handler);

  print_banner();

  if (!initialize()) {
    std::cerr << "Failed to initialize GODBRAIN\n";
    return 1;
  }

  // Run benchmarks
  benchmark_queue();
  benchmark_orderbook();
  benchmark_simd();

  // Demo trading
  demo_trading();

  printf("\n[GODBRAIN] Engine shutdown complete.\n");

  return 0;
}
