#!/usr/bin/env python3
"""🦅🐺🦁 VOLTRAN BRIDGE - Cloud Connected"""
import os, json, math, time, redis

GEN_HOST = os.getenv("GENETICS_REDIS_HOST", "127.0.0.1")
GEN_PORT = int(os.getenv("GENETICS_REDIS_PORT", "6379"))
GEN_PASS = os.getenv("GENETICS_REDIS_PASSWORD", None)
LABS_HOST = os.getenv("LABS_REDIS_HOST", "127.0.0.1")
LABS_PORT = int(os.getenv("LABS_REDIS_PORT", "6379"))
LABS_PASS = os.getenv("LABS_REDIS_PASSWORD", None)

_cache = {"data": None, "ts": 0}

def _get_redis(host, port, password=None):
    try:
        r = redis.Redis(host=host, port=port, password=password, decode_responses=True, socket_timeout=5)
        r.ping()
        return r
    except:
        return None

def _get_score(r, meta_key, dna_key, score_fields, default_dna):
    if not r: return 50.0, 0, default_dna
    try:
        raw_meta = r.get(meta_key)
        raw_dna = r.get(dna_key)
        if not raw_meta: return 50.0, 0, default_dna
        meta = json.loads(raw_meta)
        dna = json.loads(raw_dna) if raw_dna else default_dna
        gen = meta.get("gen", 0)
        score = None
        for f in score_fields:
            if f in meta: score = meta[f]; break
        if score is None:
            profit = meta.get("best_profit", meta.get("best", 0))
            score = min(100, 50 + math.log10(profit + 1) * 10) if profit > 0 else 50
        return max(0, min(100, float(score))), gen, dna
    except:
        return 50.0, 0, default_dna

from config_center import config

def get_voltran_snapshot(force=False):
    global _cache
    now = time.time()
    if not force and _cache["data"] and (now - _cache["ts"]) < 30:
        return _cache["data"]
    
    gen_r = _get_redis(config.REDIS_GENETICS_HOST, config.REDIS_GENETICS_PORT, config.REDIS_GENETICS_PASS)
    labs_r = _get_redis(config.REDIS_HOST, config.REDIS_PORT, config.REDIS_PASS)
    
    bj, bj_gen, bj_dna = _get_score(gen_r, config.BJ_META_KEY, config.BJ_DNA_KEY,
                                      ["score", "bj_score", "best_profit"], [10,10,234,326,354,500])
    rl, rl_gen, rl_dna = _get_score(labs_r, config.RL_META_KEY, config.RL_DNA_KEY,
                                      ["score"], [50,40,30,25,20,15])
    ch, ch_gen, ch_dna = _get_score(labs_r, config.CH_META_KEY, config.CH_DNA_KEY,
                                      ["cosmic_harmony", "score"], [100,50,80,40,120,60])
    
    vs = (max(1,bj) * max(1,rl) * max(1,ch)) ** (1/3)
    vf = max(0.8, min(1.2, 0.8 + (vs - 50) * 0.008))
    
    if vs >= 90: rank = "🌟 COSMIC VOLTRAN"
    elif vs >= 80: rank = "⚡ SUPER VOLTRAN"
    elif vs >= 70: rank = "🔥 VOLTRAN PRIME"
    elif vs >= 60: rank = "💫 VOLTRAN CADET"
    elif vs >= 50: rank = "🌀 PROTO-VOLTRAN"
    else: rank = "🔮 VOLTRAN SEED"
    
    snap = {
        "blackjack_score": bj, "roulette_score": rl, "chaos_score": ch,
        "voltran_score": vs, "voltran_factor": vf, "rank": rank,
        "blackjack_gen": bj_gen, "roulette_gen": rl_gen, "chaos_gen": ch_gen,
        "blackjack_dna": bj_dna, "roulette_dna": rl_dna, "chaos_dna": ch_dna,
        "timestamp": now, "cloud_connected": gen_r is not None
    }
    _cache = {"data": snap, "ts": now}
    return snap

if __name__ == "__main__":
    snap = get_voltran_snapshot(force=True)
    status = "☁️ CLOUD" if snap.get("cloud_connected") else "💻 LOCAL"
    print(f"""
  {status} VOLTRAN STATUS
  ─────────────────────────────────
  🦅 Blackjack: {snap['blackjack_score']:.1f} (Gen {snap['blackjack_gen']})
  🐺 Roulette:  {snap['roulette_score']:.1f} (Gen {snap['roulette_gen']})
  🦁 Chaos:     {snap['chaos_score']:.1f} (Gen {snap['chaos_gen']})
  ─────────────────────────────────
  ⚡ VOLTRAN:   {snap['voltran_score']:.1f}
  📊 Factor:    {snap['voltran_factor']:.2f}x
  🏆 {snap['rank']}
""")
