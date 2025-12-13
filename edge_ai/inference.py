import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import torch

from lab.edge_ai.models_regime import RegimeClassifier
from lab.edge_ai.models_anomaly import AnomalyAutoEncoder


class EdgeInferenceClient:
    """
    FAZ 3: log tabanlı eğitilmiş modellerle
      - regime pred
      - anomaly score
    üretir ve decision_payload.extras.edge_ai içine yazar.

    Fail-safe: hata olursa payload bozulmadan geri döner.
    """

    def __init__(self, config_path: str = "config/edge_ai_config.json") -> None:
        self.enabled: bool = False
        self.config: Dict[str, Any] = {}
        self.regime_model: Optional[torch.nn.Module] = None
        self.anomaly_model: Optional[torch.nn.Module] = None

        cfg_file = Path(config_path)
        if not cfg_file.exists():
            print(f"[EDGE-AI] Config bulunamadı: {config_path}")
            return

        try:
            self.config = json.loads(cfg_file.read_text(encoding="utf-8"))
            if not self.config.get("EDGE_AI_ENABLED", False):
                print("[EDGE-AI] EDGE_AI_ENABLED=false, pasif.")
                return
            self._load_models()
        except Exception as e:
            print(f"[EDGE-AI] Init error, pasif: {e}")
            self.enabled = False

    def _load_models(self) -> None:
        root = Path(self.config.get("MODEL_DIR", "models/edge_ai"))
        feat_dim = int(self.config.get("FEATURE_DIM", 8))

        regime_path = root / self.config.get("REGIME_MODEL_FILE", "regime_v1.pt")
        anomaly_path = root / self.config.get("ANOMALY_MODEL_FILE", "anomaly_v1.pt")

        if not regime_path.exists() or not anomaly_path.exists():
            print(f"[EDGE-AI] Model dosyaları eksik: {regime_path}, {anomaly_path}")
            self.enabled = False
            return

        self.regime_model = RegimeClassifier(input_dim=feat_dim, hidden_dim=16, num_classes=3)
        self.regime_model.load_state_dict(torch.load(regime_path, map_location="cpu"))
        self.regime_model.eval()

        self.anomaly_model = AnomalyAutoEncoder(input_dim=feat_dim, bottleneck_dim=4)
        self.anomaly_model.load_state_dict(torch.load(anomaly_path, map_location="cpu"))
        self.anomaly_model.eval()

        self.enabled = True
        print(f"[EDGE-AI] Modeller yüklendi: {root}")

    def _extract_features(self, decision_payload: Dict[str, Any]) -> torch.Tensor:
        extras = decision_payload.get("extras", {})
        q_score = float(extras.get("quantum_score", 50.0))
        conviction = float(extras.get("conviction", q_score / 100.0))

        feats = [
            conviction,
            float(extras.get("flow_mult", 1.0)),
            float(extras.get("voltran_factor", 1.0)),
            q_score / 100.0,
            float(extras.get("dna_mult", 1.0)),
            0.0, 0.0, 0.0,
        ]
        return torch.tensor([feats], dtype=torch.float32)

    def enrich_decision(self, decision_payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.enabled or self.regime_model is None or self.anomaly_model is None:
            return decision_payload

        start = time.time()
        max_latency_ms = float(self.config.get("MAX_INFERENCE_LATENCY_MS", 10.0))

        try:
            features = self._extract_features(decision_payload)

            with torch.no_grad():
                recon = self.anomaly_model(features)
                loss = torch.mean((features - recon) ** 2).item()

            anomaly_th = float(self.config.get("ANOMALY_THRESHOLD", 0.0025))
            is_anomaly = loss > anomaly_th

            with torch.no_grad():
                logits = self.regime_model(features)
                probs = torch.softmax(logits, dim=1).cpu().numpy()[0]
                pred_class = int(np.argmax(probs))
                confidence = float(np.max(probs))

            latency_ms = (time.time() - start) * 1000.0
            if latency_ms > max_latency_ms:
                print(f"[EDGE-AI] Uyarı: inference {latency_ms:.2f} ms (limit {max_latency_ms} ms)")

            ai_meta = {
                "ai_active": True,
                "anomaly_score": round(loss, 6),
                "is_anomaly": bool(is_anomaly),
                "regime_pred_class": pred_class,
                "regime_confidence": round(confidence, 4),
                "inference_ms": round(latency_ms, 2),
            }

            extras = decision_payload.setdefault("extras", {})
            extras["edge_ai"] = ai_meta

        except Exception as e:
            print(f"[EDGE-AI] Inference error: {e}")
            extras = decision_payload.setdefault("extras", {})
            extras["edge_ai_error"] = str(e)

        return decision_payload
