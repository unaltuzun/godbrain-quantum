/**
 * @file types.hpp
 * @brief GODBRAIN Core Type Definitions
 * 
 * Military-grade type definitions for high-performance trading.
 * All types are cache-line aligned and optimized for minimal latency.
 * 
 * @author GODBRAIN Team
 * @version 1.0.0
 */

#pragma once

#include <cstdint>
#include <atomic>
#include <chrono>
#include <array>
#include <string_view>

namespace godbrain {

// =============================================================================
// Hardware Constants
// =============================================================================

constexpr size_t CACHE_LINE_SIZE = 64;
constexpr size_t PAGE_SIZE = 4096;

// Alignment macro for cache-line optimization
#define GODBRAIN_CACHE_ALIGNED alignas(godbrain::CACHE_LINE_SIZE)

// =============================================================================
// Time Types - Nanosecond Precision
// =============================================================================

using Timestamp = uint64_t;  // Nanoseconds since epoch
using Duration = int64_t;    // Nanoseconds duration

[[nodiscard]] inline Timestamp now_ns() noexcept {
    auto duration = std::chrono::steady_clock::now().time_since_epoch();
    return static_cast<Timestamp>(
        std::chrono::duration_cast<std::chrono::nanoseconds>(duration).count()
    );
}

[[nodiscard]] inline Timestamp epoch_ns() noexcept {
    auto duration = std::chrono::system_clock::now().time_since_epoch();
    return static_cast<Timestamp>(
        std::chrono::duration_cast<std::chrono::nanoseconds>(duration).count()
    );
}

// =============================================================================
// Price & Quantity - Fixed Point for Precision
// =============================================================================

// Price in micro-units (1 USD = 1,000,000 micro-units)
using PriceMicro = int64_t;
// Quantity in nano-units (1 unit = 1,000,000,000 nano-units)
using QuantityNano = int64_t;

constexpr int64_t PRICE_SCALE = 1'000'000;
constexpr int64_t QUANTITY_SCALE = 1'000'000'000;

[[nodiscard]] constexpr PriceMicro to_price_micro(double price) noexcept {
    return static_cast<PriceMicro>(price * PRICE_SCALE);
}

[[nodiscard]] constexpr double from_price_micro(PriceMicro price) noexcept {
    return static_cast<double>(price) / PRICE_SCALE;
}

[[nodiscard]] constexpr QuantityNano to_quantity_nano(double qty) noexcept {
    return static_cast<QuantityNano>(qty * QUANTITY_SCALE);
}

[[nodiscard]] constexpr double from_quantity_nano(QuantityNano qty) noexcept {
    return static_cast<double>(qty) / QUANTITY_SCALE;
}

// =============================================================================
// Order Side & Type
// =============================================================================

enum class Side : uint8_t {
    BUY = 0,
    SELL = 1
};

enum class OrderType : uint8_t {
    MARKET = 0,
    LIMIT = 1,
    STOP_MARKET = 2,
    STOP_LIMIT = 3,
    TRAILING_STOP = 4
};

enum class TimeInForce : uint8_t {
    GTC = 0,  // Good 'til Canceled
    IOC = 1,  // Immediate or Cancel
    FOK = 2,  // Fill or Kill
    GTD = 3   // Good 'til Date
};

enum class OrderStatus : uint8_t {
    PENDING = 0,
    OPEN = 1,
    PARTIALLY_FILLED = 2,
    FILLED = 3,
    CANCELLED = 4,
    REJECTED = 5,
    EXPIRED = 6
};

// =============================================================================
// Symbol - Fixed Size for Cache Efficiency
// =============================================================================

struct Symbol {
    std::array<char, 16> data{};
    
    Symbol() = default;
    
    explicit Symbol(std::string_view sv) noexcept {
        const size_t len = std::min(sv.size(), data.size() - 1);
        for (size_t i = 0; i < len; ++i) {
            data[i] = sv[i];
        }
    }
    
    [[nodiscard]] std::string_view view() const noexcept {
        return std::string_view(data.data());
    }
    
