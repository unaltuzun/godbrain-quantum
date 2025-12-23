/**
 * @file godbrain.hpp
 * @brief GODBRAIN C++ Core Engine - Main Header
 *
 * Single header to include all GODBRAIN components.
 * Military/NASA grade high-performance trading engine.
 *
 * @author GODBRAIN Team
 * @version 1.0.0
 *
 * @code
 * #include <godbrain/godbrain.hpp>
 *
 * using namespace godbrain;
 *
 * int main() {
 *     ExecutionEngine engine;
 *
 *     // Submit order
 *     OrderId id = engine.submit_order(
 *         Symbol("DOGE/USDT"),
 *         Side::BUY,
 *         OrderType::MARKET,
 *         to_quantity_nano(1000.0)
 *     );
 *
 *     return 0;
 * }
 * @endcode
 */

#pragma once

// Core types
#include "godbrain/types.hpp"

// Data structures
#include "godbrain/lock_free_queue.hpp"
#include "godbrain/memory_pool.hpp"
#include "godbrain/orderbook.hpp"

// Execution
#include "godbrain/execution_engine.hpp"

// SIMD optimizations
#include "godbrain/simd.hpp"

namespace godbrain {

/**
 * @brief GODBRAIN version info
 */
struct Version {
  static constexpr int MAJOR = 1;
  static constexpr int MINOR = 0;
  static constexpr int PATCH = 0;
  static constexpr const char *STRING = "1.0.0";
  static constexpr const char *CODENAME = "QUANTUM";
};

/**
 * @brief Print GODBRAIN banner
 */
inline void print_banner() {
  printf(R"(
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║   ██████╗  ██████╗ ██████╗ ██████╗ ██████╗  █████╗ ██╗███╗   ██╗              ║
║  ██╔════╝ ██╔═══██╗██╔══██╗██╔══██╗██╔══██╗██╔══██╗██║████╗  ██║              ║
║  ██║  ███╗██║   ██║██║  ██║██████╔╝██████╔╝███████║██║██╔██╗ ██║              ║
║  ██║   ██║██║   ██║██║  ██║██╔══██╗██╔══██╗██╔══██║██║██║╚██╗██║              ║
║  ╚██████╔╝╚██████╔╝██████╔╝██████╔╝██║  ██║██║  ██║██║██║ ╚████║              ║
║   ╚═════╝  ╚═════╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝              ║
║                                                                               ║
║                    C++ HIGH-PERFORMANCE TRADING ENGINE                        ║
║                          Version %s (%s)                             ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
)",
         Version::STRING, Version::CODENAME);
}

/**
 * @brief Initialize GODBRAIN engine
 */
inline bool initialize() {
  // CPU feature detection
#if defined(GODBRAIN_AVX512)
  printf("[GODBRAIN] SIMD: AVX-512 enabled\n");
#elif defined(GODBRAIN_AVX2)
  printf("[GODBRAIN] SIMD: AVX2 enabled\n");
#else
  printf("[GODBRAIN] SIMD: Scalar fallback\n");
#endif

  printf("[GODBRAIN] Cache line size: %zu bytes\n", CACHE_LINE_SIZE);
  printf("[GODBRAIN] Lock-free queue capacity: %zu\n",
         SPSCQueue<int>::capacity());

  return true;
}

} // namespace godbrain
