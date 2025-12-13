import math
from typing import Dict, Literal

class DynamicSlippageModel:
    """
    GODBRAIN V3 EXECUTION MODULE
    Estimates execution cost based on Orderbook Depth & Volatility.
    """
    def estimate_slippage(
        self,
        symbol: str,
        side: str,
        notional_usd: float,
        orderbook: Dict,
        atr_percent: float = 1.0,
        hour_utc: int = 12
    ):
        """
        Returns estimated slippage percentage (e.g. 0.001 for 0.1%).
        """
        if not orderbook or 'bids' not in orderbook or 'asks' not in orderbook:
            return 0.001 # Default fallback

        # 1. Spread Cost
        best_bid = orderbook['bids'][0][0]
        best_ask = orderbook['asks'][0][0]
        mid_price = (best_bid + best_ask) / 2
        spread_pct = (best_ask - best_bid) / mid_price
        
        # 2. Market Impact (Walking the book)
        remaining_usd = notional_usd
        book_side = orderbook['asks'] if side == 'buy' else orderbook['bids']
        weighted_sum = 0.0
        total_qty = 0.0
        
        for price, amount in book_side:
            level_usd = price * amount
            take_usd = min(remaining_usd, level_usd)
            take_qty = take_usd / price
            
            weighted_sum += take_qty * price
            total_qty += take_qty
            remaining_usd -= take_usd
            
            if remaining_usd <= 0:
                break
        
        if total_qty == 0: return 0.01
        
        avg_fill_price = weighted_sum / total_qty
        
        if side == 'buy':
            impact = (avg_fill_price - best_ask) / best_ask
        else:
            impact = (best_bid - avg_fill_price) / best_bid
            
        # 3. Volatility & Time Penalty
        vol_penalty = 1.0 + (atr_percent / 10.0)
        
        total_slippage = (spread_pct / 2) + impact
        return total_slippage * vol_penalty
