# GODBRAIN QUANTUM - System Overview

## What is GODBRAIN?
An autonomous AI-powered quantitative trading system that evolves trading strategies using genetic algorithms, quantum computing, and multi-LLM orchestration.

---

## Architecture Overview (v5.0 Simplified)

```
┌─────────────────────────────────────────────────────────────────┐
│                    GODBRAIN.ORG (Cloudflare)                    │
│         godbrain.org │ app.godbrain.org │ api.godbrain.org      │
└─────────────────────────────────────────────────────────────────┘
                              │
                    Cloudflare Tunnel
                              │
┌─────────────────────────────────────────────────────────────────┐
│                      Hybrid Execution Environment                │
├────────────────┬────────────────┬────────────────┬──────────────┤
│   VOLTRAN 5.0  │   Genetics Lab │   Dashboard    │    Redis     │
│   (Modular)    │   (BJ/RL/CH)   │  + Seraph AI   │  (Namespaced)│
└────────────────┴────────────────┴────────────────┴──────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                     Active Evolution Core                       │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   Harvester     │   Executor      │     Health Check            │
│  (Aggregator)   │   (Actions)     │     (:8080/health)          │
└─────────────────┴─────────────────┴─────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                    Archived / Dormant Layer                      │
├────────────────┬────────────────┬────────────────┬──────────────┤
│  Quantum Lab   │    Neural      │ DNA Pusher     │   Anomaly    │
│  (Mothballed)  │ (Mothballed)   │ (Deprecated)   │  (Passive)   │
└────────────────┴────────────────┴────────────────┴──────────────┘
```

---

## Technology Stack

| Category | Technologies |
|----------|-------------|
| **Execution Core** | Python 3.11, CCXT, aiohttp (Health) |
| **Configuration** | Centralized `config_center.py`, `.env` |
| **Observability** | `/health` API, Sentinel Monitoring |
| **Logic Layer** | Blackjack (Edge), Roulette (Risk), Chaos (Entropy) |
| **AI Layer** | Seraph AI (Multi-LLM Router), Edge AI (Enrichment) |

---

## Simplified Services (Optimized for Stability)

| Service | Purpose | Port | Status |
|---------|---------|------|--------|
| `voltran-agg` | Modular Trading Orchestrator | 8080 | **ACTIVE** |
| `genetics-labs` | Unified Evolution Engine (BJ/RL/CH) | - | **ACTIVE** |
| `redis` | Namespaced Data Store (`genetics:*`, etc) | 16379 | **ACTIVE** |
| `dashboard` | Web UI + Seraph AI | 8000 | **ACTIVE** |
| `mobile-api` | Mobile REST API | 8001 | **ACTIVE** |
| `neural-*` | LSTM/Transformer Training | - | *ARCHIVED* |
| `quantum-*` | Multiverse Simulations | - | *ARCHIVED* |

---

## Key Modules (Modular v5.0)

### 1. The Orchestrator (`agg.py`)
Lean coordinator (~90 lines). Uses `harvester` for signals and `executor` for actions.

### 2. Signal Harvester (`signals/harvester.py`)
One-stop shop for all market and genetic signals. Fail-safe by design.

### 3. Execution Engine (`execution/executor.py`)
Handles OKX interactions, position sizing, and "YA HERRO YA MERRO" aggressive scaling.

### 4. Config Center (`config_center.py`)
Single source of truth for all system parameters and Redis namespaces.

### 5. Seraph AI (`seraph/`)
Multi-LLM AI assistant. Now integrates with the simplified telemetry.

---

## Last 3 Days Development (Dec 18-20, 2025)

### Day 1: Multi-LLM Architecture
- Implemented LLM Router for Claude/GPT/Gemini
- Added provider failover
- Integrated into Seraph AI

### Day 2: Mobile App Integration
- Created mobile_api.py REST API
- Updated Next.js components for real data
- Fixed hydration errors
- Connected to Redis for live metrics

### Day 3: Domain & Permanent Deployment
- Purchased godbrain.org domain
- Set up Cloudflare Tunnel (named tunnel)
- Dockerized mobile API
- Created startup scripts
- Git pushed all changes

---

## Live Endpoints

| URL | Returns |
|-----|---------|
| `https://godbrain.org` | Mobile App UI |
| `https://api.godbrain.org/api/status` | System metrics (voltran, DNA gen) |
| `https://api.godbrain.org/api/market` | BTC price from Redis |
| `https://api.godbrain.org/api/seraph/chat` | AI chat endpoint |
| `https://api.godbrain.org/api/llm-status` | LLM provider status |

---

## Key Files

```
godbrain-quantum/
├── mobile_api.py          # REST API for mobile
├── core/agg.py            # VOLTRAN aggregator
├── seraph/
│   ├── seraph.py          # AI assistant
│   └── llm_router.py      # Multi-LLM routing
├── quantum_lab/           # DNA evolution
├── quantum_genesis/       # IBM Quantum
├── anomaly_hunter/        # Anomaly detection
├── mobile-app/            # Next.js frontend
│   ├── lib/api.ts         # API client
│   └── components/        # React components
└── docker-compose.yml     # All services
```

---

## Current State (Dec 20, 2025)
- **DNA Generation**: 5660+
- **VOLTRAN Score**: 85.0
- **Docker Services**: 12 running
- **Uptime**: 47+ hours
- **Domain**: godbrain.org (Cloudflare)

---

## Quick Start for New LLMs

1. **Redis is the brain** - All data flows through Redis
2. **VOLTRAN is the heart** - Aggregates all signals
3. **DNA evolves** - Strategies improve over generations
4. **Seraph speaks** - AI explains everything
5. **Quantum enhances** - IBM Quantum for optimization

**Key command to check status:**
```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
```
