/**
 * @file execution_engine.hpp
 * @brief Ultra-Low Latency Execution Engine
 *
 * Core order execution with risk checks, position management,
 * and order lifecycle handling.
 *
 * @author GODBRAIN Team
 * @version 1.0.0
 */

#pragma once

#include "godbrain/lock_free_queue.hpp"
#include "godbrain/memory_pool.hpp"
#include "godbrain/orderbook.hpp"
#include "godbrain/types.hpp"
#include <functional>
#include <mutex>
#include <unordered_map>
#include <vector>

namespace godbrain {

// =============================================================================
// Execution Events
// =============================================================================

enum class EventType : uint8_t {
  ORDER_SUBMITTED,
  ORDER_ACCEPTED,
  ORDER_REJECTED,
  ORDER_PARTIALLY_FILLED,
  ORDER_FILLED,
  ORDER_CANCELLED,
  POSITION_OPENED,
  POSITION_UPDATED,
  POSITION_CLOSED,
  RISK_ALERT
};

struct ExecutionEvent {
  EventType type;
  OrderId order_id;
  Symbol symbol;
  PriceMicro price;
  QuantityNano quantity;
  Timestamp timestamp;
  ErrorCode error;
  char message[64];
};

using EventCallback = std::function<void(const ExecutionEvent &)>;

// =============================================================================
// Execution Engine
// =============================================================================

class ExecutionEngine {
public:
  explicit ExecutionEngine(const RiskParams &risk_params = {})
      : risk_params_(risk_params), next_order_id_(1),
        equity_(1'000'000 * PRICE_SCALE) // 1M starting equity
        ,
        is_running_(false) {}

  // =========================================================================
  // Order Management
  // =========================================================================

  /**
   * @brief Submit new order
   * @return Order ID if accepted, 0 if rejected
   */
  [[nodiscard]] OrderId submit_order(Symbol symbol, Side side, OrderType type,
                                     QuantityNano quantity,
                                     PriceMicro price = 0,
                                     PriceMicro stop_price = 0,
                                     TimeInForce tif = TimeInForce::GTC) {
    // Risk checks
    if (!check_position_risk(symbol, side, quantity)) {
      emit_event(EventType::ORDER_REJECTED, 0, symbol, 0, quantity,
                 ErrorCode::RISK_LIMIT_EXCEEDED,
                 "Position size limit exceeded");
      return 0;
    }

    if (!check_order_count_risk()) {
      emit_event(EventType::ORDER_REJECTED, 0, symbol, 0, quantity,
                 ErrorCode::RISK_LIMIT_EXCEEDED, "Max open orders exceeded");
      return 0;
    }

    // Create order
    Order *order = order_pool_.allocate();
    if (!order) {
      emit_event(EventType::ORDER_REJECTED, 0, symbol, 0, quantity,
                 ErrorCode::INTERNAL_ERROR, "Order pool exhausted");
      return 0;
    }

    const OrderId id = next_order_id_.fetch_add(1, std::memory_order_relaxed);
    const Timestamp now = now_ns();

    order->id = id;
    order->created_at = now;
    order->updated_at = now;
    order->symbol = symbol;
    order->price = price;
    order->stop_price = stop_price;
    order->quantity = quantity;
    order->filled_qty = 0;
    order->side = side;
    order->type = type;
    order->tif = tif;
    order->status = OrderStatus::PENDING;

    {
      std::lock_guard<std::mutex> lock(orders_mutex_);
      active_orders_[id] = order;
    }

    emit_event(EventType::ORDER_SUBMITTED, id, symbol, price, quantity,
               ErrorCode::OK, "Order submitted");

    // For market orders, simulate immediate fill
    if (type == OrderType::MARKET) {
      simulate_fill(order, price != 0
                               ? price
                               : get_execution_price(symbol, side, quantity));
    }

    return id;
  }

  /**
   * @brief Cancel order
   */
  [[nodiscard]] bool cancel_order(OrderId id) {
    std::lock_guard<std::mutex> lock(orders_mutex_);

    auto it = active_orders_.find(id);
    if (it == active_orders_.end()) {
      return false;
    }

    Order *order = it->second;
    if (!order->is_active()) {
      return false;
    }

    order->status = OrderStatus::CANCELLED;
    order->updated_at = now_ns();

    emit_event(EventType::ORDER_CANCELLED, id, order->symbol, order->price,
               order->remaining(), ErrorCode::OK, "Order cancelled");

    active_orders_.erase(it);
    order_pool_.deallocate(order);

    return true;
  }

