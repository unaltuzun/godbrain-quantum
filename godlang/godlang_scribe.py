# -*- coding: utf-8 -*-
import json
import time
import os
from pathlib import Path
from datetime import datetime

# AYARLAR
SHARED_DIR = Path(r"C:\godbrain-universe\godbrain-shared")
DNA_FILE = SHARED_DIR / "live_dna.json"
GODLANG_FILE = Path(r"C:\godbrain-quantum\current_strategy.god")
PROMETHEUS_FILE = SHARED_DIR.parent / "prometheus_status.json"

def load_json(path):
    try:
        with open(path, 'r') as f: return json.load(f)
    except: return {}

def transpile_to_godlang():
    """DNA ve Sensör verilerini GODLANG formatına çevirir"""
    
    dna = load_json(DNA_FILE)
    prom = load_json(PROMETHEUS_FILE)
    
    strat = dna.get("strategy", {})
    meta = dna.get("meta", {})
    prom_status = prom.get("status", {})
    
    # GODLANG SENTAKS OLUŞTURMA
    god_code = []
    god_code.append(f"// GODLANG AUTO-GENERATED SCRIPT")
    god_code.append(f"// TIME: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    god_code.append(f"// SOURCE: {meta.get('source', 'UNKNOWN')}")
    god_code.append(f"")
    
    # 1. ORTAM TANIMI
    god_code.append(f"ENVIRONMENT {{")
    god_code.append(f"    UNIVERSE_ID: '{meta.get('champion', 'GENESIS')}'")
    god_code.append(f"    CONTEXT: '{meta.get('note', 'None')}'")
    god_code.append(f"    WHALE_FLOW: {prom_status.get('direction', 'NEUTRAL')}")
    god_code.append(f"}}")
    god_code.append(f"")
    
    # 2. DEĞİŞKENLER
    risk = strat.get('position_size_factor', 1.0) * prom_status.get('flow_multiplier', 1.0)
    god_code.append(f"DEFINE GLOBAL_RISK = {risk:.2f}x")
    god_code.append(f"")
    
    # 3. MANTIK BLOĞU (LOGIC)
    god_code.append(f"EXECUTE STRATEGY main_loop {{")
    
    # Alım Mantığı
    rsi_buy = strat.get('rsi_buy_level', 30)
    god_code.append(f"    WHEN (RSI < {rsi_buy}) AND (COOLDOWN == FALSE) THEN {{")
    god_code.append(f"        ACTION: BUY_MARKET")
    god_code.append(f"        SIZE: MAX_ALLOCATION * GLOBAL_RISK")
    god_code.append(f"    }}")
    
    # Satış Mantığı
    rsi_sell = strat.get('rsi_sell_level', 70)
    tp = strat.get('take_profit_pct', 1.0)
    sl = strat.get('stop_loss_pct', -1.0)
    
    god_code.append(f"    WHEN (PNL > {tp}%) OR (RSI > {rsi_sell}) THEN {{")
    god_code.append(f"        ACTION: TAKE_PROFIT")
    god_code.append(f"    }}")
    
    god_code.append(f"    WHEN (PNL < {sl}%) THEN {{")
    god_code.append(f"        ACTION: STOP_LOSS_EMERGENCY")
    god_code.append(f"    }}")
    
    god_code.append(f"}}")
    
    return "\n".join(god_code)

print("📜 GODLANG SCRIBE (YAZICI) BAŞLATILIYOR...")
print("-> Botun düşünceleri GODLANG diline çevriliyor.")
print(f"-> Çıktı Dosyası: {GODLANG_FILE}")
print("==============================================")

last_code = ""

while True:
    try:
        current_code = transpile_to_godlang()
        
        # Sadece kod değiştiyse ekrana bas ve dosyaya yaz
        if current_code != last_code:
            # Ekrana Bas
            os.system('cls' if os.name == 'nt' else 'clear')
            print(current_code)
            
            # Dosyaya Yaz (.god uzantılı)
            with open(GODLANG_FILE, "w") as f:
                f.write(current_code)
                
            last_code = current_code
            print(f"\n[UPDATED] Godlang script compiled successfully.")
            
    except Exception as e:
        print(f"Scribe Error: {e}")
        
    time.sleep(2)