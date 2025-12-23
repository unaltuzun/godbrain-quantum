#!/usr/bin/env python3
"""
GODBRAIN DNA ENGINE v2 + DNA ACADEMY
------------------------------------

Deterministic evolution + position sizing + ranking layer for genomes.

This module is self-contained:
- DNAStrategyParams: core genome parameters
- MarketEnv / AssetContext: environment abstraction
- DNAEvolutionEngine: evolves DNA based on equity change + macro state
- PositionSizer: multi-layer risk & sizing engine
- JSON helpers: parse Genome history & System dump snapshots
- DNAAcademy: rank genomes (CADET → MASTER → DOCTOR)
- run_dna_cycle_from_snapshots: end-to-end lab helper
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple, List


# ===========================
#  CORE DATA MODELS
# ===========================


@dataclass
class DNAStrategyParams:
    """
    Core strategy DNA.

    All values are expressed in human-friendly units:
    - stop_loss_pct: negative percentage (e.g. -0.57 => -0.57%)
    - take_profit_pct: positive percentage (e.g. 23.1 => +23.1%)
    - rsi_buy_level: 0–100
    - rsi_sell_level: 0–100
    - position_size_factor: 0–1, relative to max_risk_per_trade_pct
    """
    stop_loss_pct: float
    take_profit_pct: float
    rsi_buy_level: float
    rsi_sell_level: float
    position_size_factor: float

    def clone(self) -> "DNAStrategyParams":
        return DNAStrategyParams(
            stop_loss_pct=self.stop_loss_pct,
            take_profit_pct=self.take_profit_pct,
            rsi_buy_level=self.rsi_buy_level,
            rsi_sell_level=self.rsi_sell_level,
            position_size_factor=self.position_size_factor,
        )


@dataclass
class MarketEnv:
    """
    Encapsulates macro / Prometheus state into a single vector.
    """
    risk_score: float               # e.g. -100 (max fear) … +100 (max greed)
    market_pressure: float          # 0–1, how "compressed / directional" the tape is
    prometheus_direction: str       # e.g. "WHALE_BUY", "WHALE_SELL", "NEUTRAL", "QUANTUM_RESONANCE"
    flow_multiplier: float          # 0.5–2.0, aggregate flow magnitude
    quantum_resonance_active: bool = False


@dataclass
class AssetContext:
    symbol: str
    price: float
    volatility_score: float  # e.g. ATR% or normalized vol 0–1


@dataclass
class PositionSizingConfig:
    """
    Global risk guardrails for the sizing engine.
    """
    max_risk_per_trade_pct: float = 1.0    # max % of equity to risk per trade
    hard_cap_position_pct: float = 50.0    # max % of equity in a single position
    freeze_during_extreme_risk: bool = True
    freeze_during_qr: bool = False
    quantum_resonance_boost: float = 1.5   # QR aktifken risk çarpanı (opsiyonel boost)


@dataclass
class PositionSizingResult:
    symbol: str
    side: str
    quantity: float
    notional: float
    risk_pct: float
    effective_multiplier: float
    reason: str

    def as_order_payload(self) -> Dict[str, Any]:
        """
        Executor'a gönderilebilecek minimal emir payload'u.
        """
        return {
            "symbol": self.symbol,
            "side": self.side,
            "qty": self.quantity,
            "notional": self.notional,
            "meta": {
                "risk_pct": self.risk_pct,
                "multiplier": self.effective_multiplier,
                "reason": self.reason,
            },
        }


# ===========================
#  DNA EVOLUTION ENGINE
# ===========================


@dataclass
class DNAEvolutionConfig:
    improve_threshold_pct: float = 0.5     # > +0.5% equity değişimi "iyi"
    degrade_threshold_pct: float = -0.5    # < -0.5% equity değişimi "kötü"
    max_sl_step_pct: float = 0.25         # SL için max relatif adım (|Δ| <= 25%)
    max_tp_step_pct: float = 0.25         # TP için max relatif adım
    max_rsi_step: float = 3.0             # RSI seviye adımı
    max_size_step_pct: float = 0.25       # position_size_factor relatif adım
    # Güvenlik limitleri
    min_stop_loss_pct: float = -5.0
    max_stop_loss_pct: float = -0.1
    min_take_profit_pct: float = 3.0
    max_take_profit_pct: float = 40.0
    min_rsi_buy: float = 2.0
    max_rsi_buy: float = 35.0
    min_rsi_sell: float = 60.0
    max_rsi_sell: float = 95.0
    min_size_factor: float = 0.05
    max_size_factor: float = 1.0


class DNAEvolutionEngine:
    """
    Deterministic DNA evolution based on last equity change and environment.
    """

    def __init__(self, cfg: Optional[DNAEvolutionConfig] = None) -> None:
        self.cfg = cfg or DNAEvolutionConfig()

    def evolve(self, current: DNAStrategyParams, equity_change_pct: float, env: MarketEnv) -> Tuple[DNAStrategyParams, str]:
        """
        Returns a new DNA instance and a short reason string.
        """
        cfg = self.cfg
        dna = current.clone()

        # Normalize signals
        perf = equity_change_pct
        risk_norm = max(-100.0, min(100.0, env.risk_score)) / 100.0  # -1 … +1
        pressure = max(0.0, min(1.0, env.market_pressure))
        is_whale_buy = env.prometheus_direction.upper() == "WHALE_BUY"
        is_whale_sell = env.prometheus_direction.upper() == "WHALE_SELL"

        reason_parts: List[str] = []

        # 1) Performance-based adaptation
        if perf >= cfg.improve_threshold_pct:
            # System performed well → we can be slightly more aggressive
            k = min(abs(perf) / 10.0, 1.0)  # 0 … 1
            # TP'yi hafif aç, SL'i biraz sıkılaştır, boyutu artır
            tp_step = dna.take_profit_pct * cfg.max_tp_step_pct * k * (0.5 + pressure)
            sl_step = abs(dna.stop_loss_pct) * cfg.max_sl_step_pct * k * (0.5 + pressure)
            size_step = dna.position_size_factor * cfg.max_size_step_pct * k * (0.5 + max(0.0, risk_norm))

            dna.take_profit_pct = self._clamp(
                dna.take_profit_pct + tp_step,
                cfg.min_take_profit_pct,
                cfg.max_take_profit_pct,
            )
            # stop_loss_pct negatif, sıfıra doğru sıkılaştır
            new_sl_abs = max(0.01, abs(dna.stop_loss_pct) - sl_step)
            dna.stop_loss_pct = -self._clamp(new_sl_abs, abs(cfg.max_stop_loss_pct), abs(cfg.min_stop_loss_pct))
            dna.position_size_factor = self._clamp(
                dna.position_size_factor + size_step,
                cfg.min_size_factor,
                cfg.max_size_factor,
            )
            reason_parts.append(f"POSITIVE_EVOLUTION({perf:.2f}%)")

        elif perf <= cfg.degrade_threshold_pct:
            # Kötü performans → defansifleş
            k = min(abs(perf) / 10.0, 1.0)
            tp_step = dna.take_profit_pct * cfg.max_tp_step_pct * k
            sl_step = abs(dna.stop_loss_pct) * cfg.max_sl_step_pct * k
            size_step = dna.position_size_factor * cfg.max_size_step_pct * k

            dna.take_profit_pct = self._clamp(
                dna.take_profit_pct - tp_step,
                cfg.min_take_profit_pct,
                cfg.max_take_profit_pct,
            )
            # SL'i daha sıkı yap (kayıp limitini küçült)
            new_sl_abs = max(0.01, abs(dna.stop_loss_pct) - sl_step)
            dna.stop_loss_pct = -self._clamp(new_sl_abs, abs(cfg.max_stop_loss_pct), abs(cfg.min_stop_loss_pct))
            dna.position_size_factor = self._clamp(
                dna.position_size_factor - size_step,
                cfg.min_size_factor,
                cfg.max_size_factor,
            )
            reason_parts.append(f"NEGATIVE_EVOLUTION({perf:.2f}%)")

        else:
            reason_parts.append(f"STABLE({perf:.2f}%)")

        # 2) Flow / direction fine-tuning (RSI levels)
        if is_whale_buy:
            # Daha agresif alım: RSI buy düşebilir, sell biraz yukarı
            dna.rsi_buy_level = self._clamp(
                dna.rsi_buy_level - cfg.max_rsi_step * pressure,
                cfg.min_rsi_buy,
                cfg.max_rsi_buy,
            )
            dna.rsi_sell_level = self._clamp(
                dna.rsi_sell_level + cfg.max_rsi_step * pressure,
                cfg.min_rsi_sell,
                cfg.max_rsi_sell,
            )
            reason_parts.append("FLOW:WHALE_BUY")

        elif is_whale_sell:
            # Satıcı baskısı: alım eşiği yukarı, satış eşiği aşağı
            dna.rsi_buy_level = self._clamp(
                dna.rsi_buy_level + cfg.max_rsi_step * pressure,
                cfg.min_rsi_buy,
                cfg.max_rsi_buy,
            )
            dna.rsi_sell_level = self._clamp(
                dna.rsi_sell_level - cfg.max_rsi_step * pressure,
                cfg.min_rsi_sell,
                cfg.max_rsi_sell,
            )
            reason_parts.append("FLOW:WHALE_SELL")

        # 3) Quantum resonance hint (şimdilik sadece reason'a işliyoruz)
        if env.quantum_resonance_active:
            reason_parts.append("QR_ACTIVE")

        reason = "|".join(reason_parts)
        return dna, reason

    @staticmethod
    def _clamp(x: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, x))


# ===========================
#  POSITION SIZING ENGINE
# ===========================


class PositionSizer:
    """
    Multi-layer risk-based position sizing.

    Layers:
      1) Base risk from DNA.position_size_factor
      2) Macro multiplier (risk_score)
      3) Volatility multiplier (ATR% or custom vol score)
      4) Prometheus flow multiplier (direction + strength)
      5) Caps: max_risk_per_trade_pct, hard_cap_position_pct, open_risk
    """

    def __init__(self, cfg: Optional[PositionSizingConfig] = None) -> None:
        self.cfg = cfg or PositionSizingConfig()

    def size_position(
        self,
        dna: DNAStrategyParams,
        env: MarketEnv,
        equity: float,
        asset: AssetContext,
        open_risk_pct: float,
        is_long: bool,
        vix: Optional[float] = None,
    ) -> PositionSizingResult:
        cfg = self.cfg

        if equity <= 0 or asset.price <= 0:
            return PositionSizingResult(
                symbol=asset.symbol,
                side="NONE",
                quantity=0.0,
                notional=0.0,
                risk_pct=0.0,
                effective_multiplier=0.0,
                reason="INVALID_EQUITY_OR_PRICE",
            )

        # Hard freeze on extreme environment
        if cfg.freeze_during_extreme_risk and env.risk_score <= -80:
            return PositionSizingResult(
                symbol=asset.symbol,
                side="NONE",
                quantity=0.0,
                notional=0.0,
                risk_pct=0.0,
                effective_multiplier=0.0,
                reason=f"FROZEN_EXTREME_RISK(risk_score={env.risk_score})",
            )

        if cfg.freeze_during_qr and env.quantum_resonance_active:
            return PositionSizingResult(
                symbol=asset.symbol,
                side="NONE",
                quantity=0.0,
                notional=0.0,
                risk_pct=0.0,
                effective_multiplier=0.0,
                reason="FROZEN_QR",
            )

        # 1) Base risk from DNA
        base_risk_pct = max(0.0, min(cfg.max_risk_per_trade_pct, cfg.max_risk_per_trade_pct * dna.position_size_factor))

        # 2) Macro multiplier
        macro_mult = self._macro_multiplier(env.risk_score)

        # 3) Volatility multiplier
        vol_mult = self._vol_multiplier(asset.volatility_score, vix)

        # 4) Prometheus / flow multiplier
        prom_mult = self._prometheus_multiplier(env, is_long)

        # 5) Quantum resonance boost (optional)
        qr_mult = 1.0
        if env.quantum_resonance_active and not cfg.freeze_during_qr:
            qr_mult = cfg.quantum_resonance_boost

        effective_mult = macro_mult * vol_mult * prom_mult * qr_mult

        # Effective risk
        eff_risk_pct = base_risk_pct * effective_mult
        # Eğer risk 0'ın altına düştüyse veya çok küçükse -> trade yok
        if eff_risk_pct <= 0.01:
            return PositionSizingResult(
                symbol=asset.symbol,
                side="NONE",
                quantity=0.0,
                notional=0.0,
                risk_pct=0.0,
                effective_multiplier=effective_mult,
                reason=f"RISK_TOO_SMALL(base={base_risk_pct:.3f},eff={eff_risk_pct:.3f})",
            )

        # Hard cap check
        remaining_risk_cap = max(0.0, cfg.hard_cap_position_pct - open_risk_pct)
        if eff_risk_pct > remaining_risk_cap:
            eff_risk_pct = remaining_risk_cap
            effective_mult = eff_risk_pct / base_risk_pct if base_risk_pct > 0 else 0.0

        if eff_risk_pct <= 0.01:
            return PositionSizingResult(
                symbol=asset.symbol,
                side="NONE",
                quantity=0.0,
                notional=0.0,
                risk_pct=0.0,
                effective_multiplier=effective_mult,
                reason=f"HARD_CAP_REACHED(open={open_risk_pct:.2f}%,cap={cfg.hard_cap_position_pct:.2f}%)",
            )

        notional = equity * (eff_risk_pct / 100.0)
        quantity = notional / asset.price

        side = "LONG" if is_long else "SHORT"
        reason = (
            f"OK|base={base_risk_pct:.3f}%|macro={macro_mult:.2f}|"
            f"vol={vol_mult:.2f}|prom={prom_mult:.2f}|qr={qr_mult:.2f}"
        )

        return PositionSizingResult(
            symbol=asset.symbol,
            side=side,
            quantity=quantity,
            notional=notional,
            risk_pct=eff_risk_pct,
            effective_multiplier=effective_mult,
            reason=reason,
        )

    @staticmethod
    def _macro_multiplier(risk_score: float) -> float:
        """
        Map risk_score (-100..+100) to a sane macro multiplier.
        """
        r = max(-100.0, min(100.0, risk_score))
        if r <= -60:
            return 0.4
        if r <= -30:
            return 0.7
        if r <= 0:
            return 1.0
        if r <= 20:
            return 1.1
        if r <= 40:
            return 1.2
        return 1.25

    @staticmethod
    def _vol_multiplier(vol_score: float, vix: Optional[float]) -> float:
        """
        Combine asset-level vol (0-1 or ATR%) with VIX if available.
        Returns 0.5..1.0 range.
        """
        # Normalize vol_score roughly assuming 0.0–0.1 range common
        vol = max(0.0, min(1.0, vol_score * 10.0))  # 0–1
        # If VIX present, map 10–40 → 0–1
        vix_comp = 0.0
        if vix is not None:
            vix_comp = max(0.0, min(1.0, (vix - 10.0) / 30.0))

        combined = (vol + vix_comp) / 2.0
        # High vol → smaller size
        if combined >= 0.8:
            return 0.5
        if combined >= 0.5:
            return 0.7
        if combined >= 0.3:
            return 0.85
        return 1.0

    @staticmethod
    def _prometheus_multiplier(env: MarketEnv, is_long: bool) -> float:
        """
        Simple directional bias based on Prometheus direction + flow multiplier.
        """
        direction = env.prometheus_direction.upper()
        flow = max(0.1, min(3.0, env.flow_multiplier))

        if direction == "WHALE_BUY":
            return 1.0 + (0.5 * flow if is_long else -0.3 * flow)
        if direction == "WHALE_SELL":
            return 1.0 + (-0.5 * flow if is_long else 0.3 * flow)
        if direction == "NEUTRAL":
            return 1.0
        if direction == "QUANTUM_RESONANCE":
            # QR durumu, ana etkiyi QR multiplier'a bırakıyoruz
            return 1.0
        return 1.0


# ===========================
#  JSON HELPERS
# ===========================


def load_json_file(path: str) -> Dict[str, Any]:
    """
    Simple JSON loader for lab usage.
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def dna_from_genome_history(
    data: Dict[str, Any],
    with_meta: bool = False,
) -> Tuple[DNAStrategyParams, str] | Tuple[DNAStrategyParams, str, str, Optional[str], Optional[str]]:
    """
    Extract DNAStrategyParams and champion id (and optional meta) from genome history snapshot.

    Expected structure:
    {
        "epoch_time": "...",
        "families_detected": [
            {
                "id": "3ce686",
                "family": "THE ABYSS WATCHERS",
                "lore": "...",
                "stats": {
                    "stop_loss_pct": -0.57,
                    "take_profit_pct": 23.1,
                    "rsi_buy_level": 5.9,
                    "rsi_sell_level": 78.8,
                    "position_size_factor": 0.36
                },
                "timestamp": "..."
            },
            ...
        ]
    }
    """
    families = data.get("families_detected") or []
    if not families:
        raise ValueError("dna_from_genome_history: 'families_detected' is empty.")

    champion = families[-1]
    stats = champion.get("stats") or {}

    dna = DNAStrategyParams(
        stop_loss_pct=float(stats.get("stop_loss_pct", -0.5)),
        take_profit_pct=float(stats.get("take_profit_pct", 15.0)),
        rsi_buy_level=float(stats.get("rsi_buy_level", 10.0)),
        rsi_sell_level=float(stats.get("rsi_sell_level", 80.0)),
        position_size_factor=float(stats.get("position_size_factor", 0.25)),
    )

    champion_id = str(champion.get("id", "unknown"))
    family = str(champion.get("family", "UNKNOWN"))
    epoch_time = data.get("epoch_time")
    ts = champion.get("timestamp")

    if with_meta:
        return dna, champion_id, family, epoch_time, ts
    return dna, champion_id


