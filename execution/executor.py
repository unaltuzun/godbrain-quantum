# -*- coding: utf-8 -*-
"""
GODBRAIN EXECUTION ENGINE
Handles OKX order placement, contract sizing, and leverage management.
"""

import math
import time
from typing import Dict, Any, Optional
from config_center import config

class GodbrainExecutor:
    """Handles execution logic for OKX."""
    
    def __init__(self, okx_client):
        self.okx = okx_client
        self.last_set_leverage = {}

    def map_symbol(self, raw_symbol: str) -> str:
        """'DOGE/USDT:USDT' -> 'DOGE-USDT-SWAP'"""
        if not raw_symbol: return ""
        base = raw_symbol.split(":")[0]
        return base.replace("/", "-") + "-SWAP"

    async def get_amount_from_usd(self, symbol: str, action: str, size_usd: float) -> float:
        """Calculates OKX contract amount from USD size."""
        try:
            market = self.okx.market(symbol)
            price = self.okx.fetch_ticker(symbol)["last"]
            contract_size = float(market.get("contractSize", 1.0))
            
            # Amount in contracts
            amount_contracts = size_usd / (price * contract_size)
            
            # Round down to nearest integer contract
            amount = math.floor(amount_contracts)
            
            if amount < 1:
                print(f"[EXEC] ⚠️ Amount {amount} too small for {symbol} (${size_usd:.2f})")
                return 0.0
                
            return float(amount)
        except Exception as e:
            print(f"[EXEC] ❌ Amount calc error for {symbol}: {e}")
            return 0.0

    async def execute_trade(self, symbol: str, action: str, size_usd: float) -> Optional[Dict]:
        """
        Executes a trade on OKX with 10x leverage and aggressive scaling.
        Fail-safe: returns None on any error to prevent partial/incorrect fills.
        """
        if not self.okx:
            print("[EXEC] ❌ No OKX client provided.")
            return None
            
        if not config.APEX_LIVE:
            print(f"[SIM] Would {action} {symbol} (Size: ${size_usd:.2f})")
            return {"status": "simulated"}

        market_symbol = self.map_symbol(symbol)
        
        try:
            # 1) Setup Leverage (10x)
            if market_symbol not in self.last_set_leverage:
                try:
                    self.okx.set_leverage(10, market_symbol)
                    self.last_set_leverage[market_symbol] = time.time()
                    print(f"[EXEC] ⚡ 10x leverage locked for {market_symbol}")
                except Exception as le:
                    print(f"[EXEC] ⚠️ Leverage set failed (might be already set): {le}")

            # 2) Refresh Available Margin for 'YA HERRO YA MERRO' scaling
            try:
                balance = self.okx.fetch_balance()
                # For cross-margin swap, use 'total' or check 'info' for actual available
                current_free = float(balance["free"].get("USDT", 0))
                
                # Fallback: If free is 0, use 40% of TOTAL equity (conservative for cross-margin)
                if current_free < 1:
                    current_total = float(balance["total"].get("USDT", 0))
                    # Use 40% of total - cross-margin reserves the rest
                    current_free = current_total * 0.40 if current_total > 5 else 0
                    if current_free > 0:
                        print(f"[EXEC] 🔓 UNLOCKED: Using 40% of total equity: ${current_free:.2f}")
                        
            except Exception as be:
                print(f"[EXEC] ⚠️ Balance refresh failed: {be}")
                return None

            # 3) YA HERRO YA MERRO: Scale to full available margin with 10x
            all_in_size_usd = current_free * 10  # 10x leverage, no extra reduction
            
            if all_in_size_usd < 2:
                # Still show if skipping
                if current_free < 0.5:
                    print(f"[EXEC] ❌ Skip: Margin too low (${current_free:.2f})")
                return None

            # 4) Calculate contracts
            amount = await self.get_amount_from_usd(symbol, action, all_in_size_usd)
            
            if amount <= 0:
                return None

            # 5) Place Order
            side = action.lower() # 'buy' or 'sell'
            print(f"[EXEC] 🚀 EXECUTE {action} {market_symbol} | Amount: {amount} contracts (~${all_in_size_usd:.0f})")
            
            order = self.okx.create_market_order(market_symbol, side, amount)
            print(f"[EXEC] ✅ Order Placed: {order.get('id', 'N/A')}")
            return order

        except Exception as e:
            print(f"[EXEC] ❌ CRITICAL EXCEPTION during {action} {symbol}: {e}")
            return None
