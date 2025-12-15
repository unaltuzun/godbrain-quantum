/**
 * @file memory_pool.hpp
 * @brief Zero-Allocation Memory Pool
 *
 * Pre-allocated memory pool for eliminating runtime allocations.
 * Critical for maintaining consistent latency.
 *
 * @author GODBRAIN Team
 * @version 1.0.0
 */

#pragma once

#include "godbrain/types.hpp"
#include <array>
#include <atomic>
#include <cstdint>
#include <memory>
#include <new>


namespace godbrain {

/**
 * @brief Fixed-Size Object Pool
 *
 * Lock-free object pool with O(1) allocation and deallocation.
 * Zero runtime allocations after initialization.
 *
 * @tparam T Object type
 * @tparam PoolSize Number of pre-allocated objects
 */
template <typename T, size_t PoolSize = 1024> class ObjectPool {
  static_assert(PoolSize > 0, "Pool size must be positive");

  struct Node {
    std::atomic<Node *> next;
    alignas(alignof(T)) std::byte storage[sizeof(T)];
  };

public:
  ObjectPool() noexcept {
    // Initialize free list
    for (size_t i = 0; i < PoolSize - 1; ++i) {
      nodes_[i].next.store(&nodes_[i + 1], std::memory_order_relaxed);
    }
    nodes_[PoolSize - 1].next.store(nullptr, std::memory_order_relaxed);
    free_list_.store(&nodes_[0], std::memory_order_release);
  }

  ~ObjectPool() {
    // Objects must be explicitly released before destruction
  }

  /**
   * @brief Allocate object from pool
   * @return Pointer to object, nullptr if pool exhausted
   */
  [[nodiscard]] T *allocate() noexcept {
    Node *node = pop_free();
    if (!node)
      return nullptr;

    ++allocated_;
    return new (node->storage) T();
  }

  /**
   * @brief Allocate and construct with arguments
   */
  template <typename... Args>
  [[nodiscard]] T *allocate(Args &&...args) noexcept {
    Node *node = pop_free();
    if (!node)
      return nullptr;

    ++allocated_;
    return new (node->storage) T(std::forward<Args>(args)...);
  }

  /**
   * @brief Return object to pool
   */
  void deallocate(T *ptr) noexcept {
    if (!ptr)
      return;

    ptr->~T();

    // Find node from pointer
    auto *node = reinterpret_cast<Node *>(reinterpret_cast<std::byte *>(ptr) -
                                          offsetof(Node, storage));

    push_free(node);
    --allocated_;
  }

  /**
   * @brief Get number of allocated objects
   */
  [[nodiscard]] size_t allocated() const noexcept {
    return allocated_.load(std::memory_order_relaxed);
  }

  /**
   * @brief Get number of available slots
   */
  [[nodiscard]] size_t available() const noexcept {
    return PoolSize - allocated();
  }

  /**
   * @brief Get total pool capacity
   */
  [[nodiscard]] static constexpr size_t capacity() noexcept { return PoolSize; }

private:
  Node *pop_free() noexcept {
    Node *head = free_list_.load(std::memory_order_acquire);
    while (head) {
      Node *next = head->next.load(std::memory_order_relaxed);
      if (free_list_.compare_exchange_weak(head, next,
                                           std::memory_order_release,
                                           std::memory_order_acquire)) {
        return head;
      }
    }
    return nullptr;
  }

  void push_free(Node *node) noexcept {
    Node *head = free_list_.load(std::memory_order_relaxed);
    do {
      node->next.store(head, std::memory_order_relaxed);
    } while (!free_list_.compare_exchange_weak(
        head, node, std::memory_order_release, std::memory_order_relaxed));
  }

  GODBRAIN_CACHE_ALIGNED std::atomic<Node *> free_list_;
  GODBRAIN_CACHE_ALIGNED std::atomic<size_t> allocated_{0};
  std::array<Node, PoolSize> nodes_;
};

/**
 * @brief Arena Allocator for Sequential Allocations
 *
 * Ultra-fast bump allocator for temporary/frame-based allocations.
 * Reset once per frame/tick for zero deallocation overhead.
 */
template <size_t Size = 1024 * 1024> // 1MB default
class Arena {
public:
  Arena() noexcept : offset_(0) {}

  /**
   * @brief Allocate aligned memory
   */
  template <typename T> [[nodiscard]] T *allocate(size_t count = 1) noexcept {
    constexpr size_t alignment = alignof(T);
    const size_t size = sizeof(T) * count;

    // Align offset
    size_t aligned_offset = (offset_ + alignment - 1) & ~(alignment - 1);

    if (aligned_offset + size > Size) {
      return nullptr; // Arena exhausted
    }

    T *ptr = reinterpret_cast<T *>(buffer_.data() + aligned_offset);
    offset_ = aligned_offset + size;

    return ptr;
  }

  /**
   * @brief Reset arena (no destructors called!)
   */
  void reset() noexcept { offset_ = 0; }

  /**
   * @brief Get used bytes
   */
  [[nodiscard]] size_t used() const noexcept { return offset_; }

  /**
   * @brief Get remaining bytes
   */
  [[nodiscard]] size_t remaining() const noexcept { return Size - offset_; }

private:
  GODBRAIN_CACHE_ALIGNED std::array<std::byte, Size> buffer_;
  size_t offset_;
};

} // namespace godbrain
