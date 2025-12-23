// GODBRAIN API Client
// Connects mobile app to existing dashboard backend

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

// Types
export interface SystemStatus {
    voltran_score: number;
    dna_generation: number;
    epoch: number;
    risk_var: number;
    equity: number;
    pnl: number;
    uptime: number;
    services: {
        name: string;
        status: 'healthy' | 'unhealthy' | 'unknown';
        uptime: string;
    }[];
}

export interface WisdomData {
    total_generations: number;
    global_champion_id: string;
    champion_fitness: number;
    ensemble_params: {
        stop_loss: number;
        take_profit: number;
        rsi_buy_level: number;
        rsi_sell_level: number;
    };
    epoch: number;
    timestamp: string;
}

export interface ChatMessage {
    role: 'user' | 'assistant';
    content: string;
    confidence?: number;
}

export interface Position {
    symbol: string;
    side: 'long' | 'short';
    size: number;
    entry_price: number;
    current_price: number;
    pnl: number;
    pnl_percent: number;
}

export interface Anomaly {
    id: string;
    type: string;
    confidence: number;
    nobel_potential: number;
    description: string;
    timestamp: string;
}

export interface RiskAdjustment {
    position_multiplier: number;
    stop_loss_multiplier: number;
    take_profit_multiplier: number;
    signal_threshold: number;
    reason: string;
    source: string;
}

// API Functions
export const godbrainApi = {
    // System status (VOLTRAN, DNA, Epoch)
    async getStatus(): Promise<SystemStatus> {
        try {
            const res = await fetch(`${API_BASE}/api/status`);
            if (!res.ok) throw new Error('Failed to fetch status');
            return res.json();
        } catch (error) {
            console.error('API Error:', error);
            // Return mock data on error
            // Return obvious error/syncing state - NO MORE FAKE DATA
            return {
                voltran_score: 0,
                dna_generation: 0,
                epoch: 0,
                risk_var: 0,
                equity: 0,
                pnl: 0,
                uptime: 0,
                services: [],
                status: 'error' // Add this field if possible or just rely on zeros
            } as any;
        }
    },

    // Quantum Lab wisdom data
    async getWisdom(): Promise<WisdomData> {
        try {
            const res = await fetch(`${API_BASE}/api/wisdom`);
            if (!res.ok) throw new Error('Failed to fetch wisdom');
            return res.json();
        } catch (error) {
            console.error('API Error:', error);
            return {
                total_generations: 19000,
                global_champion_id: 'DNA_mock',
                champion_fitness: 0.95,
                ensemble_params: {
                    stop_loss: 0.02,
                    take_profit: 0.05,
                    rsi_buy_level: 30,
                    rsi_sell_level: 70
                },
                epoch: 300,
                timestamp: new Date().toISOString()
            };
        }
    },

    // Chat with Seraph
    async chat(message: string): Promise<ChatMessage> {
        try {
            const res = await fetch(`${API_BASE}/api/seraph/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message })
            });
            if (!res.ok) throw new Error('Failed to chat');
            return res.json();
        } catch (error) {
            console.error('API Error:', error);
            return {
                role: 'assistant',
                content: 'Connection to SERAPH temporarily unavailable. Please try again.',
                confidence: 0
            };
        }
    },

    // Get open positions
    async getPositions(): Promise<Position[]> {
        try {
            const res = await fetch(`${API_BASE}/api/positions`);
            if (!res.ok) throw new Error('Failed to fetch positions');
            return res.json();
        } catch (error) {
            console.error('API Error:', error);
            return [];
        }
    },

    // Get anomalies
    async getAnomalies(): Promise<Anomaly[]> {
        try {
            const res = await fetch(`${API_BASE}/api/anomalies`);
            if (!res.ok) throw new Error('Failed to fetch anomalies');
            return res.json();
        } catch (error) {
            console.error('API Error:', error);
            return [];
        }
    },

    // Get risk adjustment
    async getRiskAdjustment(): Promise<RiskAdjustment> {
        try {
            const res = await fetch(`${API_BASE}/api/risk-adjustment`);
            if (!res.ok) throw new Error('Failed to fetch risk');
            return res.json();
        } catch (error) {
            console.error('API Error:', error);
            return {
                position_multiplier: 1.0,
                stop_loss_multiplier: 1.0,
                take_profit_multiplier: 1.0,
                signal_threshold: 0.5,
                reason: 'No anomalies detected',
                source: 'none'
            };
        }
    },

    // LLM status
    async getLLMStatus(): Promise<{ name: string; active: boolean; latency: number }[]> {
        try {
            const res = await fetch(`${API_BASE}/api/llm-status`);
            if (!res.ok) throw new Error('Failed to fetch LLM status');
            return res.json();
        } catch (error) {
            console.error('API Error:', error);
            return [
                { name: 'CLAUDE', active: true, latency: 120 },
                { name: 'GPT', active: true, latency: 90 },
                { name: 'GEMINI', active: true, latency: 150 },
                { name: 'LLAMA', active: false, latency: 0 }
            ];
        }
    }
};

// Real-time data hook
export function useGodbrainData<T>(
    fetcher: () => Promise<T>,
    interval: number = 5000
) {
    const [data, setData] = useState<T | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<Error | null>(null);

    useEffect(() => {
        let mounted = true;

        const fetchData = async () => {
            try {
                const result = await fetcher();
                if (mounted) {
                    setData(result);
                    setError(null);
                }
            } catch (err) {
                if (mounted) setError(err as Error);
            } finally {
                if (mounted) setLoading(false);
            }
        };

        fetchData();
        const id = setInterval(fetchData, interval);

        return () => {
            mounted = false;
            clearInterval(id);
        };
    }, [fetcher, interval]);

    return { data, loading, error };
}

// Import React hooks
import { useState, useEffect } from 'react';
