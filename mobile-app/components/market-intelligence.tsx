"use client"

import { motion } from "framer-motion"
import { useState, useEffect } from "react"
import { godbrainApi } from "@/lib/api"

interface Ticker {
  symbol: string
  price: number
  change: number
}

interface WhaleAlert {
  id: number
  amount: string
  asset: string
  action: string
  time: string
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

  const [whaleAlerts] = useState<WhaleAlert[]>([
    { id: 1, amount: "$2.4M", asset: "BTC", action: "moved to Binance", time: "2 min ago" },
    { id: 2, amount: "$890K", asset: "ETH", action: "withdrawn from exchange", time: "8 min ago" },
    { id: 3, amount: "$1.2M", asset: "SOL", action: "Smart money accumulating", time: "15 min ago" },
  ])

  const [chartData, setChartData] = useState<number[]>([])
  const [timeframe, setTimeframe] = useState("1H")

  // Fetch real BTC price from API
  useEffect(() => {
    const fetchPrice = async () => {
      try {
        const data = await godbrainApi.getStatus()
        // Also get market data if available
        const marketRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/market`)
        const marketData = await marketRes.json()

        const btcPrice = marketData.btc_price || 88000

        setTickers(prev => [
          { symbol: "BTC", price: btcPrice, change: prev[0].change + (Math.random() - 0.5) * 0.2 },
          { symbol: "ETH", price: btcPrice * 0.035, change: prev[1].change + (Math.random() - 0.5) * 0.2 },
          { symbol: "SOL", price: btcPrice * 0.0022, change: prev[2].change + (Math.random() - 0.5) * 0.3 },
          { symbol: "DOGE", price: btcPrice * 0.0000045, change: prev[3].change + (Math.random() - 0.5) * 0.5 },
        ])

        // Update chart
        setChartData(prev => {
          if (prev.length === 0) return [...Array(50)].map(() => btcPrice + (Math.random() - 0.5) * 2000)
          return [...prev.slice(1), btcPrice + (Math.random() - 0.5) * 500]
        })
      } catch (error) {
        console.error('Market API error:', error)
      }
    }

    fetchPrice()
    const interval = setInterval(fetchPrice, 5000)
    return () => clearInterval(interval)
  }, [])

  const minPrice = chartData.length > 0 ? Math.min(...chartData) : 0
  const maxPrice = chartData.length > 0 ? Math.max(...chartData) : 1
  const priceRange = maxPrice - minPrice || 1 // Prevent division by zero

  const getYPosition = (price: number) => {
    if (!price || !isFinite(price) || priceRange === 0) return 96 // Return middle if invalid
    const normalized = (price - minPrice) / priceRange
    return 192 - normalized * 160
  }

  const lastPrice = chartData.length > 0 ? chartData[chartData.length - 1] : 100000
  const lastY = getYPosition(lastPrice)

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <motion.span
          className="text-2xl"
          animate={{ rotate: [0, 360] }}
          transition={{ duration: 4, repeat: Number.POSITIVE_INFINITY, ease: "linear" }}
        >
          📡
        </motion.span>
        <h1 className="text-lg font-bold text-white">MARKET FEED</h1>
      </div>

      {/* Price tickers */}
      <div className="flex gap-3 overflow-x-auto pb-2">
        {tickers.map((ticker) => (
          <motion.div
            key={ticker.symbol}
            className="flex-shrink-0 px-4 py-2 rounded-xl bg-white/5 border border-white/10"
            whileHover={{ scale: 1.02 }}
          >
            <div className="flex items-center gap-2">
              <span className="font-bold text-white">{ticker.symbol}</span>
              <span className="text-sm text-gray-400">
                ${ticker.price.toLocaleString("en-US", { maximumFractionDigits: ticker.price < 1 ? 4 : 0 })}
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
      <div className="relative h-48 rounded-2xl bg-black/50 border border-cyan-500/20 overflow-hidden">
        {/* Timeframe selector */}
        <div className="absolute top-2 right-2 flex gap-1 z-10">
          {["1H", "4H", "1D"].map((tf) => (
            <button
              key={tf}
              className={`px-2 py-1 rounded text-xs font-mono ${timeframe === tf ? "bg-cyan-500 text-black" : "bg-white/10 text-gray-400"
                }`}
              onClick={() => setTimeframe(tf)}
            >
              {tf}
            </button>
          ))}
        </div>

        {/* Chart - only render if we have data */}
        {chartData.length > 0 && (
          <svg className="w-full h-full" viewBox="0 0 400 192" preserveAspectRatio="none">
            <defs>
              <linearGradient id="chartGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stopColor="#00F5FF" stopOpacity="0.3" />
                <stop offset="100%" stopColor="#00F5FF" stopOpacity="0" />
              </linearGradient>
            </defs>

            {/* Area fill */}
            <path
              d={`
                M 0 ${getYPosition(chartData[0])}
                ${chartData.map((p, i) => `L ${(i / (chartData.length - 1)) * 400} ${getYPosition(p)}`).join(" ")}
                L 400 192 L 0 192 Z
              `}
              fill="url(#chartGradient)"
            />

            {/* Line */}
            <motion.path
              d={`M ${chartData.map((p, i) => `${(i / (chartData.length - 1)) * 400} ${getYPosition(p)}`).join(" L ")}`}
              fill="none"
              stroke="#00F5FF"
              strokeWidth="2"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ duration: 1 }}
            />

            {/* Glow effect on last point - with safe cy value */}
            <motion.circle
              cx={400}
              cy={lastY}
              r="4"
              fill="#00F5FF"
              animate={{
                r: [4, 8, 4],
                opacity: [1, 0.5, 1],
              }}
              transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY }}
            />
          </svg>
        )}

        {/* Price label */}
        <div className="absolute top-2 left-2 text-xs text-gray-400 font-mono">
          BTC/USDT{" "}
          <span className="text-white">${lastPrice.toLocaleString("en-US", { maximumFractionDigits: 0 })}</span>
        </div>
      </div>

      {/* Signal strength bars */}
      <div className="space-y-3">
        <div className="text-xs text-gray-400 font-mono uppercase">Signal Strength</div>
        {[
          { label: "TECHNICAL", value: signals.technical, color: "cyan" },
          { label: "SENTIMENT", value: signals.sentiment, color: "purple" },
          { label: "ON-CHAIN", value: signals.onChain, color: "emerald", alert: signals.onChain > 85 },
          { label: "ORDER FLOW", value: signals.orderFlow, color: "amber" },
          { label: "PHYSICS DNA", value: signals.physicsDna, color: "cyan" },
        ].map((signal) => (
          <div key={signal.label} className="flex items-center gap-3">
            <div className="w-24 text-xs text-gray-400 font-mono">{signal.label}</div>
            <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden">
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
            <div className="w-12 text-xs text-right font-mono text-white">{signal.value.toFixed(0)}%</div>
            {signal.alert && <span className="text-xs text-emerald-400">↑ WHALE</span>}
          </div>
        ))}
      </div>

      {/* Whale activity feed */}
      <div className="space-y-2">
        <div className="text-xs text-gray-400 font-mono uppercase">Whale Activity</div>
        {whaleAlerts.map((alert, i) => (
          <motion.div
            key={alert.id}
            className="flex items-center gap-3 p-3 rounded-xl bg-white/5 border border-white/10"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.1 }}
          >
            <span className="text-xl">🐋</span>
            <div className="flex-1">
              <span className="text-white font-medium">
                {alert.amount} {alert.asset}
              </span>
              <span className="text-gray-400 text-sm"> {alert.action}</span>
            </div>
            <span className="text-xs text-gray-500">{alert.time}</span>
          </motion.div>
        ))}
      </div>
    </div>
  )
}
