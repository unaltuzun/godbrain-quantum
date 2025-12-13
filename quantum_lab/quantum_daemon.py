#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QUANTUM RESONANCE LAB DAEMON
Sürekli multiverse simülasyonu ve genom evrimi
"""

import sys
import time
import json
import random
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/mnt/c/godbrain-quantum')

# Paths
ROOT = Path("/mnt/c/godbrain-quantum")
UNIVERSE_DIR = ROOT / "quantum_lab" / "universes"
WISDOM_DIR = ROOT / "quantum_lab" / "wisdom"
CONVERGENCE_DIR = ROOT / "quantum_lab" / "convergence"
LOG_FILE = ROOT / "logs" / "quantum_lab.log"

# Ensure dirs exist
UNIVERSE_DIR.mkdir(parents=True, exist_ok=True)
WISDOM_DIR.mkdir(parents=True, exist_ok=True)
CONVERGENCE_DIR.mkdir(parents=True, exist_ok=True)

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[QUANTUM] {timestamp} | {msg}")
    with open(LOG_FILE, 'a') as f:
        f.write(f"{timestamp} | {msg}\n")

class UniverseSimulator:
    """Tek bir evren simülasyonu"""
    
    def __init__(self, universe_id: int, regime: str):
        self.universe_id = universe_id
        self.regime = regime
        self.genomes = []
        self.generation = 0
        self.best_fitness = 0
        self.champion = None
        
    def create_genome(self) -> dict:
        """Rastgele genom oluştur"""
        return {
            "id": f"g{random.randint(10000, 99999)}",
            "stop_loss_pct": random.uniform(-5, -0.1),
            "take_profit_pct": random.uniform(1, 20),
            "rsi_buy_level": random.uniform(10, 40),
            "rsi_sell_level": random.uniform(60, 90),
            "position_size_factor": random.uniform(0.1, 1.0),
            "fitness": 0,
            "generation": self.generation
        }
    
    def evaluate_fitness(self, genome: dict) -> float:
        """
        Fitness hesapla - regime'e göre farklı metrikler
        Gerçek backtest yerine heuristic kullanıyoruz (hızlı simülasyon için)
        """
        # Base fitness
        fitness = 50
        
        # Stop loss kalitesi (-2% ideal)
        sl = genome["stop_loss_pct"]
        sl_score = 100 - abs(sl + 2) * 20
        fitness += sl_score * 0.2
        
        # Take profit kalitesi (5-10% ideal)
        tp = genome["take_profit_pct"]
        tp_score = 100 - abs(tp - 7.5) * 5
        fitness += tp_score * 0.2
        
        # RSI seviyeleri (30/70 ideal)
        rsi_buy = genome["rsi_buy_level"]
        rsi_sell = genome["rsi_sell_level"]
        rsi_score = 100 - (abs(rsi_buy - 30) + abs(rsi_sell - 70)) * 2
        fitness += rsi_score * 0.2
        
        # Position size (regime'e göre)
        size = genome["position_size_factor"]
        if self.regime in ["BULL", "EUPHORIA"]:
            size_score = size * 100  # Agresif iyi
        elif self.regime in ["BEAR", "CRASH"]:
            size_score = (1 - size) * 100  # Muhafazakar iyi
        else:
            size_score = 100 - abs(size - 0.5) * 100  # Orta iyi
        fitness += size_score * 0.2
        
        # Risk/reward oranı
        if sl != 0:
            rr_ratio = abs(tp / sl)
            rr_score = min(100, rr_ratio * 20)
            fitness += rr_score * 0.2
        
        # Random noise (piyasa belirsizliği)
        fitness += random.uniform(-10, 10)
        
        return max(0, min(100, fitness))
    
    def evolve_generation(self, population_size: int = 20):
        """Bir jenerasyon evrimleştir"""
        self.generation += 1
        
        # İlk jenerasyon
        if not self.genomes:
            self.genomes = [self.create_genome() for _ in range(population_size)]
        
        # Fitness hesapla
        for g in self.genomes:
            g["fitness"] = self.evaluate_fitness(g)
        
        # Sırala
        self.genomes.sort(key=lambda x: x["fitness"], reverse=True)
        
        # En iyi
        self.champion = self.genomes[0]
        self.best_fitness = self.champion["fitness"]
        
        # Seçilim - en iyi %50
        survivors = self.genomes[:population_size // 2]
        
        # Crossover ve mutasyon
        new_genomes = []
        while len(new_genomes) < population_size - len(survivors):
            parent1 = random.choice(survivors)
            parent2 = random.choice(survivors)
            
            # Crossover
            child = {
                "id": f"g{random.randint(10000, 99999)}",
                "stop_loss_pct": random.choice([parent1["stop_loss_pct"], parent2["stop_loss_pct"]]),
                "take_profit_pct": random.choice([parent1["take_profit_pct"], parent2["take_profit_pct"]]),
                "rsi_buy_level": random.choice([parent1["rsi_buy_level"], parent2["rsi_buy_level"]]),
                "rsi_sell_level": random.choice([parent1["rsi_sell_level"], parent2["rsi_sell_level"]]),
                "position_size_factor": (parent1["position_size_factor"] + parent2["position_size_factor"]) / 2,
                "fitness": 0,
                "generation": self.generation
            }
            
            # Mutasyon (%20 şans)
            if random.random() < 0.2:
                mutation_key = random.choice(["stop_loss_pct", "take_profit_pct", "rsi_buy_level", "rsi_sell_level", "position_size_factor"])
                if mutation_key == "stop_loss_pct":
                    child[mutation_key] += random.uniform(-0.5, 0.5)
                elif mutation_key == "take_profit_pct":
                    child[mutation_key] += random.uniform(-2, 2)
                elif mutation_key in ["rsi_buy_level", "rsi_sell_level"]:
                    child[mutation_key] += random.uniform(-5, 5)
                else:
                    child[mutation_key] += random.uniform(-0.1, 0.1)
                child[mutation_key] = max(0.01, child[mutation_key])
            
            new_genomes.append(child)
        
        self.genomes = survivors + new_genomes
        
        return self.champion


class MultiverseEngine:
    """Çoklu evren simülasyon motoru"""
    
    def __init__(self):
        self.universes = {}
        self.regimes = ["BULL", "BEAR", "NEUTRAL", "CRASH", "EUPHORIA", "SIDEWAYS"]
        self.global_wisdom = []
        self.total_generations = 0
        
    def create_multiverse(self, num_universes: int = 6):
        """Paralel evrenler oluştur"""
        for i, regime in enumerate(self.regimes[:num_universes]):
            universe_id = 100000 + i
            self.universes[universe_id] = UniverseSimulator(universe_id, regime)
            log(f"🌌 Universe-{universe_id} created: {regime}")
    
    def run_epoch(self) -> dict:
        """Bir epoch çalıştır - tüm evrenlerde bir jenerasyon"""
        epoch_results = {}
        
        for uid, universe in self.universes.items():
            champion = universe.evolve_generation()
            epoch_results[uid] = {
                "regime": universe.regime,
                "generation": universe.generation,
                "champion_id": champion["id"],
                "fitness": champion["fitness"],
                "params": {
                    "sl": champion["stop_loss_pct"],
                    "tp": champion["take_profit_pct"],
                    "rsi_buy": champion["rsi_buy_level"],
                    "rsi_sell": champion["rsi_sell_level"],
                    "size": champion["position_size_factor"]
                }
            }
        
        self.total_generations += 1
        return epoch_results
    
    def extract_wisdom(self) -> dict:
        """Tüm evrenlerden bilgelik çıkar"""
        # En iyi genomları topla
        all_champions = []
        for uid, universe in self.universes.items():
            if universe.champion:
                all_champions.append({
                    "universe": uid,
                    "regime": universe.regime,
                    **universe.champion
                })
        
        if not all_champions:
            return None
        
        # Global en iyi
        global_best = max(all_champions, key=lambda x: x["fitness"])
        
        # Ortalama parametreler (ensemble)
        avg_params = {
            "stop_loss_pct": sum(c["stop_loss_pct"] for c in all_champions) / len(all_champions),
            "take_profit_pct": sum(c["take_profit_pct"] for c in all_champions) / len(all_champions),
            "rsi_buy_level": sum(c["rsi_buy_level"] for c in all_champions) / len(all_champions),
            "rsi_sell_level": sum(c["rsi_sell_level"] for c in all_champions) / len(all_champions),
            "position_size_factor": sum(c["position_size_factor"] for c in all_champions) / len(all_champions),
        }
        
        wisdom = {
            "timestamp": datetime.now().isoformat(),
            "total_generations": self.total_generations,
            "global_champion": global_best,
            "ensemble_params": avg_params,
            "regime_champions": {c["regime"]: c for c in all_champions}
        }
        
        # Kaydet
        wisdom_file = WISDOM_DIR / f"wisdom_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(wisdom_file, 'w') as f:
            json.dump(wisdom, f, indent=2)
        
        # Latest wisdom
        with open(WISDOM_DIR / "latest_wisdom.json", 'w') as f:
            json.dump(wisdom, f, indent=2)
        
        return wisdom
    
    def apply_wisdom_to_live(self, wisdom: dict):
        """Bilgeliği canlı sisteme uygula"""
        try:
            # Active genome'u güncelle
            active_genome = {
                "timestamp": datetime.now().isoformat(),
                "params": {
                    "stop_loss_pct": wisdom["ensemble_params"]["stop_loss_pct"],
                    "take_profit_pct": wisdom["ensemble_params"]["take_profit_pct"],
                    "rsi_buy_level": wisdom["ensemble_params"]["rsi_buy_level"],
                    "rsi_sell_level": wisdom["ensemble_params"]["rsi_sell_level"],
                    "position_size_factor": wisdom["ensemble_params"]["position_size_factor"]
                },
                "generation": self.total_generations,
                "source": "QUANTUM_MULTIVERSE",
                "champion_id": wisdom["global_champion"]["id"],
                "champion_fitness": wisdom["global_champion"]["fitness"]
            }
            
            with open(ROOT / "logs" / "active_genome.json", 'w') as f:
                json.dump(active_genome, f, indent=2)
            
            log(f"🧬 Wisdom applied to live system: {wisdom['global_champion']['id']} (fitness: {wisdom['global_champion']['fitness']:.1f})")
            
        except Exception as e:
            log(f"❌ Failed to apply wisdom: {e}")


def main():
    print("=" * 70)
    print("  🌌 QUANTUM RESONANCE LAB DAEMON")
    print("  Multiverse Evolution Engine")
    print("=" * 70)
    
    engine = MultiverseEngine()
    engine.create_multiverse(6)
    
    epoch = 0
    wisdom_interval = 10  # Her 10 epoch'ta wisdom çıkar
    
    while True:
        try:
            epoch += 1
            log(f"═══ EPOCH {epoch} ═══")
            
            # Epoch çalıştır
            results = engine.run_epoch()
            
            # Sonuçları logla
            for uid, res in results.items():
                log(f"  Universe-{uid} ({res['regime']}): Gen {res['generation']} | Champion: {res['champion_id']} | Fitness: {res['fitness']:.1f}")
            
            # Wisdom çıkar ve uygula
            if epoch % wisdom_interval == 0:
                log("📚 Extracting multiverse wisdom...")
                wisdom = engine.extract_wisdom()
                if wisdom:
                    log(f"  Global Champion: {wisdom['global_champion']['id']} from {wisdom['global_champion']['regime']}")
                    log(f"  Fitness: {wisdom['global_champion']['fitness']:.1f}")
                    log(f"  Ensemble SL: {wisdom['ensemble_params']['stop_loss_pct']:.2f}% | TP: {wisdom['ensemble_params']['take_profit_pct']:.2f}%")
                    
                    # Canlı sisteme uygula
                    engine.apply_wisdom_to_live(wisdom)
            
            # Sonraki epoch için bekle
            time.sleep(30)  # 30 saniye aralıkla evrim
            
        except KeyboardInterrupt:
            log("Quantum Lab stopped by user")
            break
        except Exception as e:
            log(f"❌ Error: {e}")
            time.sleep(60)


if __name__ == "__main__":
    main()