def market_env_from_system_dump(
    data: Dict[str, Any],
    default_risk_score: float = -20.0,
) -> Tuple[MarketEnv, Optional[float]]:
    """
    Build MarketEnv + optional VIX value from system dump snapshot.
    """
    prom = data.get("channel:prom") or {}
    macro = data.get("channel:macro") or {}

    prom_meta = prom.get("meta") or {}
    prom_status = prom.get("status") or {}
    macro_mode = macro.get("system_mode") or {}
    macro_vals = macro.get("macro") or {}

    market_pressure = float(prom_meta.get("market_pressure", 0.0))
    direction = str(prom_status.get("direction", "NEUTRAL"))
    flow_multiplier = float(prom_status.get("flow_multiplier", 1.0))

    try:
        risk_score = float(macro_mode.get("risk_score", default_risk_score))
    except (TypeError, ValueError):
        risk_score = default_risk_score

    vix_raw = macro_vals.get("vix")
    try:
        vix: Optional[float] = float(vix_raw) if vix_raw is not None else None
    except (TypeError, ValueError):
        vix = None

    quantum_resonance_active = direction.upper() == "QUANTUM_RESONANCE"

    env = MarketEnv(
        risk_score=risk_score,
        market_pressure=market_pressure,
        prometheus_direction=direction,
        flow_multiplier=flow_multiplier,
        quantum_resonance_active=quantum_resonance_active,
    )

    return env, vix