  /**
   * @brief Cancel all orders for symbol
   */
  size_t cancel_all_orders(Symbol symbol) {
    std::lock_guard<std::mutex> lock(orders_mutex_);

    size_t count = 0;
    std::vector<OrderId> to_cancel;

    for (const auto &[id, order] : active_orders_) {
      if (order->symbol == symbol && order->is_active()) {
        to_cancel.push_back(id);
      }
    }

    for (OrderId id : to_cancel) {
      auto it = active_orders_.find(id);
      if (it != active_orders_.end()) {
        Order *order = it->second;
        order->status = OrderStatus::CANCELLED;
        emit_event(EventType::ORDER_CANCELLED, id, order->symbol, order->price,
                   order->remaining(), ErrorCode::OK, "");
        order_pool_.deallocate(order);
        active_orders_.erase(it);
        ++count;
      }
    }

    return count;
  }

  // =========================================================================
  // Position Management
  // =========================================================================

  /**
   * @brief Get position for symbol
   */
  [[nodiscard]] const Position *get_position(Symbol symbol) const {
    auto it = positions_.find(std::string(symbol.view()));
    return it != positions_.end() ? &it->second : nullptr;
  }

  /**
   * @brief Close position for symbol
   */
  bool close_position(Symbol symbol) {
    auto it = positions_.find(std::string(symbol.view()));
    if (it == positions_.end() || it->second.is_flat()) {
      return false;
    }

    const Position &pos = it->second;
    const Side close_side = pos.is_long() ? Side::SELL : Side::BUY;
    const QuantityNano qty = std::abs(pos.quantity);

    (void)submit_order(symbol, close_side, OrderType::MARKET, qty);
    return true;
  }

  /**
   * @brief Close all positions
   */
  size_t close_all_positions() {
    size_t count = 0;
    for (auto &[sym, pos] : positions_) {
      if (!pos.is_flat()) {
        close_position(Symbol(sym));
        ++count;
      }
    }
    return count;
  }

  // =========================================================================
  // Market Data
  // =========================================================================

  /**
   * @brief Update orderbook
   */
  void update_orderbook(Symbol symbol, const Orderbook &book) {
    orderbooks_[std::string(symbol.view())] = book;
  }

  /**
   * @brief Get orderbook
   */
  [[nodiscard]] const Orderbook *get_orderbook(Symbol symbol) const {
    auto it = orderbooks_.find(std::string(symbol.view()));
    return it != orderbooks_.end() ? &it->second : nullptr;
  }

  // =========================================================================
  // Event Handling
  // =========================================================================

  void register_callback(EventCallback callback) {
    callbacks_.push_back(std::move(callback));
  }

  // =========================================================================
  // Accessors
  // =========================================================================

  [[nodiscard]] PriceMicro equity() const noexcept { return equity_; }
  [[nodiscard]] size_t open_order_count() const noexcept {
    return active_orders_.size();
  }
  [[nodiscard]] size_t position_count() const noexcept {
    return positions_.size();
  }
  [[nodiscard]] const RiskParams &risk_params() const noexcept {
    return risk_params_;
  }

  void set_equity(PriceMicro equity) noexcept { equity_ = equity; }

private:
  // =========================================================================
  // Internal Methods
  // =========================================================================

  bool check_position_risk(Symbol symbol, Side side, QuantityNano quantity) {
    // Check max position size
    const auto *pos = get_position(symbol);
    QuantityNano new_qty = quantity;

    if (pos) {
      new_qty = (side == Side::BUY) ? pos->quantity + quantity
                                    : pos->quantity - quantity;
    }

    const double notional = from_quantity_nano(std::abs(new_qty)) *
                            from_price_micro(get_current_price(symbol));
    const double equity_pct = notional / from_price_micro(equity_);

    return equity_pct <= risk_params_.max_position_size;
  }

  bool check_order_count_risk() {
    return static_cast<int>(active_orders_.size()) <
           risk_params_.max_open_orders;
  }

