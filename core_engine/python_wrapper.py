"""
GODBRAIN C++ Engine Python Wrapper
Provides Python access to the high-performance C++ core.
"""

import os
import ctypes
from pathlib import Path
from typing import Optional, Tuple, List
import numpy as np

# Find the shared library
SCRIPT_DIR = Path(__file__).parent
LIB_PATHS = [
    SCRIPT_DIR / "build" / "libgodbrain.so",
    SCRIPT_DIR / "build" / "libgodbrain.dylib",
    SCRIPT_DIR / "build" / "Release" / "godbrain.dll",
    SCRIPT_DIR / "build" / "Debug" / "godbrain.dll",
]

_lib = None

def _load_library():
    """Load the C++ shared library."""
    global _lib
    if _lib is not None:
        return _lib
    
    for path in LIB_PATHS:
        if path.exists():
            try:
                _lib = ctypes.CDLL(str(path))
                _setup_functions()
                return _lib
            except Exception as e:
                print(f"Failed to load {path}: {e}")
                continue
    
    raise RuntimeError(
        "GODBRAIN C++ library not found. Build with:\n"
        "  cd core_engine && mkdir build && cd build\n"
        "  cmake .. -DCMAKE_BUILD_TYPE=Release && make"
    )

def _setup_functions():
    """Setup C function signatures."""
    # Initialization
    _lib.godbrain_init.restype = ctypes.c_int
    _lib.godbrain_shutdown.restype = None
    _lib.godbrain_version.restype = ctypes.c_char_p
    
    # Orderbook
    _lib.godbrain_update_orderbook.argtypes = [
        ctypes.c_char_p,
        ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_double), ctypes.c_int,
        ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_double), ctypes.c_int,
    ]
    _lib.godbrain_get_mid_price.argtypes = [ctypes.c_char_p]
    _lib.godbrain_get_mid_price.restype = ctypes.c_double
    _lib.godbrain_get_spread.argtypes = [ctypes.c_char_p]
    _lib.godbrain_get_spread.restype = ctypes.c_double
    _lib.godbrain_get_imbalance.argtypes = [ctypes.c_char_p, ctypes.c_int]
    _lib.godbrain_get_imbalance.restype = ctypes.c_double
    
    # Trading
    _lib.godbrain_submit_order.argtypes = [
        ctypes.c_char_p, ctypes.c_int, ctypes.c_int, 
        ctypes.c_double, ctypes.c_double
    ]
    _lib.godbrain_submit_order.restype = ctypes.c_uint64
    _lib.godbrain_cancel_order.argtypes = [ctypes.c_uint64]
    _lib.godbrain_cancel_order.restype = ctypes.c_int
    _lib.godbrain_close_position.argtypes = [ctypes.c_char_p]
    _lib.godbrain_close_position.restype = ctypes.c_int
    
    # Position
    _lib.godbrain_get_position.argtypes = [
        ctypes.c_char_p,
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_double),
    ]
    _lib.godbrain_get_position.restype = ctypes.c_int
    _lib.godbrain_get_equity.restype = ctypes.c_double
    _lib.godbrain_set_equity.argtypes = [ctypes.c_double]
    
    # SIMD
    _lib.godbrain_simd_mean.argtypes = [ctypes.POINTER(ctypes.c_double), ctypes.c_int]
    _lib.godbrain_simd_mean.restype = ctypes.c_double
    _lib.godbrain_simd_stddev.argtypes = [ctypes.POINTER(ctypes.c_double), ctypes.c_int]
    _lib.godbrain_simd_stddev.restype = ctypes.c_double
    _lib.godbrain_simd_sharpe.argtypes = [ctypes.POINTER(ctypes.c_double), ctypes.c_int, ctypes.c_double]
    _lib.godbrain_simd_sharpe.restype = ctypes.c_double
    _lib.godbrain_simd_max_drawdown.argtypes = [ctypes.POINTER(ctypes.c_double), ctypes.c_int]
    _lib.godbrain_simd_max_drawdown.restype = ctypes.c_double


