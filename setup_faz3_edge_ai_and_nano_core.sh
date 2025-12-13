#!/usr/bin/env bash
set -euo pipefail

echo ">>> GODBRAIN – FAZ 3 Edge AI + Nano Core Setup starting..."

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

###############################################
# 0) KLASÖRLER
###############################################
mkdir -p edge_ai lab/edge_ai models/edge_ai config logs nano_core/include nano_core/src

###############################################
# 1) FAZ 3 EDGE AI BASE KURULUMU
###############################################

echo ">>> [FAZ3] Config yazılıyor..."
cat > config/edge_ai_config.json << 'EOF'
{
  "EDGE_AI_ENABLED": true,
  "MODEL_DIR": "models/edge_ai",
  "REGIME_MODEL_FILE": "regime_v1.pt",
  "ANOMALY_MODEL_FILE": "anomaly_v1.pt",
  "FEATURE_DIM": 8,
  "CONFIDENCE_THRESHOLD": 0.65,
  "ANOMALY_THRESHOLD": 0.0025,
  "MAX_INFERENCE_LATENCY_MS": 10
}
EOF

cat > edge_ai/__init__.py << 'EOF'
"""
GODBRAIN - Edge AI live inference package (FAZ 3).
"""
from .inference import EdgeInferenceClient

__all__ = ["EdgeInferenceClient"]
EOF

cat > edge_ai/inference.py << 'EOF'
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
EOF

cat > lab/edge_ai/__init__.py << 'EOF'
"""
GODBRAIN - Edge AI Laboratory (dataset + models + training).
"""
EOF

cat > lab/edge_ai/datasets.py << 'EOF'
import re
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import torch
from torch.utils.data import Dataset


class GodbrainLogDataset(Dataset):
    """
    logs/agg_decisions.log içinden EXECUTE satırlarını parse eder.

    Features (8):
      [conviction, flow_mult, voltran, q_score_norm, dna_mult, 0, 0, 0]

    Label:
      Regime string -> integer mapping
    """

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
        # Bu regex log formatın farklıysa boş döner; sorun değil, sadece eğitim yapmaz.
        re_exec = re.compile(
            r"EXECUTE:\s+(?P<action>\w+)\s+(?P<symbol>[^ ]+)\s+\|\s+\$(?P<size>[\d\.]+)\s+\|"
            r"\s+Regime:(?P<regime>[^ ]+)\s+\|\s+Flow:(?P<flow>[\d\.]+)x\s+\|"
            r"\s+QScore:(?P<qscore>[\d\.]+)\s+\|\s+DNAx:(?P<dna>[\d\.]+)\s+\|\s+VOL:(?P<vol>[\d\.]+)"
        )

        if not path.exists():
            print(f"[DATASET] Log bulunamadı: {path}")
            return rows

        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if "EXECUTE:" not in line:
                continue
            m = re_exec.search(line)
            if not m:
                continue
            g = m.groupdict()
            rows.append({
                "action": g["action"],
                "symbol": g["symbol"],
                "size_usd": float(g["size"]),
                "regime": g["regime"],
                "flow_mult": float(g["flow"]),
                "q_score": float(g["qscore"]),
                "dna_mult": float(g["dna"]),
                "voltran": float(g["vol"]),
            })
        return rows

    def __len__(self) -> int:
        return int(self.x_data.shape[0])

    def __getitem__(self, idx: int):
        return (
            torch.tensor(self.x_data[idx], dtype=torch.float32),
            torch.tensor(self.y_data[idx], dtype=torch.int64),
        )
EOF

cat > lab/edge_ai/models_regime.py << 'EOF'
import torch
import torch.nn as nn


class RegimeClassifier(nn.Module):
    def __init__(self, input_dim: int = 8, hidden_dim: int = 16, num_classes: int = 3) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)
EOF

cat > lab/edge_ai/models_anomaly.py << 'EOF'
import torch
import torch.nn as nn


