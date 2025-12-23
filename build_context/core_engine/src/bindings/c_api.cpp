/**
 * @file c_api.cpp
 * @brief C API for Python ctypes integration
 *
 * Simple C interface for calling from Python without pybind11.
 *
 * @author GODBRAIN Team
 * @version 1.0.0
 */

#include "godbrain/godbrain.hpp"
#include <cstring>


using namespace godbrain;

// Global engine instance
static ExecutionEngine *g_engine = nullptr;

extern "C" {

// =============================================================================
// Initialization
// =============================================================================

int godbrain_init() {
  if (g_engine)
    return 0;

  try {
    g_engine = new ExecutionEngine();
    return 0;
  } catch (...) {
    return -1;
  }
}

void godbrain_shutdown() {
  delete g_engine;
  g_engine = nullptr;
}

const char *godbrain_version() { return Version::STRING; }

// =============================================================================
// Orderbook
// =============================================================================

void godbrain_update_orderbook(const char *symbol, const double *bid_prices,
                               const double *bid_sizes, int bid_count,
                               const double *ask_prices,
                               const double *ask_sizes, int ask_count) {
  if (!g_engine)
    return;

  Orderbook book;
  PriceLevel bids[25], asks[25];

  for (int i = 0; i < bid_count && i < 25; ++i) {
    bids[i].price = to_price_micro(bid_prices[i]);
    bids[i].quantity = to_quantity_nano(bid_sizes[i]);
  }

  for (int i = 0; i < ask_count && i < 25; ++i) {
    asks[i].price = to_price_micro(ask_prices[i]);
    asks[i].quantity = to_quantity_nano(ask_sizes[i]);
  }

  book.update_snapshot(bids, bid_count, asks, ask_count, 0, now_ns());
  g_engine->update_orderbook(Symbol(symbol), book);
}

double godbrain_get_mid_price(const char *symbol) {
  if (!g_engine)
    return 0.0;

  const Orderbook *book = g_engine->get_orderbook(Symbol(symbol));
  return book ? from_price_micro(book->mid_price()) : 0.0;
}

double godbrain_get_spread(const char *symbol) {
  if (!g_engine)
    return 0.0;

  const Orderbook *book = g_engine->get_orderbook(Symbol(symbol));
  return book ? book->spread_percent() : 0.0;
}

double godbrain_get_imbalance(const char *symbol, int levels) {
  if (!g_engine)
    return 0.0;

  const Orderbook *book = g_engine->get_orderbook(Symbol(symbol));
  return book ? book->imbalance(static_cast<size_t>(levels)) : 0.0;
}

// =============================================================================
// Trading
// =============================================================================

uint64_t godbrain_submit_order(const char *symbol,
                               int side, // 0=BUY, 1=SELL
                               int type, // 0=MARKET, 1=LIMIT
                               double quantity, double price) {
  if (!g_engine)
    return 0;

  return g_engine->submit_order(
      Symbol(symbol), static_cast<Side>(side), static_cast<OrderType>(type),
      to_quantity_nano(quantity), to_price_micro(price));
}

int godbrain_cancel_order(uint64_t order_id) {
  if (!g_engine)
    return 0;
  return g_engine->cancel_order(order_id) ? 1 : 0;
}

int godbrain_cancel_all_orders(const char *symbol) {
  if (!g_engine)
    return 0;
  return static_cast<int>(g_engine->cancel_all_orders(Symbol(symbol)));
}

int godbrain_close_position(const char *symbol) {
  if (!g_engine)
    return 0;
  return g_engine->close_position(Symbol(symbol)) ? 1 : 0;
}

int godbrain_close_all_positions() {
  if (!g_engine)
    return 0;
  return static_cast<int>(g_engine->close_all_positions());
}

// =============================================================================
// Position
// =============================================================================

int godbrain_get_position(const char *symbol, double *quantity,
                          double *entry_price, double *pnl) {
  if (!g_engine)
    return 0;

  const Position *pos = g_engine->get_position(Symbol(symbol));
  if (!pos)
    return 0;

  *quantity = from_quantity_nano(pos->quantity);
  *entry_price = from_price_micro(pos->avg_entry_price);
  *pnl = from_price_micro(pos->realized_pnl);

  return 1;
}

double godbrain_get_equity() {
  if (!g_engine)
    return 0.0;
  return from_price_micro(g_engine->equity());
}

void godbrain_set_equity(double equity) {
  if (g_engine) {
    g_engine->set_equity(to_price_micro(equity));
  }
}

// =============================================================================
// SIMD Statistics
// =============================================================================

double godbrain_simd_mean(const double *data, int n) {
  return simd::mean(data, static_cast<size_t>(n));
}

double godbrain_simd_stddev(const double *data, int n) {
  return simd::stddev(data, static_cast<size_t>(n));
}

double godbrain_simd_sharpe(const double *returns, int n, double risk_free) {
  return simd::sharpe_ratio(returns, static_cast<size_t>(n), risk_free);
}

double godbrain_simd_max_drawdown(const double *equity, int n) {
  return simd::max_drawdown(equity, static_cast<size_t>(n));
}

} // extern "C"