class GodbrainEngine:
    """
    Python wrapper for GODBRAIN C++ Engine.
    
    Usage:
        engine = GodbrainEngine()
        engine.update_orderbook("DOGE/USDT", bids, asks)
        order_id = engine.submit_order("DOGE/USDT", "BUY", "MARKET", 1000)
    """
    
    BUY = 0
    SELL = 1
    MARKET = 0
    LIMIT = 1
    
    def __init__(self):
        self._lib = _load_library()
        result = self._lib.godbrain_init()
        if result != 0:
            raise RuntimeError("Failed to initialize GODBRAIN engine")
    
    def __del__(self):
        if hasattr(self, '_lib') and self._lib:
            self._lib.godbrain_shutdown()
    
    @property
    def version(self) -> str:
        return self._lib.godbrain_version().decode('utf-8')
    
    @property
    def equity(self) -> float:
        return self._lib.godbrain_get_equity()
    
    @equity.setter
    def equity(self, value: float):
        self._lib.godbrain_set_equity(value)
    
    def update_orderbook(
        self, 
        symbol: str,
        bid_prices: List[float],
        bid_sizes: List[float],
        ask_prices: List[float],
        ask_sizes: List[float]
    ):
        """Update orderbook for symbol."""
        symbol_bytes = symbol.encode('utf-8')
        
        bid_p = (ctypes.c_double * len(bid_prices))(*bid_prices)
        bid_s = (ctypes.c_double * len(bid_sizes))(*bid_sizes)
        ask_p = (ctypes.c_double * len(ask_prices))(*ask_prices)
        ask_s = (ctypes.c_double * len(ask_sizes))(*ask_sizes)
        
        self._lib.godbrain_update_orderbook(
            symbol_bytes,
            bid_p, bid_s, len(bid_prices),
            ask_p, ask_s, len(ask_prices)
        )
    
    def get_mid_price(self, symbol: str) -> float:
        """Get mid price for symbol."""
        return self._lib.godbrain_get_mid_price(symbol.encode('utf-8'))
    
    def get_spread(self, symbol: str) -> float:
        """Get spread percentage for symbol."""
        return self._lib.godbrain_get_spread(symbol.encode('utf-8'))
    
    def get_imbalance(self, symbol: str, levels: int = 5) -> float:
        """Get order imbalance (-1 to +1)."""
        return self._lib.godbrain_get_imbalance(symbol.encode('utf-8'), levels)
    
    def submit_order(
        self,
        symbol: str,
        side: str,  # "BUY" or "SELL"
        order_type: str,  # "MARKET" or "LIMIT"
        quantity: float,
        price: float = 0.0
    ) -> int:
        """Submit order. Returns order ID or 0 if rejected."""
        side_int = self.BUY if side.upper() == "BUY" else self.SELL
        type_int = self.MARKET if order_type.upper() == "MARKET" else self.LIMIT
        
        return self._lib.godbrain_submit_order(
            symbol.encode('utf-8'),
            side_int, type_int,
            quantity, price
        )
    
    def cancel_order(self, order_id: int) -> bool:
        """Cancel order by ID."""
        return self._lib.godbrain_cancel_order(order_id) == 1
    
    def close_position(self, symbol: str) -> bool:
        """Close position for symbol."""
        return self._lib.godbrain_close_position(symbol.encode('utf-8')) == 1
    
    def get_position(self, symbol: str) -> Optional[Tuple[float, float, float]]:
        """Get position (quantity, entry_price, pnl) or None."""
        qty = ctypes.c_double()
        price = ctypes.c_double()
        pnl = ctypes.c_double()
        
        result = self._lib.godbrain_get_position(
            symbol.encode('utf-8'),
            ctypes.byref(qty),
            ctypes.byref(price),
            ctypes.byref(pnl)
        )
        
        if result == 0:
            return None
        
        return (qty.value, price.value, pnl.value)


class SIMDStats:
    """SIMD-optimized statistics using C++ engine."""
    
    def __init__(self):
        self._lib = _load_library()
    
    def _to_c_array(self, data: np.ndarray):
        if not isinstance(data, np.ndarray):
            data = np.array(data, dtype=np.float64)
        if data.dtype != np.float64:
            data = data.astype(np.float64)
        return data.ctypes.data_as(ctypes.POINTER(ctypes.c_double)), len(data)
    
    def mean(self, data: np.ndarray) -> float:
        """Calculate mean using SIMD."""
        ptr, n = self._to_c_array(data)
        return self._lib.godbrain_simd_mean(ptr, n)
    
    def stddev(self, data: np.ndarray) -> float:
        """Calculate standard deviation using SIMD."""
        ptr, n = self._to_c_array(data)
        return self._lib.godbrain_simd_stddev(ptr, n)
    
    def sharpe_ratio(self, returns: np.ndarray, risk_free: float = 0.0) -> float:
        """Calculate Sharpe ratio using SIMD."""
        ptr, n = self._to_c_array(returns)
        return self._lib.godbrain_simd_sharpe(ptr, n, risk_free)
    
    def max_drawdown(self, equity: np.ndarray) -> float:
        """Calculate max drawdown using SIMD."""
        ptr, n = self._to_c_array(equity)
        return self._lib.godbrain_simd_max_drawdown(ptr, n)


# Convenience functions
def create_engine() -> GodbrainEngine:
    """Create a new GODBRAIN engine instance."""
    return GodbrainEngine()

def create_simd_stats() -> SIMDStats:
    """Create SIMD statistics calculator."""
    return SIMDStats()


if __name__ == "__main__":
    print("GODBRAIN Python Wrapper Test")
    print("=" * 60)
    
    try:
        engine = GodbrainEngine()
        print(f"Version: {engine.version}")
        print(f"Equity: ${engine.equity:,.2f}")
        
        # Test orderbook
        engine.update_orderbook(
            "DOGE/USDT",
            bid_prices=[0.3199, 0.3198, 0.3197],
            bid_sizes=[10000, 20000, 30000],
            ask_prices=[0.3201, 0.3202, 0.3203],
            ask_sizes=[8000, 15000, 22000]
        )
        
        print(f"Mid price: {engine.get_mid_price('DOGE/USDT'):.6f}")
        print(f"Spread: {engine.get_spread('DOGE/USDT'):.4f}%")
        print(f"Imbalance: {engine.get_imbalance('DOGE/USDT'):.4f}")
        
        # Test order
        order_id = engine.submit_order("DOGE/USDT", "BUY", "MARKET", 5000)
        print(f"Order ID: {order_id}")
        
        pos = engine.get_position("DOGE/USDT")
        if pos:
            print(f"Position: qty={pos[0]:.2f}, entry={pos[1]:.6f}, pnl={pos[2]:.2f}")
        
        # Test SIMD
        stats = SIMDStats()
        data = np.random.randn(10000)
        print(f"\nSIMD Mean: {stats.mean(data):.6f}")
        print(f"SIMD Stddev: {stats.stddev(data):.6f}")
        
    except RuntimeError as e:
        print(f"Library not built: {e}")