class AnomalyAutoEncoder(nn.Module):
    def __init__(self, input_dim: int = 8, bottleneck_dim: int = 4) -> None:
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, bottleneck_dim),
            nn.ReLU(),
        )
        self.decoder = nn.Sequential(
            nn.Linear(bottleneck_dim, input_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.decoder(self.encoder(x))
EOF

cat > lab/edge_ai/run_training.py << 'EOF'
from pathlib import Path

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader

from .datasets import GodbrainLogDataset
from .models_regime import RegimeClassifier
from .models_anomaly import AnomalyAutoEncoder

EPOCHS = 5
BATCH_SIZE = 64

def train() -> None:
    root = Path(__file__).resolve().parents[2]
    log_file = root / "logs" / "agg_decisions.log"
    model_dir = root / "models" / "edge_ai"

    print(">>> GODBRAIN Edge AI Training Lab <<<")
    print(f"[1/4] Dataset log: {log_file}")

    dataset = GodbrainLogDataset(log_file)
    if len(dataset) == 0:
        print("[ERR] Dataset boş. logs/agg_decisions.log formatı regex ile uyuşmuyor olabilir.")
        return

    loader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)

    # Regime classifier
    print("[2/4] RegimeClassifier eğitiliyor...")
    num_classes = int(dataset.y_data.max() + 1)
    clf = RegimeClassifier(input_dim=8, hidden_dim=16, num_classes=num_classes)
    opt_clf = optim.Adam(clf.parameters(), lr=1e-2)
    crit_clf = nn.CrossEntropyLoss()

    for epoch in range(EPOCHS):
        clf.train()
        total = 0.0
        for x, y in loader:
            opt_clf.zero_grad()
            out = clf(x)
            loss = crit_clf(out, y)
            loss.backward()
            opt_clf.step()
            total += float(loss.item())
        print(f"    [Regime] Epoch {epoch+1}/{EPOCHS} Loss: {total:.4f}")

    # Anomaly AE
    print("[3/4] AnomalyAutoEncoder eğitiliyor...")
    ae = AnomalyAutoEncoder(input_dim=8, bottleneck_dim=4)
    opt_ae = optim.Adam(ae.parameters(), lr=1e-2)
    crit_ae = nn.MSELoss()

    for epoch in range(EPOCHS):
        ae.train()
        total = 0.0
        for x, _ in loader:
            opt_ae.zero_grad()
            recon = ae(x)
            loss = crit_ae(recon, x)
            loss.backward()
            opt_ae.step()
            total += float(loss.item())
        print(f"    [AE] Epoch {epoch+1}/{EPOCHS} Loss: {total:.4f}")

    model_dir.mkdir(parents=True, exist_ok=True)
    torch.save(clf.state_dict(), model_dir / "regime_v1.pt")
    torch.save(ae.state_dict(), model_dir / "anomaly_v1.pt")
    print(f"[4/4] Modeller kaydedildi: {model_dir}")

if __name__ == "__main__":
    train()
EOF

echo ">>> [FAZ3] Edge AI base kurulum tamamlandı."

###############################################
# 2) NANO CORE C ÇEKİRDEĞİ İSKELETİ
###############################################

cat > nano_core/README.md << 'EOF'
# GODBRAIN Nano Core (Ultra-Low Latency Engine)

Bu klasör, GODBRAIN için tasarlanan ultra-low latency C çekirdeğinin iskeletidir.

Hedefler:
- Lock-free ring buffer (SPSC)
- Branchless risk kontrolü
- rdtsc ile latency ölçümü
- SIMD placeholder (ileride gerçek veri düzeniyle)

Derleme:
  cd nano_core
  make
  ./nano_core_demo
EOF

cat > nano_core/include/market.h << 'EOF'
#ifndef GODBRAIN_MARKET_H
#define GODBRAIN_MARKET_H

#include <stdatomic.h>
#include <stdint.h>
#include <string.h>

#define CACHE_LINE_SIZE 64
#define RING_SIZE 4096  // 2^n olmalı

// Tick data: ring içinde plain struct (atomic değil); atomic head/tail yeterli.
typedef struct __attribute__((aligned(64))) {
    uint64_t price;        // örn: 1000.00 * 100
    uint64_t volume;
    uint64_t timestamp_ns;
} MarketTick;

typedef struct __attribute__((aligned(CACHE_LINE_SIZE))) {
    MarketTick buffer[RING_SIZE];
    _Atomic uint64_t head;
    _Atomic uint64_t tail;
} LockFreeRing;

static inline void ring_init(LockFreeRing* ring) {
    memset(ring, 0, sizeof(*ring));
}

static inline int ring_push(LockFreeRing* ring, const MarketTick* tick) {
    uint64_t head = atomic_load_explicit(&ring->head, memory_order_relaxed);
    uint64_t next_head = (head + 1) & (RING_SIZE - 1);

    uint64_t tail = atomic_load_explicit(&ring->tail, memory_order_acquire);
    if (next_head == tail) return 0; // full

    ring->buffer[head] = *tick;
    atomic_store_explicit(&ring->head, next_head, memory_order_release);
    return 1;
}

static inline int ring_pop(LockFreeRing* ring, MarketTick* out) {
    uint64_t tail = atomic_load_explicit(&ring->tail, memory_order_relaxed);
    uint64_t head = atomic_load_explicit(&ring->head, memory_order_acquire);
    if (tail == head) return 0; // empty

    *out = ring->buffer[tail];
    uint64_t next_tail = (tail + 1) & (RING_SIZE - 1);
    atomic_store_explicit(&ring->tail, next_tail, memory_order_release);
    return 1;
}

#endif // GODBRAIN_MARKET_H
EOF

cat > nano_core/include/risk.h << 'EOF'
#ifndef GODBRAIN_RISK_H
#define GODBRAIN_RISK_H

#include <stdint.h>

typedef struct {
    double entry_price;
    double quantity;
    double stop_loss;
    double take_profit;
} Position;

typedef enum {
    RISK_NONE = 0,
    RISK_TP   = 1,
    RISK_SL   = 2,
    RISK_BOTH = 3
} risk_level_t;

// Branchless-ish risk kontrolü (0/1 mask)
static inline risk_level_t check_risk(const Position* pos, double last_price) {
    double pnl = (last_price - pos->entry_price) * pos->quantity;

    uint64_t is_stop_loss   = (pnl <= -pos->stop_loss) ? 1ULL : 0ULL;
    uint64_t is_take_profit = (pnl >=  pos->take_profit) ? 1ULL : 0ULL;

    return (risk_level_t)((is_stop_loss << 1) | is_take_profit);
}

#endif // GODBRAIN_RISK_H
EOF

cat > nano_core/include/perf.h << 'EOF'
#ifndef GODBRAIN_PERF_H
#define GODBRAIN_PERF_H

#include <stdint.h>
#include <stdio.h>

#ifndef CPU_FREQ_HZ
#define CPU_FREQ_HZ 3000000000.0 // default 3 GHz (istersen güncelle)
#endif

static inline uint64_t rdtsc(void) {
    unsigned int lo, hi;
    __asm__ __volatile__("rdtsc" : "=a"(lo), "=d"(hi));
    return ((uint64_t)hi << 32) | lo;
}

static inline void measure_latency(const char* label, void (*fn)(void)) {
    uint64_t start = rdtsc();
    fn();
    uint64_t end = rdtsc();
    uint64_t cycles = end - start;
    double ns = cycles * (1e9 / CPU_FREQ_HZ);

    printf("%s: %llu cycles (%.2f ns)\n",
           label,
           (unsigned long long)cycles,
           ns);
}

#endif // GODBRAIN_PERF_H
EOF

cat > nano_core/src/orderbook_simd.c << 'EOF'
#include <stddef.h>

// SIMD placeholder: gerçek orderbook bellek düzeni netleşince AVX/NEON optimize edilir.
// Şimdilik sadece derlenebilir iskelet.

typedef struct {
    double bid;
    double ask;
    int64_t microtimestamp;
} OrderBookLevel;

double process_orderbook_scalar(const OrderBookLevel* levels, size_t n) {
    double acc = 0.0;
    for (size_t i = 0; i < n; i++) {
        acc += (levels[i].ask - levels[i].bid);
    }
    return acc;
}
EOF

cat > nano_core/src/main.c << 'EOF'
#include <stdio.h>
#include <time.h>

#include "market.h"
#include "risk.h"
#include "perf.h"

static LockFreeRing tick_ring;

static void fake_tick_producer(void) {
    MarketTick t;
    t.price = 100000; // 1000.00 * 100
    t.volume = 1000;
    t.timestamp_ns = (uint64_t)time(NULL) * 1000000000ULL;
    ring_push(&tick_ring, &t);
}

static void fake_tick_consumer(void) {
    MarketTick t;
    if (ring_pop(&tick_ring, &t)) {
        double price = (double)t.price / 100.0;
        Position pos = {
            .entry_price = 995.0,
            .quantity = 1.0,
            .stop_loss = 10.0,
            .take_profit = 15.0
        };
        risk_level_t r = check_risk(&pos, price);
        printf("Tick consumed: price=%.2f, risk_level=%d\n", price, (int)r);
    }
}

static void measure_demo(void) {
    measure_latency("fake_tick_producer", fake_tick_producer);
    measure_latency("fake_tick_consumer", fake_tick_consumer);
}

int main(void) {
    printf("GODBRAIN Nano Core Demo starting...\n");
    ring_init(&tick_ring);

    for (int i = 0; i < 5; i++) {
        measure_demo();
    }

    printf("GODBRAIN Nano Core Demo finished.\n");
    return 0;
}
EOF

cat > nano_core/Makefile << 'EOF'
CC = gcc
CFLAGS = -O3 -std=c11 -Wall -Wextra -march=native
INCLUDE = -Iinclude

SRC = src/main.c src/orderbook_simd.c
OBJ = $(SRC:.c=.o)
TARGET = nano_core_demo

all: $(TARGET)

$(TARGET): $(OBJ)
	$(CC) $(CFLAGS) $(INCLUDE) -o $@ $^

%.o: %.c
	$(CC) $(CFLAGS) $(INCLUDE) -c $< -o $@

clean:
	rm -f $(OBJ) $(TARGET)

.PHONY: all clean
EOF

echo ">>> [NANO] Nano Core iskeleti hazır."

cat << 'EOF'

===============================================
FAZ 3 Edge AI + Nano Core kurulum tamam.
Sonraki adımlar:

1) (Opsiyonel) Python bağımlılıkları:
   pip install -U numpy torch

2) Modelleri eğit:
   python3 -m lab.edge_ai.run_training
   ls models/edge_ai

3) Nano core derle ve demo çalıştır:
   cd nano_core
   make
   ./nano_core_demo

Not:
- Eğitim datası logs/agg_decisions.log içindeki EXECUTE satır formatına bağlıdır.
  Eğer boş dataset görürsen, regex'i senin log formatına göre patch'leriz.
- agg.py'ye dokunulmadı (FAZ 3.1 observer hook sonraki patch).
===============================================

EOF

