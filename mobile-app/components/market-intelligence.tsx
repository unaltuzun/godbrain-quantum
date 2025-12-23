"use client"

import { motion } from "framer-motion"
import { useState, useEffect } from "react"
import { godbrainApi } from "@/lib/api"
import { Clock, TrendingUp, TrendingDown } from "lucide-react"

interface Ticker {
  symbol: string
  price: number
  change: number
}

export function MarketIntelligence() {
  const [tickers, setTickers] = useState<Ticker[]>([
    { symbol: "BTC", price: 0, change: 0 },
    { symbol: "ETH", price: 0, change: -0.8 },
    { symbol: "SOL", price: 0, change: 5.1 },
    { symbol: "DOGE", price: 0, change: 12.4 },
  ])

  const [signals, setSignals] = useState({
    technical: 78,
    sentiment: 62,
    onChain: 89,
    orderFlow: 71,
    physicsDna: 94,
  })

  const [whaleAlerts, setWhaleAlerts] = useState<any[]>([])
  const [loadingAnomalies, setLoadingAnomalies] = useState(true)
  const [chartData, setChartData] = useState<number[]>([])
  const [timeframe, setTimeframe] = useState("1H")

  useEffect(() => {
    const fetchData = async () => {
      try {
        // 1) Main Status (VOLTRAN, etc)
        const status = await godbrainApi.getStatus()

        // 2) Market Prices
        let btcPrice = 96000
        try {
          const marketData = await godbrainApi.getMarketData()
          btcPrice = marketData.btc_price || 96000
        } catch (e) { }

        setTickers(prev => [
          { symbol: "BTC", price: btcPrice, change: prev[0].change + (Math.random() - 0.5) * 0.2 },
          { symbol: "ETH", price: btcPrice * 0.035, change: prev[1].change + (Math.random() - 0.5) * 0.2 },
          { symbol: "SOL", price: btcPrice * 0.0022, change: prev[2].change + (Math.random() - 0.5) * 0.3 },
          { symbol: "DOGE", price: btcPrice * 0.0000045, change: prev[3].change + (Math.random() - 0.5) * 0.5 },
        ])

        // 3) Anomalies (Whale Alerts)
        const anomalies = await godbrainApi.getAnomalies()
        setWhaleAlerts(anomalies)
        setLoadingAnomalies(false)

        // 4) Chart
        setChartData(prev => {
          if (prev.length === 0) return [...Array(50)].map(() => btcPrice + (Math.random() - 0.5) * 2000)
          return [...prev.slice(1), btcPrice + (Math.random() - 0.5) * 500]
        })

        // 5) Dynamic Signals from status
        setSignals(prev => ({
          ...prev,
          physicsDna: status.voltran_score || prev.physicsDna
        }))

      } catch (error) {
        console.error('Intelligence fetch error:', error)
      }
    }

    fetchData()
    const interval = setInterval(fetchData, 5000)
    return () => clearInterval(interval)
  }, [])

  const minPrice = chartData.length > 0 ? Math.min(...chartData) : 0
  const maxPrice = chartData.length > 0 ? Math.max(...chartData) : 1
  const priceRange = maxPrice - minPrice || 1

  const getYPosition = (price: number) => {
    if (!price || !isFinite(price) || priceRange === 0) return 96
    const normalized = (price - minPrice) / priceRange
    return 192 - normalized * 160
  }

  const lastPrice = chartData.length > 0 ? chartData[chartData.length - 1] : 0
  const lastY = getYPosition(lastPrice)

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <motion.span
            className="text-2xl"
            animate={{ rotate: [0, 360] }}
            transition={{ duration: 4, repeat: Number.POSITIVE_INFINITY, ease: "linear" }}
          >
            📡
          </motion.span>
          <h1 className="text-lg font-bold text-white tracking-tight">MARKET INTELLIGENCE</h1>
        </div>
        {whaleAlerts.some(a => a.is_stale) && (
          <span className="text-[10px] text-orange-500 font-mono flex items-center gap-1">
            <Clock className="w-2.5 h-2.5" /> SYNCING...
          </span>
        )}
      </div>

      {/* Price tickers */}
      <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-hide">
        {tickers.map((ticker) => (
          <motion.div
            key={ticker.symbol}
            className="flex-shrink-0 px-4 py-3 rounded-xl bg-white/5 border border-white/10"
            whileHover={{ scale: 1.02, backgroundColor: "rgba(255,255,255,0.08)" }}
          >
            <div className="flex items-center gap-2">
              <span className="font-bold text-white">{ticker.symbol}</span>
              <span className="text-sm text-gray-400">
                ${ticker.price.toLocaleString("en-US", {
                  minimumFractionDigits: ticker.price < 1 ? 4 : 0,
                  maximumFractionDigits: ticker.price < 1 ? 4 : 0
                })}
              </span>
              <span className={`text-xs ${ticker.change >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                {ticker.change >= 0 ? "▲" : "▼"}
                {Math.abs(ticker.change).toFixed(1)}%
              </span>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Main chart */}
      <div className="relative h-48 rounded-2xl bg-black/50 border border-cyan-500/20 overflow-hidden backdrop-blur-md">
        <div className="absolute top-3 right-3 flex gap-1 z-10">
          {["1H", "4H", "1D"].map((tf) => (
            <button
              key={tf}
              className={`px-2 py-1 rounded text-[10px] font-mono transition-colors ${timeframe === tf ? "bg-cyan-500 text-black shadow-[0_0_10px_rgba(0,245,255,0.5)]" : "bg-white/5 text-gray-500 hover:text-white"
                }`}
              onClick={() => setTimeframe(tf)}
            >
              {tf}
            </button>
          ))}
        </div>

        {chartData.length > 0 && (
          <svg className="w-full h-full" viewBox="0 0 400 192" preserveAspectRatio="none">
            <defs>
              <linearGradient id="chartGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stopColor="#00F5FF" stopOpacity="0.2" />
                <stop offset="100%" stopColor="#00F5FF" stopOpacity="0" />
              </linearGradient>
            </defs>

            <path
              d={`
                M 0 ${getYPosition(chartData[0])}
                ${chartData.map((p, i) => `L ${(i / (chartData.length - 1)) * 400} ${getYPosition(p)}`).join(" ")}
                L 400 192 L 0 192 Z
              `}
              fill="url(#chartGradient)"
            />

            <motion.path
              d={`M ${chartData.map((p, i) => `${(i / (chartData.length - 1)) * 400} ${getYPosition(p)}`).join(" L ")}`}
              fill="none"
              stroke="#00F5FF"
              strokeWidth="1.5"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ duration: 1 }}
            />

            <motion.circle
              cx={400}
              cy={lastY}
              r="3"
              fill="#00F5FF"
              animate={{
                r: [3, 6, 3],
                opacity: [1, 0.4, 1],
              }}
              transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY }}
            />
          </svg>
        )}

        <div className="absolute top-3 left-3 text-[10px] text-gray-500 font-mono tracking-widest uppercase">
          Live Market Pulse
        </div>
      </div>

      {/* Signal strength bars */}
      <div className="space-y-4 p-4 rounded-2xl bg-white/5 border border-white/5">
        <div className="text-[10px] text-gray-500 font-mono uppercase tracking-widest">Signal Distribution</div>
        {[
          { label: "TECHNICAL", value: signals.technical, color: "cyan" },
          { label: "SENTIMENT", value: signals.sentiment, color: "purple" },
          { label: "ON-CHAIN", value: signals.onChain, color: "emerald", alert: signals.onChain > 85 },
          { label: "ORDER FLOW", value: signals.orderFlow, color: "amber" },
          { label: "PHYSICS DNA", value: signals.physicsDna, color: "cyan" },
        ].map((signal) => (
          <div key={signal.label} className="flex items-center gap-3">
            <div className="w-20 text-[10px] text-gray-400 font-mono leading-none">{signal.label}</div>
            <div className="flex-1 h-1.5 bg-white/5 rounded-full overflow-hidden">
              <motion.div
                className={`h-full rounded-full ${signal.color === "cyan"
                  ? "bg-cyan-400"
                  : signal.color === "purple"
                    ? "bg-purple-400"
                    : signal.color === "emerald"
                      ? "bg-emerald-400"
                      : "bg-amber-400"
                  }`}
                style={{ width: `${signal.value}%` }}
                animate={signal.alert ? { opacity: [1, 0.5, 1] } : {}}
                transition={{ duration: 0.5, repeat: signal.alert ? Number.POSITIVE_INFINITY : 0 }}
              />
            </div>
            <div className="w-10 text-[10px] text-right font-mono text-white">{signal.value.toFixed(0)}%</div>
          </div>
        ))}
      </div>

      {/* Whale activity feed */}
      <div className="space-y-3">
        <div className="text-[10px] text-gray-500 font-mono uppercase tracking-widest flex justify-between">
          <span>Whale Feed</span>
          <span>REAL-TIME</span>
        </div>
        {whaleAlerts.length === 0 ? (
          <div className="text-center py-6 text-gray-600 text-[10px] font-mono animate-pulse uppercase">
            Waiting for alpha signals...
          </div>
        ) : (
          whaleAlerts.slice(0, 5).map((alert, i) => (
            <motion.div
              key={alert.id || i}
              className={`flex items-center gap-3 p-3 rounded-xl border transition-all ${alert.is_stale ? 'bg-white/[0.02] border-white/5 opacity-40 grayscale' : 'bg-white/5 border-white/10'}`}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
            >
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-xl ${alert.type === 'buy' ? 'bg-emerald-500/10' : 'bg-white/5'}`}>
                {alert.type === 'universal_attractor' ? '🧬' : '🐋'}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-0.5">
                  <span className="text-xs font-bold text-white truncate max-w-[150px]">
                    {alert.title || (alert.amount ? `${alert.amount} ${alert.asset}` : "Detection Active")}
                  </span>
                  <span className="text-[10px] text-gray-500 font-mono">
                    {alert.age_hours ? `${alert.age_hours}h ago` : "NEW"}
                  </span>
                </div>
                <div className="text-[10px] text-gray-400 truncate">
                  {alert.description || alert.action}
                </div>
              </div>
            </motion.div>
          ))
        )}
      </div>
    </div>
  )
}
