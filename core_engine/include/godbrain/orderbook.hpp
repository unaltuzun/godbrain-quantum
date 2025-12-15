/**
 * @file orderbook.hpp
 * @brief High-Performance Orderbook
 *
 * SIMD-optimized orderbook with preallocated price levels.
 * Supports Level 2 market data with O(1) best bid/ask access.
 *
 * @author GODBRAIN Team
 * @version 1.0.0
 */

#pragma once

#include "godbrain/types.hpp"
#include <algorithm>
#include <array>
#include <cstring>


namespace godbrain {

constexpr size_t MAX_ORDERBOOK_LEVELS = 25;

/**
 * @brief Single Price Level
 */
struct PriceLevel {
  PriceMicro price = 0;
  QuantityNano quantity = 0;
  uint32_t order_count = 0;
  uint32_t padding = 0;
};

static_assert(sizeof(PriceLevel) == 24, "PriceLevel size mismatch");

/**
 * @brief High-Performance Orderbook
 *
 * Features:
 * - O(1) best bid/ask access
 * - SIMD-ready array layout
 * - Cache-friendly memory layout
 * - Lock-free updates
 */
class Orderbook {
public:
  Orderbook() = default;

  /**
   * @brief Update entire orderbook snapshot
   */
  void update_snapshot(const PriceLevel *bids, size_t bid_count,
                       const PriceLevel *asks, size_t ask_count,
                       uint64_t sequence, Timestamp timestamp) noexcept {
    bid_count_ = std::min(bid_count, MAX_ORDERBOOK_LEVELS);
    ask_count_ = std::min(ask_count, MAX_ORDERBOOK_LEVELS);

    std::memcpy(bids_.data(), bids, bid_count_ * sizeof(PriceLevel));
    std::memcpy(asks_.data(), asks, ask_count_ * sizeof(PriceLevel));

    sequence_ = sequence;
    timestamp_ = timestamp;
  }

  /**
   * @brief Update single bid level
   */
  void update_bid(size_t level, PriceMicro price, QuantityNano qty) noexcept {
    if (level < MAX_ORDERBOOK_LEVELS) {
      bids_[level].price = price;
      bids_[level].quantity = qty;
      if (level >= bid_count_)
        bid_count_ = level + 1;
    }
  }

  /**
   * @brief Update single ask level
   */
  void update_ask(size_t level, PriceMicro price, QuantityNano qty) noexcept {
    if (level < MAX_ORDERBOOK_LEVELS) {
      asks_[level].price = price;
      asks_[level].quantity = qty;
      if (level >= ask_count_)
        ask_count_ = level + 1;
    }
  }

  // ==========================================================================
  // Accessors
  // ==========================================================================

  [[nodiscard]] PriceMicro best_bid() const noexcept {
    return bid_count_ > 0 ? bids_[0].price : 0;
  }

  [[nodiscard]] PriceMicro best_ask() const noexcept {
    return ask_count_ > 0 ? asks_[0].price : 0;
  }

  [[nodiscard]] PriceMicro mid_price() const noexcept {
    return (best_bid() + best_ask()) / 2;
  }

  [[nodiscard]] PriceMicro spread() const noexcept {
    return best_ask() - best_bid();
  }

  [[nodiscard]] double spread_percent() const noexcept {
    const auto mid = mid_price();
    if (mid == 0)
      return 0.0;
    return from_price_micro(spread()) / from_price_micro(mid) * 100.0;
  }

  [[nodiscard]] QuantityNano best_bid_size() const noexcept {
    return bid_count_ > 0 ? bids_[0].quantity : 0;
  }

  [[nodiscard]] QuantityNano best_ask_size() const noexcept {
    return ask_count_ > 0 ? asks_[0].quantity : 0;
  }

  /**
   * @brief Get bid at level (0 = best)
   */
  [[nodiscard]] const PriceLevel &bid(size_t level) const noexcept {
    return bids_[std::min(level, MAX_ORDERBOOK_LEVELS - 1)];
  }

