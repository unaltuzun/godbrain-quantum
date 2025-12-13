#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GODBRAIN NIGHT SNIPER MODE

Tek komutla gece profiline geçen risk ayarları:
- Tek pozisyon (sniper)
- Limitli günlük zarar
- QScore için sniper eşiği (90) hint'i
"""

import json
import shutil
from pathlib import Path
from datetime import datetime

ROOT = Path("/mnt/c/godbrain-quantum")
HUMAN_BIAS = ROOT / "human_bias.json"
HUMAN_CONTROL = ROOT / "human_control.json"
ENV_PATH = ROOT / ".env"


def load_json(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def save_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def backup_file(path: Path) -> None:
    if not path.exists():
        return
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_name(f"{path.name}.{ts}.bak")
    shutil.copy2(path, backup)


def upsert_env(lines, key, value):
    out = []
    found = False
    for line in lines:
        if line.strip().startswith(f"{key}="):
            out.append(f"{key}={value}\n")
            found = True
        else:
            out.append(line)
    if not found:
        out.append(f"{key}={value}\n")
    return out


def main():
    print("====================================================")
    print("  GODBRAIN NIGHT SNIPER MODE – PROFILE LOADER")
    print("====================================================")

    # --- JSON yedekleri ---
    backup_file(HUMAN_BIAS)
    backup_file(HUMAN_CONTROL)

    # --- human_bias.json güncelle ---
    bias = load_json(HUMAN_BIAS, {})
    bias.setdefault("bias_mode", "NEUTRAL")
    bias.setdefault("risk_adjustment", 1.0)

    bias["bias_mode"] = "SNIPER_NIGHT"
    bias["risk_adjustment"] = 0.8
    # İleride koddan kullanmak için hint:
    bias["qscore_sniper_threshold"] = 90.0
    bias["notes"] = "Set by tools/night_sniper_mode.py (night sniper profile)"

    save_json(HUMAN_BIAS, bias)
    print(f"[NIGHT] human_bias.json güncellendi → {HUMAN_BIAS}")

    # --- human_control.json güncelle ---
    ctrl = load_json(HUMAN_CONTROL, {})
    ctrl.setdefault("kill_switch", False)
    ctrl.setdefault("block_new_entries", False)

    # Tek sniper pozisyon
    ctrl["max_open_positions"] = 1
    # Gece için makul daily loss cap (istersen elle değiştirirsin)
    ctrl["max_daily_loss_usd"] = 30.0
    ctrl["notes"] = "Night mode: single-position sniper profile"

    save_json(HUMAN_CONTROL, ctrl)
    print(f"[NIGHT] human_control.json güncellendi → {HUMAN_CONTROL}")

    # --- .env içindeki APEX_* hint değişkenleri ---
    if ENV_PATH.exists():
        env_lines = ENV_PATH.read_text(encoding="utf-8").splitlines(keepends=True)
    else:
        env_lines = []

    env_lines = upsert_env(env_lines, "APEX_MODE", "SNIPER_NIGHT")
    env_lines = upsert_env(env_lines, "APEX_SNIPER_QSCORE", "90")
    # Sniper için kaldıraç hint'i (kodda kullanmak için hazır)
    env_lines = upsert_env(env_lines, "APEX_SNIPER_LEVERAGE", "20")
    # Tek atımlık mermi boyutu (USDT)
    env_lines = upsert_env(env_lines, "APEX_SNIPER_MAX_NOTIONAL_USDT", "30")
    # Normal scalp işlemler için tavan (USDT)
    env_lines = upsert_env(env_lines, "APEX_SCALP_MAX_NOTIONAL_USDT", "8")
    # “Kaliteli” coin listesi hint'i
    env_lines = upsert_env(
        env_lines,
        "APEX_QUALITY_SYMBOLS",
        "BTC-USDT-SWAP,ETH-USDT-SWAP,SOL-USDT-SWAP",
    )

    ENV_PATH.write_text("".join(env_lines), encoding="utf-8")
    print(f"[NIGHT] .env APEX night sniper değişkenleri güncellendi → {ENV_PATH}")

    print("\nArtık gece modu profili yüklü.")
    print("Servisleri yeniden başlat:")
    print("  pm2 restart godbrain-quantum godmoney-apex")
    print("\nSonra bot, fiilen:")
    print("  - Tek sembol açık (sniper stack)")
    print("  - Günlük zarar 30$ civarında sınırlı")
    print("  - QScore >= 90 için sniper eşiği hint'li")
    print("\nBundan sonrası GODBRAIN risk motorunun işi.")


if __name__ == "__main__":
    main()
