/**
 * @file simd.hpp
 * @brief SIMD-Optimized Computations
 *
 * AVX2/AVX-512 optimized functions for high-performance calculations.
 * Falls back to scalar on unsupported platforms.
 *
 * @author GODBRAIN Team
 * @version 1.0.0
 */

#pragma once

#include "godbrain/types.hpp"
#include <algorithm>
#include <cmath>
#include <cstddef>


#if defined(GODBRAIN_AVX512)
#include <immintrin.h>
#define GODBRAIN_SIMD_WIDTH 16
#elif defined(GODBRAIN_AVX2)
#include <immintrin.h>
#define GODBRAIN_SIMD_WIDTH 8
#else
#define GODBRAIN_SIMD_WIDTH 1
#endif

namespace godbrain {
namespace simd {

// =============================================================================
// Statistics
// =============================================================================

/**
 * @brief Calculate sum of array (SIMD optimized)
 */
inline double sum(const double *data, size_t n) noexcept {
#if defined(GODBRAIN_AVX2)
  __m256d vsum = _mm256_setzero_pd();
  size_t i = 0;

  for (; i + 4 <= n; i += 4) {
    __m256d v = _mm256_loadu_pd(data + i);
    vsum = _mm256_add_pd(vsum, v);
  }

  // Horizontal sum
  __m128d vlow = _mm256_castpd256_pd128(vsum);
  __m128d vhigh = _mm256_extractf128_pd(vsum, 1);
  vlow = _mm_add_pd(vlow, vhigh);
  __m128d vh = _mm_unpackhi_pd(vlow, vlow);
  vlow = _mm_add_sd(vlow, vh);

  double result = _mm_cvtsd_f64(vlow);

  // Handle remaining
  for (; i < n; ++i) {
    result += data[i];
  }

  return result;
#else
  double result = 0.0;
  for (size_t i = 0; i < n; ++i) {
    result += data[i];
  }
  return result;
#endif
}

/**
 * @brief Calculate mean of array
 */
inline double mean(const double *data, size_t n) noexcept {
  if (n == 0)
    return 0.0;
  return sum(data, n) / static_cast<double>(n);
}

/**
 * @brief Calculate variance (SIMD optimized)
 */
inline double variance(const double *data, size_t n) noexcept {
  if (n <= 1)
    return 0.0;

  const double m = mean(data, n);

#if defined(GODBRAIN_AVX2)
  __m256d vmean = _mm256_set1_pd(m);
  __m256d vsum = _mm256_setzero_pd();
  size_t i = 0;

  for (; i + 4 <= n; i += 4) {
    __m256d v = _mm256_loadu_pd(data + i);
    __m256d diff = _mm256_sub_pd(v, vmean);
    vsum = _mm256_fmadd_pd(diff, diff, vsum);
  }

  // Horizontal sum
  __m128d vlow = _mm256_castpd256_pd128(vsum);
  __m128d vhigh = _mm256_extractf128_pd(vsum, 1);
  vlow = _mm_add_pd(vlow, vhigh);
  __m128d vh = _mm_unpackhi_pd(vlow, vlow);
  vlow = _mm_add_sd(vlow, vh);

  double result = _mm_cvtsd_f64(vlow);

  for (; i < n; ++i) {
    double diff = data[i] - m;
    result += diff * diff;
  }

  return result / static_cast<double>(n - 1);
#else
  double result = 0.0;
  for (size_t i = 0; i < n; ++i) {
    double diff = data[i] - m;
    result += diff * diff;
  }
  return result / static_cast<double>(n - 1);
#endif
}

/**
 * @brief Calculate standard deviation
 */
inline double stddev(const double *data, size_t n) noexcept {
  return std::sqrt(variance(data, n));
}

/**
 * @brief Calculate min and max
 */
inline void minmax(const double *data, size_t n, double &min_val,
                   double &max_val) noexcept {
  if (n == 0) {
    min_val = max_val = 0.0;
    return;
  }

#if defined(GODBRAIN_AVX2)
  __m256d vmin = _mm256_set1_pd(data[0]);
  __m256d vmax = vmin;
  size_t i = 1;

  for (; i + 4 <= n; i += 4) {
    __m256d v = _mm256_loadu_pd(data + i);
    vmin = _mm256_min_pd(vmin, v);
    vmax = _mm256_max_pd(vmax, v);
  }

  // Reduce
  double mins[4], maxs[4];
  _mm256_storeu_pd(mins, vmin);
  _mm256_storeu_pd(maxs, vmax);

  min_val = std::min({mins[0], mins[1], mins[2], mins[3]});
  max_val = std::max({maxs[0], maxs[1], maxs[2], maxs[3]});

  for (; i < n; ++i) {
    min_val = std::min(min_val, data[i]);
    max_val = std::max(max_val, data[i]);
  }
#else
  min_val = max_val = data[0];
  for (size_t i = 1; i < n; ++i) {
    min_val = std::min(min_val, data[i]);
    max_val = std::max(max_val, data[i]);
  }
#endif
}

// =============================================================================
// Returns
// =============================================================================

/**
 * @brief Calculate returns from prices
 */
inline void calculate_returns(const double *prices, double *returns,
                              size_t n) noexcept {
  if (n < 2)
    return;

#if defined(GODBRAIN_AVX2)
  size_t i = 0;
  for (; i + 4 < n; i += 4) {
    __m256d p0 = _mm256_loadu_pd(prices + i);
    __m256d p1 = _mm256_loadu_pd(prices + i + 1);
    __m256d ret = _mm256_div_pd(_mm256_sub_pd(p1, p0), p0);
    _mm256_storeu_pd(returns + i, ret);
  }

  for (; i < n - 1; ++i) {
    returns[i] = (prices[i + 1] - prices[i]) / prices[i];
  }
#else
  for (size_t i = 0; i < n - 1; ++i) {
    returns[i] = (prices[i + 1] - prices[i]) / prices[i];
  }
#endif
}

/**
 * @brief Calculate Sharpe ratio
 */
inline double sharpe_ratio(const double *returns, size_t n,
                           double risk_free_rate = 0.0,
                           double annualization = 252.0) noexcept {
  if (n < 2)
    return 0.0;

  const double m = mean(returns, n);
  const double s = stddev(returns, n);

  if (s == 0.0)
    return 0.0;

  return (m - risk_free_rate / annualization) / s * std::sqrt(annualization);
}

/**
 * @brief Calculate maximum drawdown
 */
inline double max_drawdown(const double *equity, size_t n) noexcept {
  if (n < 2)
    return 0.0;

  double peak = equity[0];
  double max_dd = 0.0;

  for (size_t i = 1; i < n; ++i) {
    peak = std::max(peak, equity[i]);
    const double dd = (peak - equity[i]) / peak;
    max_dd = std::max(max_dd, dd);
  }

  return max_dd;
}

// =============================================================================
// Orderbook SIMD
// =============================================================================

/**
 * @brief Calculate total liquidity from orderbook levels (SIMD)
 */
inline int64_t total_liquidity(const PriceLevel *levels, size_t n) noexcept {
#if defined(GODBRAIN_AVX2)
  __m256i vsum = _mm256_setzero_si256();
  size_t i = 0;

  // Process 4 levels at a time (24 bytes each, 96 bytes = ~2 cache lines)
  for (; i + 4 <= n; i += 4) {
    // Load quantities (offset 8 bytes in each level)
    __m256i q =
        _mm256_set_epi64x(levels[i + 3].quantity, levels[i + 2].quantity,
                          levels[i + 1].quantity, levels[i + 0].quantity);
    vsum = _mm256_add_epi64(vsum, q);
  }

  // Horizontal sum
  int64_t result = 0;
  int64_t tmp[4];
  _mm256_storeu_si256(reinterpret_cast<__m256i *>(tmp), vsum);
  for (int j = 0; j < 4; ++j)
    result += tmp[j];

  // Handle remaining
  for (; i < n; ++i) {
    result += levels[i].quantity;
  }

  return result;
#else
  int64_t result = 0;
  for (size_t i = 0; i < n; ++i) {
    result += levels[i].quantity;
  }
  return result;
#endif
}

/**
 * @brief Calculate VWAP from orderbook levels (SIMD)
 */
inline double vwap(const PriceLevel *levels, size_t n) noexcept {
  if (n == 0)
    return 0.0;

  double weighted_sum = 0.0;
  int64_t total_qty = 0;

  for (size_t i = 0; i < n; ++i) {
    weighted_sum += from_price_micro(levels[i].price) *
                    from_quantity_nano(levels[i].quantity);
    total_qty += levels[i].quantity;
  }

  return total_qty > 0 ? weighted_sum / from_quantity_nano(total_qty) : 0.0;
}

} // namespace simd
} // namespace godbrain
