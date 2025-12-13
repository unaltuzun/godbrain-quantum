import re
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import torch
from torch.utils.data import Dataset


class GodbrainLogDataset(Dataset):
    """
    Tolerant parser for logs/agg_decisions.log.

    Requires: line contains "EXECUTE:"
    Extracts if present:
      - action, symbol
      - Regime:<...>
      - Flow:<num>x
      - QScore:<num>
      - DNAx:<num> or DNA:<num>
      - VOL:<num>

    Features (8):
      [conviction, flow_mult, voltran, q_score_norm, dna_mult, 0, 0, 0]
    conviction defaults to q_score/100
    """

    RE_HEAD = re.compile(r"EXECUTE:\s*(?P<action>\w+)\s+(?P<symbol>\S+)", re.IGNORECASE)
    RE_REGIME = re.compile(r"Regime:(?P<regime>\S+)", re.IGNORECASE)
    RE_FLOW = re.compile(r"Flow:(?P<flow>[\d\.]+)x", re.IGNORECASE)
    RE_QSCORE = re.compile(r"QScore:(?P<qscore>[\d\.]+)", re.IGNORECASE)
    RE_DNA = re.compile(r"(DNAx|DNA):(?P<dna>[\d\.]+)", re.IGNORECASE)
    RE_VOL = re.compile(r"VOL:(?P<vol>[\d\.]+)", re.IGNORECASE)

    def __init__(self, log_path: str | Path) -> None:
        self.x_data: np.ndarray
        self.y_data: np.ndarray

        rows = self._parse_logs(Path(log_path))
        if not rows:
            print(f"[DATASET] Uyarı: {log_path} içinde parse edilebilir EXECUTE satırı yok.")
            self.x_data = np.zeros((0, 8), dtype=np.float32)
            self.y_data = np.zeros((0,), dtype=np.int64)
            return

        feats_list: List[List[float]] = []
        labels_list: List[int] = []

        regime_map: Dict[str, int] = {}
        next_id = 0

        for r in rows:
            regime = r.get("regime", "UNKNOWN")
            if regime not in regime_map:
                regime_map[regime] = next_id
                next_id += 1

            q_score = float(r.get("q_score", 50.0))
            conviction = float(r.get("conviction", q_score / 100.0))

            feats_list.append([
                conviction,
                float(r.get("flow_mult", 1.0)),
                float(r.get("voltran", 1.0)),
                q_score / 100.0,
                float(r.get("dna_mult", 1.0)),
                0.0, 0.0, 0.0,
            ])
            labels_list.append(regime_map[regime])

        self.x_data = np.array(feats_list, dtype=np.float32)
        self.y_data = np.array(labels_list, dtype=np.int64)
        print(f"[DATASET] {len(self.x_data)} örnek, {len(regime_map)} rejim sınıfı.")

    def _parse_logs(self, path: Path) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        if not path.exists():
            print(f"[DATASET] Log bulunamadı: {path}")
            return rows

        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if "EXECUTE:" not in line:
                continue

            m = self.RE_HEAD.search(line)
            if not m:
                continue

            action = m.group("action").upper()
            symbol = m.group("symbol")

            regime = "UNKNOWN"
            flow = 1.0
            qscore = 50.0
            dna = 1.0
            vol = 1.0

            mr = self.RE_REGIME.search(line)
            if mr:
                regime = mr.group("regime")

            mf = self.RE_FLOW.search(line)
            if mf:
                flow = float(mf.group("flow"))

            mq = self.RE_QSCORE.search(line)
            if mq:
                qscore = float(mq.group("qscore"))

            md = self.RE_DNA.search(line)
            if md:
                dna = float(md.group("dna"))

            mv = self.RE_VOL.search(line)
            if mv:
                vol = float(mv.group("vol"))

            rows.append({
                "action": action,
                "symbol": symbol,
                "regime": regime,
                "flow_mult": flow,
                "q_score": qscore,
                "dna_mult": dna,
                "voltran": vol,
            })

        return rows

    def __len__(self) -> int:
        return int(self.x_data.shape[0])

    def __getitem__(self, idx: int):
        return (
            torch.tensor(self.x_data[idx], dtype=torch.float32),
            torch.tensor(self.y_data[idx], dtype=torch.int64),
        )