  /**
   * @brief Get ask at level (0 = best)
   */
  [[nodiscard]] const PriceLevel &ask(size_t level) const noexcept {
    return asks_[std::min(level, MAX_ORDERBOOK_LEVELS - 1)];
  }

  [[nodiscard]] size_t bid_depth() const noexcept { return bid_count_; }
  [[nodiscard]] size_t ask_depth() const noexcept { return ask_count_; }
  [[nodiscard]] uint64_t sequence() const noexcept { return sequence_; }
  [[nodiscard]] Timestamp timestamp() const noexcept { return timestamp_; }

  // ==========================================================================
  // Analysis
  // ==========================================================================

  /**
   * @brief Calculate total bid liquidity up to N levels
   */
  [[nodiscard]] QuantityNano
  total_bid_liquidity(size_t levels = MAX_ORDERBOOK_LEVELS) const noexcept {
    QuantityNano total = 0;
    const size_t n = std::min(levels, bid_count_);
    for (size_t i = 0; i < n; ++i) {
      total += bids_[i].quantity;
    }
    return total;
  }

  /**
   * @brief Calculate total ask liquidity up to N levels
   */
  [[nodiscard]] QuantityNano
  total_ask_liquidity(size_t levels = MAX_ORDERBOOK_LEVELS) const noexcept {
    QuantityNano total = 0;
    const size_t n = std::min(levels, ask_count_);
    for (size_t i = 0; i < n; ++i) {
      total += asks_[i].quantity;
    }
    return total;
  }

  /**
   * @brief Calculate order imbalance (-1 to +1)
   * Positive = more bid pressure, Negative = more ask pressure
   */
  [[nodiscard]] double imbalance(size_t levels = 5) const noexcept {
    const auto bid_liq = total_bid_liquidity(levels);
    const auto ask_liq = total_ask_liquidity(levels);
    const auto total = bid_liq + ask_liq;

    if (total == 0)
      return 0.0;
    return static_cast<double>(bid_liq - ask_liq) / static_cast<double>(total);
  }

  /**
   * @brief Estimate execution price for given quantity
   */
  [[nodiscard]] PriceMicro
  estimate_execution_price(Side side, QuantityNano qty) const noexcept {
    const auto &levels = (side == Side::BUY) ? asks_ : bids_;
    const size_t count = (side == Side::BUY) ? ask_count_ : bid_count_;

    QuantityNano remaining = qty;
    PriceMicro weighted_sum = 0;
    QuantityNano filled = 0;

    for (size_t i = 0; i < count && remaining > 0; ++i) {
      const QuantityNano fill = std::min(remaining, levels[i].quantity);
      weighted_sum += levels[i].price * fill / QUANTITY_SCALE;
      filled += fill;
      remaining -= fill;
    }

    return filled > 0 ? weighted_sum * QUANTITY_SCALE / filled : 0;
  }

  /**
   * @brief Calculate slippage for given quantity
   */
  [[nodiscard]] double estimate_slippage(Side side,
                                         QuantityNano qty) const noexcept {
    const PriceMicro exec_price = estimate_execution_price(side, qty);
    const PriceMicro best = (side == Side::BUY) ? best_ask() : best_bid();

    if (best == 0)
      return 0.0;

    const double diff = from_price_micro(std::abs(exec_price - best));
    return diff / from_price_micro(best) * 100.0;
  }

  // ==========================================================================
  // Raw Data Access (for SIMD)
  // ==========================================================================

  [[nodiscard]] const PriceLevel *bids_data() const noexcept {
    return bids_.data();
  }
  [[nodiscard]] const PriceLevel *asks_data() const noexcept {
    return asks_.data();
  }

private:
  GODBRAIN_CACHE_ALIGNED std::array<PriceLevel, MAX_ORDERBOOK_LEVELS> bids_;
  GODBRAIN_CACHE_ALIGNED std::array<PriceLevel, MAX_ORDERBOOK_LEVELS> asks_;
  size_t bid_count_ = 0;
  size_t ask_count_ = 0;
  uint64_t sequence_ = 0;
  Timestamp timestamp_ = 0;
};

} // namespace godbrain
