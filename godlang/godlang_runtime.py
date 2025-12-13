# -*- coding: utf-8 -*-
"""
GODLANG RUNTIME v0
------------------

Şimdilik GODLANG'ı "JSON policy" modunda çalıştırıyoruz.

script: str  -> JSON string bekleniyor, örn:
    {
      "quantum_flow_multiplier": 2.5,
      "risk_score": -30.0
    }

context: dict -> AGG tarafından sağlanan env/dna/equity bilgisi.
"""

from __future__ import annotations
import json
from typing import Any, Dict


def evaluate_policy(script: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Basit JSON policy:
      - script geçerli JSON dictionary ise doğrudan onu döndür.
      - değilse {} döndür.

    Beklenen key örnekleri:
      - "quantum_flow_multiplier": float
      - "risk_score": float
      - "max_leverage": float
      - vs.
    """
    if not script:
        return {}

    script = script.strip()
    try:
        data = json.loads(script)
    except Exception:
        return {}

    if not isinstance(data, dict):
        return {}

    return data
