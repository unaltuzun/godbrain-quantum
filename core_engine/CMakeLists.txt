# GODBRAIN C++ Core Engine
# CMake Build System - Military/NASA Grade

cmake_minimum_required(VERSION 3.20)
project(godbrain_core 
    VERSION 1.0.0
    LANGUAGES CXX C
    DESCRIPTION "GODBRAIN High-Performance Trading Core"
)

# =============================================================================
# C++ Standard & Compiler Settings
# =============================================================================
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Position Independent Code for shared library
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# =============================================================================
# Build Types
# =============================================================================
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

set(CMAKE_CXX_FLAGS_DEBUG "-g -O0 -DDEBUG -fsanitize=address,undefined")
set(CMAKE_CXX_FLAGS_RELEASE "-O3 -DNDEBUG -march=native -mtune=native -flto")
set(CMAKE_CXX_FLAGS_RELWITHDEBINFO "-O2 -g -DNDEBUG -march=native")

# =============================================================================
# Compiler Warnings - Maximum Strictness
# =============================================================================
add_compile_options(
    -Wall -Wextra -Wpedantic
    -Werror
    -Wconversion
    -Wshadow
    -Wnon-virtual-dtor
    -Wold-style-cast
    -Wcast-align
    -Wunused
    -Woverloaded-virtual
    -Wnull-dereference
    -Wdouble-promotion
    -Wformat=2
    -Wimplicit-fallthrough
)

# =============================================================================
# SIMD Detection
# =============================================================================
include(CheckCXXCompilerFlag)

check_cxx_compiler_flag("-mavx2" COMPILER_SUPPORTS_AVX2)
check_cxx_compiler_flag("-mavx512f" COMPILER_SUPPORTS_AVX512)

if(COMPILER_SUPPORTS_AVX512)
    add_compile_definitions(GODBRAIN_AVX512)
    message(STATUS "AVX-512 support detected")
elseif(COMPILER_SUPPORTS_AVX2)
    add_compile_definitions(GODBRAIN_AVX2)
    message(STATUS "AVX2 support detected")
endif()

# =============================================================================
# Dependencies
# =============================================================================
find_package(Threads REQUIRED)

# Optional: Redis (hiredis)
find_library(HIREDIS_LIB hiredis)
if(HIREDIS_LIB)
    add_compile_definitions(GODBRAIN_HAS_REDIS)
    message(STATUS "Redis support enabled")
endif()

# Optional: Python bindings (pybind11)
find_package(pybind11 CONFIG)
if(pybind11_FOUND)
    message(STATUS "Python bindings will be built")
endif()

# =============================================================================
# Core Library
# =============================================================================
add_library(godbrain_core STATIC
    src/core/memory_pool.cpp
    src/core/lock_free_queue.cpp
    src/core/ring_buffer.cpp
    src/core/timestamp.cpp
    
    src/market/orderbook.cpp
    src/market/tick_processor.cpp
    src/market/market_data.cpp
    
    src/trading/order.cpp
    src/trading/position.cpp
    src/trading/execution_engine.cpp
    src/trading/risk_manager.cpp
    
    src/network/websocket_client.cpp
    src/network/tcp_client.cpp
    
    src/simd/orderbook_simd.cpp
    src/simd/statistics_simd.cpp
)

target_include_directories(godbrain_core 
    PUBLIC 
        ${CMAKE_CURRENT_SOURCE_DIR}/include
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/src
)

target_link_libraries(godbrain_core 
    PUBLIC 
        Threads::Threads
)

if(HIREDIS_LIB)
    target_link_libraries(godbrain_core PUBLIC ${HIREDIS_LIB})
endif()

# =============================================================================
# Shared Library (for Python bindings)
# =============================================================================
add_library(godbrain_shared SHARED
    src/bindings/c_api.cpp
)
target_link_libraries(godbrain_shared PRIVATE godbrain_core)
set_target_properties(godbrain_shared PROPERTIES OUTPUT_NAME "godbrain")

# =============================================================================
# Python Bindings
# =============================================================================
if(pybind11_FOUND)
    pybind11_add_module(pygodbrain src/bindings/python_bindings.cpp)
    target_link_libraries(pygodbrain PRIVATE godbrain_core)
endif()

# =============================================================================
# Main Executable
# =============================================================================
add_executable(godbrain_engine src/main.cpp)
target_link_libraries(godbrain_engine PRIVATE godbrain_core)

# =============================================================================
# Benchmarks
# =============================================================================
add_executable(godbrain_bench 
    benchmarks/main.cpp
    benchmarks/orderbook_bench.cpp
    benchmarks/queue_bench.cpp
)
target_link_libraries(godbrain_bench PRIVATE godbrain_core)

# =============================================================================
# Tests
# =============================================================================
enable_testing()
add_executable(godbrain_tests
    tests/test_main.cpp
    tests/test_lock_free_queue.cpp
    tests/test_orderbook.cpp
    tests/test_risk_manager.cpp
)
target_link_libraries(godbrain_tests PRIVATE godbrain_core)
add_test(NAME godbrain_tests COMMAND godbrain_tests)

# =============================================================================
# Installation
# =============================================================================
install(TARGETS godbrain_core godbrain_shared godbrain_engine
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
    RUNTIME DESTINATION bin
)

install(DIRECTORY include/ DESTINATION include)

# =============================================================================
# Summary
# =============================================================================
message(STATUS "")
message(STATUS "=== GODBRAIN C++ Core Engine ===")
message(STATUS "Build Type: ${CMAKE_BUILD_TYPE}")
message(STATUS "C++ Standard: ${CMAKE_CXX_STANDARD}")
message(STATUS "Compiler: ${CMAKE_CXX_COMPILER_ID} ${CMAKE_CXX_COMPILER_VERSION}")
message(STATUS "AVX2: ${COMPILER_SUPPORTS_AVX2}")
message(STATUS "AVX-512: ${COMPILER_SUPPORTS_AVX512}")
message(STATUS "Redis: ${HIREDIS_LIB}")
message(STATUS "Python: ${pybind11_FOUND}")
message(STATUS "")