  PriceMicro get_current_price(Symbol symbol) {
    const auto *book = get_orderbook(symbol);
    return book ? book->mid_price() : to_price_micro(1.0);
  }

  PriceMicro get_execution_price(Symbol symbol, Side side, QuantityNano qty) {
    const auto *book = get_orderbook(symbol);
    if (book) {
      return book->estimate_execution_price(side, qty);
    }
    return to_price_micro(1.0);
  }

  void simulate_fill(Order *order, PriceMicro fill_price) {
    order->status = OrderStatus::FILLED;
    order->filled_qty = order->quantity;
    order->updated_at = now_ns();

    update_position(order->symbol, order->side, order->quantity, fill_price);

    emit_event(EventType::ORDER_FILLED, order->id, order->symbol, fill_price,
               order->quantity, ErrorCode::OK, "Order filled");

    {
      std::lock_guard<std::mutex> lock(orders_mutex_);
      active_orders_.erase(order->id);
    }
    order_pool_.deallocate(order);
  }

  void update_position(Symbol symbol, Side side, QuantityNano qty,
                       PriceMicro price) {
    std::string_view sym = symbol.view();
    auto it = positions_.find(std::string(sym));

    if (it == positions_.end()) {
      // New position
      Position pos{};
      pos.symbol = symbol;
      pos.quantity = (side == Side::BUY) ? qty : -qty;
      pos.avg_entry_price = price;
      pos.opened_at = now_ns();
      pos.updated_at = now_ns();
      positions_[std::string(sym)] = pos;

      emit_event(EventType::POSITION_OPENED, 0, symbol, price, qty,
                 ErrorCode::OK, "Position opened");
    } else {
      Position &pos = it->second;
      const QuantityNano delta = (side == Side::BUY) ? qty : -qty;
      const QuantityNano old_qty = pos.quantity;

      // Update average entry price
      if ((old_qty >= 0 && delta > 0) || (old_qty <= 0 && delta < 0)) {
        // Adding to position
        const auto total_notional =
            pos.avg_entry_price * std::abs(old_qty) / QUANTITY_SCALE +
            price * std::abs(delta) / QUANTITY_SCALE;
        pos.quantity += delta;
        if (pos.quantity != 0) {
          pos.avg_entry_price =
              total_notional * QUANTITY_SCALE / std::abs(pos.quantity);
        }
      } else {
        // Reducing position
        const QuantityNano closed =
            std::min(std::abs(old_qty), std::abs(delta));
        const PriceMicro pnl =
            (price - pos.avg_entry_price) * closed / QUANTITY_SCALE;
        pos.realized_pnl += (old_qty > 0) ? pnl : -pnl;
        pos.quantity += delta;
      }

      pos.updated_at = now_ns();

      if (pos.is_flat()) {
        emit_event(EventType::POSITION_CLOSED, 0, symbol, price, qty,
                   ErrorCode::OK, "Position closed");
        positions_.erase(it);
      } else {
        emit_event(EventType::POSITION_UPDATED, 0, symbol, price, qty,
                   ErrorCode::OK, "Position updated");
      }
    }
  }

  void emit_event(EventType type, OrderId id, Symbol symbol, PriceMicro price,
                  QuantityNano qty, ErrorCode error, const char *msg) {
    ExecutionEvent event{};
    event.type = type;
    event.order_id = id;
    event.symbol = symbol;
    event.price = price;
    event.quantity = qty;
    event.timestamp = now_ns();
    event.error = error;
    if (msg) {
      std::strncpy(event.message, msg, sizeof(event.message) - 1);
    }

    for (const auto &callback : callbacks_) {
      callback(event);
    }
  }

  // =========================================================================
  // Data Members
  // =========================================================================

  RiskParams risk_params_;
  std::atomic<OrderId> next_order_id_;
  std::atomic<PriceMicro> equity_;
  std::atomic<bool> is_running_;

  ObjectPool<Order, 10000> order_pool_;
  std::unordered_map<OrderId, Order *> active_orders_;
  std::mutex orders_mutex_;

  std::unordered_map<std::string, Position> positions_;
  std::unordered_map<std::string, Orderbook> orderbooks_;

  std::vector<EventCallback> callbacks_;
};

} // namespace godbrain