    bool operator==(const Symbol& other) const noexcept {
        return data == other.data;
    }
};

// =============================================================================
// Market Tick - Cache-Line Aligned
// =============================================================================

struct GODBRAIN_CACHE_ALIGNED MarketTick {
    Timestamp timestamp;      // 8 bytes
    Symbol symbol;            // 16 bytes
    PriceMicro bid;           // 8 bytes
    PriceMicro ask;           // 8 bytes
    PriceMicro last;          // 8 bytes
    QuantityNano bid_size;    // 8 bytes
    QuantityNano ask_size;    // 8 bytes
    uint64_t sequence;        // 8 bytes  = 72 bytes total, padded to 128
    
    [[nodiscard]] double spread() const noexcept {
        return from_price_micro(ask - bid);
    }
    
    [[nodiscard]] double mid_price() const noexcept {
        return from_price_micro((bid + ask) / 2);
    }
};

static_assert(sizeof(MarketTick) <= 2 * CACHE_LINE_SIZE, 
    "MarketTick must fit in 2 cache lines");

// =============================================================================
// Order - Cache-Line Aligned
// =============================================================================

using OrderId = uint64_t;

struct GODBRAIN_CACHE_ALIGNED Order {
    OrderId id;               // 8 bytes
    Timestamp created_at;     // 8 bytes
    Timestamp updated_at;     // 8 bytes
    Symbol symbol;            // 16 bytes
    PriceMicro price;         // 8 bytes
    PriceMicro stop_price;    // 8 bytes
    QuantityNano quantity;    // 8 bytes
    QuantityNano filled_qty;  // 8 bytes
    Side side;                // 1 byte
    OrderType type;           // 1 byte
    TimeInForce tif;          // 1 byte
    OrderStatus status;       // 1 byte
    uint8_t padding[4];       // 4 bytes padding
    
    [[nodiscard]] QuantityNano remaining() const noexcept {
        return quantity - filled_qty;
    }
    
    [[nodiscard]] bool is_active() const noexcept {
        return status == OrderStatus::OPEN || 
               status == OrderStatus::PARTIALLY_FILLED;
    }
};

static_assert(sizeof(Order) <= 2 * CACHE_LINE_SIZE,
    "Order must fit in 2 cache lines");

// =============================================================================
// Position
// =============================================================================

struct GODBRAIN_CACHE_ALIGNED Position {
    Symbol symbol;                  // 16 bytes
    QuantityNano quantity;          // 8 bytes (positive=long, negative=short)
    PriceMicro avg_entry_price;     // 8 bytes
    PriceMicro unrealized_pnl;      // 8 bytes
    PriceMicro realized_pnl;        // 8 bytes
    Timestamp opened_at;            // 8 bytes
    Timestamp updated_at;           // 8 bytes
    
    [[nodiscard]] bool is_long() const noexcept { return quantity > 0; }
    [[nodiscard]] bool is_short() const noexcept { return quantity < 0; }
    [[nodiscard]] bool is_flat() const noexcept { return quantity == 0; }
    
    [[nodiscard]] double notional_value() const noexcept {
        return from_price_micro(avg_entry_price) * 
               from_quantity_nano(std::abs(quantity));
    }
};

// =============================================================================
// Risk Parameters
// =============================================================================

struct RiskParams {
    double max_position_size = 0.1;      // 10% of equity
    double max_drawdown = 0.05;          // 5% max drawdown
    double stop_loss_percent = 0.02;     // 2% stop loss
    double take_profit_percent = 0.03;   // 3% take profit
    int max_open_orders = 10;
    int max_daily_trades = 100;
};

// =============================================================================
// Error Codes
// =============================================================================

enum class ErrorCode : int32_t {
    OK = 0,
    INVALID_SYMBOL = -1,
    INVALID_QUANTITY = -2,
    INVALID_PRICE = -3,
    INSUFFICIENT_MARGIN = -4,
    RISK_LIMIT_EXCEEDED = -5,
    ORDER_NOT_FOUND = -6,
    POSITION_NOT_FOUND = -7,
    NETWORK_ERROR = -8,
    TIMEOUT = -9,
    RATE_LIMITED = -10,
    INTERNAL_ERROR = -100
};

} // namespace godbrain
