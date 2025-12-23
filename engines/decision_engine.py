# engines/decision_engine.py
# -*- coding: utf-8 -*-

"""
GODBRAIN v5 – DecisionEngine (FAZ 1)
Bu sınıf, agg.py içindeki per-coin karar mantığını kapsüllemek için tasarlanmıştır.
Amaç: davranışı değiştirmeden, karar verme sürecini modüler hale getirmek.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class DecisionEngineConfig:
    # Gerekirse buraya risk / sizing parametreleri eklenebilir.
    min_trade_usd: float = 5.0
    max_equity_fraction: float = 1.0  # trade başına max %100 equity cap
    base_equity_fraction: float = 1.0  # per-coin equity'nin %100'ü baz alınacak


class DecisionEngine:
    """
    DecisionEngine, tek bir sembol için:
      - ultimate_brain'den sinyal alır
      - signal filter uygular
      - pulse + cheat + DNA + VOLTRAN ile final trade boyutunu hesaplar
      - agg.py'ye log string'leri ve APEX'e gidecek payload'ı döner

    NOT:
      - Dosya yazma, APEX'e sinyal gönderme gibi side-effect'ler agg.py'de kalır.
      - Burada sadece hesaplama ve formatlama yapılır.
    """

    def __init__(
        self,
        ultimate_brain: Any,
        blackjack_multiplier_fn: Any,
        pulse_consumer: Optional[Any] = None,
        cheat_enabled: bool = False,
        cheat_fn: Optional[Any] = None,
        config: Optional[DecisionEngineConfig] = None,
    ) -> None:
        self.ultimate_brain = ultimate_brain
        self.blackjack_multiplier_fn = blackjack_multiplier_fn
        self.pulse_consumer = pulse_consumer
        self.cheat_enabled = cheat_enabled
        self.cheat_fn = cheat_fn
        self.config = config or DecisionEngineConfig()

    async def run_symbol_cycle(
        self,
        symbol: str,
        equity_usd: float,
        per_coin_equity: float,
        ohlcv,
        voltran_factor: float,
        voltran_score: float,
        signal_filter: Any,
    ) -> Optional[Dict[str, Any]]:
        """
        Tek bir sembol için tam karar döngüsünü çalıştırır.

        Dönüş:
          - None           -> HOLD (hiçbir şey yapma)
          - {"type": "execute", ...}
          - {"type": "blocked", ...}
        """
        # 1) Ultimate brain'den sinyal al
        decision = await self.ultimate_brain.get_signal(symbol, per_coin_equity, ohlcv)

        # 2) Raw action map
        raw_action = "HOLD"
        if decision.action in ["BUY", "STRONG_BUY"]:
            raw_action = "BUY"
        elif decision.action in ["SELL", "STRONG_SELL"]:
            raw_action = "SELL"

        # HOLD ise filter ve diğer hesaplamalara girmeye gerek yok
        if raw_action == "HOLD":
            return None

        # 3) Signal filter uygula
        filtered = signal_filter.filter(raw_action, decision.conviction)

        ts = datetime.now().strftime("%H:%M:%S")
        coin_short = symbol.split("/")[0]

        # 4) Eğer bloklandıysa, sadece blocked log'u döndür
        if not filtered.should_execute:
            blocked_msg = (
                f"[{ts}] {coin_short} 🛡️ BLOCKED: {raw_action} -> {filtered.filter_reason}"
            )
            return {
                "type": "blocked",
                "symbol": symbol,
                "raw_action": raw_action,
                "blocked_msg": blocked_msg,
            }

        # 5) Pulse + Cheat + DNA + VOLTRAN ile boyut hesapla
        # Pulse (GODLANG) -> flow_multiplier, quantum_boost_active
        flow_mult = 1.0
        quantum_active = False
        if self.pulse_consumer is not None:
            try:
                pulse = self.pulse_consumer.get_latest_pulse() or {}
                flow_mult = float(pulse.get("flow_multiplier", 1.0))
                quantum_active = bool(pulse.get("quantum_boost_active", False))
            except Exception:
                # Pulse arızalansa bile sistemi durdurma
                flow_mult = 1.0
                quantum_active = False

        # CHEAT override (varsa)
        if self.cheat_enabled and self.cheat_fn is not None:
            try:
                cheat_action, cheat_boost, cheat_mult = self.cheat_fn(symbol)
            except Exception:
                cheat_action, cheat_boost, cheat_mult = (None, 0, 1.0)
        else:
            cheat_action, cheat_boost, cheat_mult = (None, 0, 1.0)

        if cheat_action and cheat_action == raw_action:
            flow_mult *= cheat_mult
            cheat_log = (
                f"  🎮 CHEAT BOOST: {cheat_action} +{cheat_boost:.0%} conf, {cheat_mult:.1f}x size"
            )
        else:
            cheat_log = None

        # Quantum score & DNA multiplier
        quantum_resonance_score = max(
            0.0, min(100.0, float(decision.conviction) * 100.0)
        )
        dna_mult = float(self.blackjack_multiplier_fn(quantum_resonance_score))

        total_mult = dna_mult * float(voltran_factor)

        # Sizing
        base_size_usd = per_coin_equity * self.config.base_equity_fraction * flow_mult
        size_usd = max(self.config.min_trade_usd, base_size_usd * total_mult)
        size_usd = min(size_usd, equity_usd * self.config.max_equity_fraction)

        # Status line (önceki ile birebir aynı format)
        status_line = (
            f"[{ts}] {coin_short} | Eq:${per_coin_equity:.0f} | "
            f"{decision.regime} | {raw_action} "
            f"(Conv:{decision.conviction:.2f}, QScore:{quantum_resonance_score:.1f}, "
            f"DNAx:{dna_mult:.2f}, VOL:{voltran_factor:.2f})"
        )

        # EXECUTE log (önceki ile birebir aynı format)
        quantum_flag = " 🔮" if quantum_active else ""
        voltran_flag = " 🦅🐺🦁" if voltran_factor > 1.0 else ""

        log_msg = (
            f"  >>> EXECUTE: {raw_action} {symbol} | ${size_usd:.0f} | "
            f"Regime:{decision.regime} | Flow:{flow_mult:.2f}x | "
            f"QScore:{quantum_resonance_score:.1f} | DNAx:{dna_mult:.2f} | "
            f"VOL:{voltran_factor:.2f}{quantum_flag}{voltran_flag}"
        )

        extras = {
            "conviction": float(decision.conviction),
            "quantum_score": quantum_resonance_score,
            "dna_mult": dna_mult,
            "voltran_factor": float(voltran_factor),
            "voltran_score": float(voltran_score),
            "flow_mult": float(flow_mult),
            "quantum_active": bool(quantum_active),
        }

        result: Dict[str, Any] = {
            "type": "execute",
            "symbol": symbol,
            "raw_action": raw_action,
            "size_usd": float(size_usd),
            "regime": decision.regime,
            "extras": extras,
            "status_line": status_line,
            "log_msg": log_msg,
        }
        if cheat_log:
            result["cheat_log"] = cheat_log

        return result
