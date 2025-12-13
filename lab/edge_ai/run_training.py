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
