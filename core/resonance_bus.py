# -*- coding: utf-8 -*-
"""
RESONANCE BUS v1.0
GODBRAIN QUANTUM – Rezonans Lab Köprüsü

Tek görev: Lab kaynaklarından (neural_stream.log, Redis, vs.)
anlık rezonans durumunu okuyup sistemin geri kalanına temiz
bir interface ile vermek.

Bu modül:
- Çift yarık / EEG / Optical Nexus / sim sinyallerinin nihai çıktısını
  "ResonanceState" olarak temsil eder.
- AGG, APEX, GODLANG, DNA Academy hep buradan beslenir.
"""

from __future__ import annotations
import os
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Literal

# Redis opsiyonel
try:
    import redis as _redis_lib
except ImportError:
    _redis_lib = None


ResMode = Literal[
    "IDLE",                # hiçbir özel rezonans yok
    "QUANTUM_RESONANCE",   # bizim mevcut PROMETHEUS modu
    "COHERENT",            # stabil, düşük entropi
    "DECOHERENCE",         # gürültülü / bozulmuş
    "MANUAL_OVERRIDE",     # insan override etmiş
]


@dataclass
class ResonanceState:
    active: bool
    mode: ResMode
    flow_mult: float
    energy_state: float       # 0.0–1.0 arası normalize enerji (0 düşük, 1 çok yüksek)
    source: str               # "SIM", "EEG", "OPTICAL", "MANUAL", "REDIS", ...
    last_event_id: str
    last_updated_ts: float    # epoch seconds

    @property
    def is_fresh(self) -> bool:
        # 60 saniyeden eski olayları "bayat" say
        return (time.time() - self.last_updated_ts) <= 60.0


class ResonanceBus:
    """
    Tüm rezonans kaynakları için tek arayüz.

    Kullanım:
        bus = ResonanceBus(
            neural_stream_path=Path("/mnt/c/godbrain-quantum/logs/neural_stream.log"),
            redis_dsn=os.getenv("GODBRAIN_REDIS_DSN", "")
        )
        state = bus.get_state()
    """

    def __init__(
        self,
        neural_stream_path: Path,
        redis_dsn: Optional[str] = None,
        redis_channel: str = "godbrain:resonance",
    ):
        self.neural_stream_path = neural_stream_path
        self.redis_channel = redis_channel
        self._redis = None

        if redis_dsn and _redis_lib is not None:
            try:
                self._redis = _redis_lib.from_url(redis_dsn)
            except Exception:
                self._redis = None

        # Varsayılan "IDLE" state
        self._state = ResonanceState(
            active=False,
            mode="IDLE",
            flow_mult=1.0,
            energy_state=0.0,
            source="SIM",
            last_event_id="INIT",
            last_updated_ts=time.time(),
        )

    # --------------------- PUBLIC API -----------------------------------

    def get_state(self) -> ResonanceState:
        """
        Sisteme verilecek son rezonans durumu.

        - Önce Redis'ten en taze olayı dene (varsa).
        - Yoksa neural_stream.log tail et.
        - İkisi de yoksa, en son bildiğimiz state'i döndür.
        """
        updated = False

        # 1) Redis varsa onu dene
        if self._redis is not None:
            try:
                msg = self._redis.lindex(self.redis_channel, -1)
                if msg is not None:
                    payload = json.loads(msg)
                    self._state = self._state_from_payload(payload, source="REDIS")
                    updated = True
            except Exception:
                # Redis patlarsa sessiz düş
                pass

        # 2) neural_stream.log'tan oku (PROMETHEUS_ALERT)
        try:
            tail_event = self._tail_last_prometheus_alert(self.neural_stream_path)
            if tail_event is not None:
                self._state = self._state_from_payload(tail_event, source="NEURAL_STREAM")
                updated = True
        except Exception:
            pass

        # 3) Hiç güncelleme yoksa bile mevcut state'i döndür
        if not updated:
            # Bayatsa bile sistem hiç değilse fallback'e sahip olsun
            return self._state

        return self._state

    # --------------------- INTERNAL HELPERS -----------------------------

    def _tail_last_prometheus_alert(self, path: Path, window_bytes: int = 8192) -> Optional[dict]:
        """
        Dosyanın son ~8KB'ını okuyup
        son "CHANNEL:PROMETHEUS_ALERT" satırındaki JSON payload'ı parse eder.
        """
        if not path.exists():
            return None

        with path.open("rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            read_size = min(window_bytes, size)
            f.seek(-read_size, os.SEEK_END)
            data = f.read().decode("utf-8", errors="ignore")

        lines = data.splitlines()
        alert_lines = [ln for ln in lines if "CHANNEL:PROMETHEUS_ALERT" in ln]
        if not alert_lines:
            return None

        last = alert_lines[-1]

        # Satırdan JSON'ı sök
        if ">>>" in last:
            _, payload = last.split(">>>", 1)
        else:
            idx = last.find("{")
            if idx == -1:
                return None
            payload = last[idx:]

        try:
            return json.loads(payload.strip())
        except Exception:
            return None

    def _state_from_payload(self, payload: dict, source: str) -> ResonanceState:
        """
        payload formatı (örnek):

        {
          "status": {
            "direction": "QUANTUM_RESONANCE",
            "flow_multiplier": 2.0,
            "energy_level": 0.73,         # opsiyonel
            "mode": "QUANTUM_RESONANCE",  # opsiyonel, yoksa direction kullanılır
            "event_id": "abc123"          # opsiyonel
          }
        }
        """
        status = payload.get("status", {})

        direction = str(status.get("direction", "IDLE"))
        mode: ResMode = status.get("mode", direction)  # mode yoksa direction kullan
        if mode not in ("IDLE", "QUANTUM_RESONANCE", "COHERENT", "DECOHERENCE", "MANUAL_OVERRIDE"):
            mode = "IDLE"

        flow_mult = float(status.get("flow_multiplier", 1.0))
        energy_state = float(status.get("energy_level", 0.0))
        energy_state = max(0.0, min(1.0, energy_state))  # clamp 0–1

        event_id = str(status.get("event_id") or payload.get("event_id") or "unknown")

        active = mode in ("QUANTUM_RESONANCE", "COHERENT", "MANUAL_OVERRIDE")

        return ResonanceState(
            active=active,
            mode=mode,
            flow_mult=flow_mult,
            energy_state=energy_state,
            source=source,
            last_event_id=event_id,
            last_updated_ts=time.time(),
        )