# ===========================
#  DNA ACADEMY LAYER
# ===========================


@dataclass
class GenomeRecord:
    """
    Persistent stats for a single genome across time.
    """
    genome_id: str
    family: str
    rank: str = "CADET"
    trades: int = 0
    wins: int = 0
    losses: int = 0
    cumulative_return_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    best_run_pct: float = 0.0
    worst_run_pct: float = 0.0
    equity_index: float = 100.0      # synthetic equity index starting at 100
    peak_equity_index: float = 100.0
    last_score: float = 0.0
    last_update_ts: float = field(default_factory=lambda: time.time())

    @property
    def win_rate(self) -> float:
        if self.trades == 0:
            return 0.0
        return self.wins / self.trades

    def to_dict(self) -> Dict[str, Any]:
        return {
            "genome_id": self.genome_id,
            "family": self.family,
            "rank": self.rank,
            "trades": self.trades,
            "wins": self.wins,
            "losses": self.losses,
            "cumulative_return_pct": self.cumulative_return_pct,
            "max_drawdown_pct": self.max_drawdown_pct,
            "best_run_pct": self.best_run_pct,
            "worst_run_pct": self.worst_run_pct,
            "equity_index": self.equity_index,
            "peak_equity_index": self.peak_equity_index,
            "last_score": self.last_score,
            "last_update_ts": self.last_update_ts,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "GenomeRecord":
        return GenomeRecord(
            genome_id=data["genome_id"],
            family=data.get("family", "UNKNOWN"),
            rank=data.get("rank", "CADET"),
            trades=int(data.get("trades", 0)),
            wins=int(data.get("wins", 0)),
            losses=int(data.get("losses", 0)),
            cumulative_return_pct=float(data.get("cumulative_return_pct", 0.0)),
            max_drawdown_pct=float(data.get("max_drawdown_pct", 0.0)),
            best_run_pct=float(data.get("best_run_pct", 0.0)),
            worst_run_pct=float(data.get("worst_run_pct", 0.0)),
            equity_index=float(data.get("equity_index", 100.0)),
            peak_equity_index=float(data.get("peak_equity_index", 100.0)),
            last_score=float(data.get("last_score", 0.0)),
            last_update_ts=float(data.get("last_update_ts", time.time())),
        )


class DNAAcademy:
    """
    DNA Academy:
      - Tracks genomes across time
      - Computes ranks: CADET → ROOKIE → SPECIALIST → EXPERT → MASTER → DOCTOR
      - Provides leaderboard for best genomes

    Kullanım:
      academy = DNAAcademy()
      rec = academy.record_cycle(genome_id, family, equity_change_pct)
    """

    def __init__(self) -> None:
        self._records: Dict[str, GenomeRecord] = {}

    # --- public API ---

    def get_record(self, genome_id: str) -> Optional[GenomeRecord]:
        return self._records.get(genome_id)

    def register_genome(self, genome_id: str, family: str) -> GenomeRecord:
        rec = self._records.get(genome_id)
        if rec is not None:
            # family değiştiyse bile son family'yi güncelliyoruz
            rec.family = family
            return rec
        rec = GenomeRecord(genome_id=genome_id, family=family)
        self._records[genome_id] = rec
        return rec

    def record_cycle(
        self,
        genome_id: str,
        family: str,
        equity_change_pct: float,
        trades_in_cycle: int = 1,
        winning_trades: Optional[int] = None,
        timestamp: Optional[float] = None,
    ) -> GenomeRecord:
        """
        Update stats for given genome with one lab / live cycle.

        For simplicity, if winning_trades is None:
          - if equity_change_pct > 0 → all trades counted as win
          - if equity_change_pct <= 0 → all as loss
        """
        rec = self.register_genome(genome_id, family)

        if timestamp is None:
            timestamp = time.time()

        trades_in_cycle = max(0, trades_in_cycle)
        if trades_in_cycle == 0:
            # just update equity & rank (e.g. mark-to-market)
            self._update_equity(rec, equity_change_pct)
        else:
            if winning_trades is None:
                wins = trades_in_cycle if equity_change_pct > 0 else 0
            else:
                wins = max(0, min(trades_in_cycle, winning_trades))
            losses = trades_in_cycle - wins

            rec.trades += trades_in_cycle
            rec.wins += wins
            rec.losses += losses

            self._update_equity(rec, equity_change_pct)

        rec.cumulative_return_pct += equity_change_pct
        rec.best_run_pct = max(rec.best_run_pct, equity_change_pct)
        rec.worst_run_pct = min(rec.worst_run_pct, equity_change_pct)
        rec.last_score = self._compute_score(rec)
        rec.rank = self._compute_rank(rec)
        rec.last_update_ts = timestamp

        return rec

    def leaderboard(self, top_n: int = 10) -> List[GenomeRecord]:
        """
        Return top-N genomes by last_score, descending.
        """
        return sorted(self._records.values(), key=lambda r: r.last_score, reverse=True)[:top_n]

    def to_dict(self) -> Dict[str, Any]:
        return {gid: rec.to_dict() for gid, rec in self._records.items()}

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "DNAAcademy":
        acad = DNAAcademy()
        for gid, rec_data in data.items():
            rec = GenomeRecord.from_dict(rec_data)
            acad._records[gid] = rec
        return acad

    # --- internal helpers ---

    @staticmethod
    def _update_equity(rec: GenomeRecord, equity_change_pct: float) -> None:
        """
        Update synthetic equity index and drawdown stats.
        """
        # equity_index *= (1 + change/100)
        rec.equity_index *= (1.0 + equity_change_pct / 100.0)
        rec.peak_equity_index = max(rec.peak_equity_index, rec.equity_index)
        if rec.peak_equity_index > 0:
            dd = (rec.peak_equity_index - rec.equity_index) / rec.peak_equity_index * 100.0
            rec.max_drawdown_pct = max(rec.max_drawdown_pct, dd)

    @staticmethod
    def _compute_score(rec: GenomeRecord) -> float:
        """
        Composite score for ranking genomes.

        Components:
          - cumulative_return_pct (primary)
          - win_rate (secondary)
          - drawdown (penalty)
        """
        win_rate = rec.win_rate
        dd_penalty = rec.max_drawdown_pct

        stability = max(0.0, 50.0 - dd_penalty) / 50.0  # 0..1, reward low drawdown

        score = (
            rec.cumulative_return_pct
            + 20.0 * (win_rate - 0.5)   # ±10 contribution if WR ~ [0,1]
            + 10.0 * stability          # 0..10 bonus
        )
        # Slight trade count bonus
        score += min(10.0, rec.trades * 0.1)

        return score

    @staticmethod
    def _compute_rank(rec: GenomeRecord) -> str:
        """
        Map score + experience to rank string.

        Rough ladder:
          - <10 trades → CADET
          - then score bands → ROOKIE / SPECIALIST / EXPERT / MASTER / DOCTOR
        """
        if rec.trades < 10:
            return "CADET"

        s = rec.last_score

        if s < 0:
            return "CADET"
        if s < 20:
            return "ROOKIE"
        if s < 40:
            return "SPECIALIST"
        if s < 70:
            return "EXPERT"
        if s < 120:
            return "MASTER"
        return "DOCTOR"


# ===========================
#  FULL PIPELINE HELPER
# ===========================


def run_dna_cycle_from_snapshots(
    genome_history: Dict[str, Any],
    system_dump: Dict[str, Any],
    equity: float,
    symbol: str,
    price: float,
    volatility_score: float,
    last_equity_change_pct: float,
    open_risk_pct: float = 0.0,
    cfg: Optional[PositionSizingConfig] = None,
    academy: Optional[DNAAcademy] = None,
    trades_in_cycle: int = 1,
    winning_trades: Optional[int] = None,
) -> Dict[str, Any]:
    """
    GODBRAIN lab helper: single call evolution + sizing (+ optional academy update).

    Inputs:
      - genome_history: Genome history JSON (dict)
      - system_dump: System dump JSON (dict)
      - equity: account equity
      - symbol, price, volatility_score: asset context
      - last_equity_change_pct: last PnL (%)
      - open_risk_pct: already exposed risk (% of equity)
      - cfg: optional PositionSizingConfig
      - academy: optional DNAAcademy instance → will be updated if provided
      - trades_in_cycle / winning_trades: for academy stats

    Returns:
      dict with:
        {
          "champion_id": str,
          "champion_family": str,
          "old_dna": DNAStrategyParams,
          "new_dna": DNAStrategyParams,
          "evolve_reason": str,
          "sizing": PositionSizingResult,
          "env": MarketEnv,
          "vix": float | None,
          "academy_record": GenomeRecord | None,
        }
    """
    # 1) Genome → DNA (+ meta)
    dna, champion_id, champion_family, epoch_time, genome_ts = dna_from_genome_history(
        genome_history,
        with_meta=True,
    )

    # 2) System dump → Env + VIX
    env, vix = market_env_from_system_dump(system_dump)

    # 3) DNA evolve
    evo = DNAEvolutionEngine()
    new_dna, evolve_reason = evo.evolve(
        current=dna,
        equity_change_pct=last_equity_change_pct,
        env=env,
    )

    # 4) Position sizing
    asset = AssetContext(
        symbol=symbol,
        price=price,
        volatility_score=volatility_score,
    )
    sizer = PositionSizer(cfg or PositionSizingConfig())
    sizing = sizer.size_position(
        dna=new_dna,
        env=env,
        equity=equity,
        asset=asset,
        open_risk_pct=open_risk_pct,
        is_long=True,
        vix=vix,
    )

    # 5) Academy update (optional)
    academy_record: Optional[GenomeRecord] = None
    if academy is not None:
        academy_record = academy.record_cycle(
            genome_id=champion_id,
            family=champion_family,
            equity_change_pct=last_equity_change_pct,
            trades_in_cycle=trades_in_cycle,
            winning_trades=winning_trades,
            timestamp=time.time(),
        )

    return {
        "champion_id": champion_id,
        "champion_family": champion_family,
        "epoch_time": epoch_time,
        "genome_timestamp": genome_ts,
        "old_dna": dna,
        "new_dna": new_dna,
        "evolve_reason": evolve_reason,
        "sizing": sizing,
        "env": env,
        "vix": vix,
        "academy_record": academy_record,
    }


# ===========================
#  DEMO / LAB ENTRYPOINT
# ===========================


if __name__ == "__main__":
    # Example lab usage with local JSON files
    try:
        gh = load_json_file("genome_history.json")
        sd = load_json_file("system_dump.json")

        academy = DNAAcademy()

        result = run_dna_cycle_from_snapshots(
            genome_history=gh,
            system_dump=sd,
            equity=1000.0,
            symbol="BTC/USDT:USDT",
            price=100000.0,
            volatility_score=0.05,
            last_equity_change_pct=0.8,
            open_risk_pct=2.0,
            academy=academy,
            trades_in_cycle=1,
        )

        print("==== DNA CYCLE RESULT ====")
        print("CHAMPION:", result["champion_id"], "| FAMILY:", result["champion_family"])
        print("OLD_DNA:", result["old_dna"])
        print("NEW_DNA:", result["new_dna"])
        print("REASON:", result["evolve_reason"])
        print("SIZING:", result["sizing"])
        print("ENV:", result["env"])
        print("VIX:", result["vix"])
        if result["academy_record"] is not None:
            rec = result["academy_record"]
            print("ACADEMY:", rec.genome_id, rec.family, rec.rank, f"score={rec.last_score:.2f}", f"WR={rec.win_rate:.2%}")

        # Show simple leaderboard
        print("\n==== ACADEMY LEADERBOARD ====")
        for r in academy.leaderboard(top_n=5):
            print(
                r.genome_id,
                r.family,
                r.rank,
                f"score={r.last_score:.2f}",
                f"WR={r.win_rate:.2%}",
                f"DD={r.max_drawdown_pct:.2f}%",
            )

    except FileNotFoundError:
        print("Lab demo: genome_history.json / system_dump.json not found. Only module import is available.")
