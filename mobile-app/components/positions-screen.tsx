"use client"

import { motion } from "framer-motion"
import { useState, useEffect } from "react"

interface Position {
  symbol: string
  side: "LONG" | "SHORT"
  leverage: number
  entry: number
  current: number
  pnl: number
  tp: number
  sl: number
}

export function PositionsScreen() {
  const [positions, setPositions] = useState<Position[]>([
    { symbol: "BTC/USDT", side: "LONG", leverage: 10, entry: 102450, current: 104231, pnl: 892, tp: 108000, sl: 99500 },
    { symbol: "ETH/USDT", side: "LONG", leverage: 5, entry: 3780, current: 3842, pnl: 164, tp: 4000, sl: 3600 },
    { symbol: "SOL/USDT", side: "SHORT", leverage: 3, entry: 205, current: 198, pnl: 102, tp: 185, sl: 220 },
  ])

  const [portfolio] = useState({
    total: 12847,
    btc: 42,
    eth: 31,
    sol: 18,
    usdt: 9,
  })

  const [orderAmount, setOrderAmount] = useState(25)
  const [leverage, setLeverage] = useState(10)

  // Animate positions
  useEffect(() => {
    const interval = setInterval(() => {
      setPositions((prev) =>
        prev.map((p) => ({
          ...p,
          current: p.current * (1 + (Math.random() - 0.5) * 0.002),
          pnl: p.pnl + (Math.random() - 0.5) * 20,
        })),
      )
    }, 3000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <motion.span
          className="text-2xl"
          animate={{ scale: [1, 1.1, 1] }}
          transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY }}
        >
          ⚡
        </motion.span>
        <h1 className="text-lg font-bold text-white">COMMAND CENTER</h1>
      </div>

      {/* Portfolio donut */}
      <div className="relative h-48 flex items-center justify-center">
        <motion.svg viewBox="0 0 100 100" className="w-40 h-40">
          <defs>
            <filter id="glow">
              <feGaussianBlur stdDeviation="2" result="coloredBlur" />
              <feMerge>
                <feMergeNode in="coloredBlur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Background circle */}
          <circle cx="50" cy="50" r="40" fill="none" stroke="#1a1a2e" strokeWidth="8" />

          {/* BTC segment */}
          <motion.circle
            cx="50"
            cy="50"
            r="40"
            fill="none"
            stroke="#F7931A"
            strokeWidth="8"
            strokeDasharray={`${portfolio.btc * 2.51} 251`}
            strokeDashoffset="0"
            transform="rotate(-90 50 50)"
            filter="url(#glow)"
            initial={{ strokeDasharray: "0 251" }}
            animate={{ strokeDasharray: `${portfolio.btc * 2.51} 251` }}
            transition={{ duration: 1 }}
          />

          {/* ETH segment */}
          <motion.circle
            cx="50"
            cy="50"
            r="40"
            fill="none"
            stroke="#627EEA"
            strokeWidth="8"
            strokeDasharray={`${portfolio.eth * 2.51} 251`}
            strokeDashoffset={`${-portfolio.btc * 2.51}`}
            transform="rotate(-90 50 50)"
            filter="url(#glow)"
          />

          {/* SOL segment */}
          <motion.circle
            cx="50"
            cy="50"
            r="40"
            fill="none"
            stroke="#00FFA3"
            strokeWidth="8"
            strokeDasharray={`${portfolio.sol * 2.51} 251`}
            strokeDashoffset={`${-(portfolio.btc + portfolio.eth) * 2.51}`}
            transform="rotate(-90 50 50)"
            filter="url(#glow)"
          />

          {/* Center text */}
          <text x="50" y="46" textAnchor="middle" fill="white" fontSize="8" fontWeight="bold">
            ${portfolio.total.toLocaleString()}
          </text>
          <text x="50" y="56" textAnchor="middle" fill="#9ca3af" fontSize="4">
            Total Value
          </text>
        </motion.svg>

        {/* Legend */}
        <div className="absolute right-4 top-1/2 -translate-y-1/2 space-y-2">
          {[
            { label: "BTC", value: portfolio.btc, color: "#F7931A" },
            { label: "ETH", value: portfolio.eth, color: "#627EEA" },
            { label: "SOL", value: portfolio.sol, color: "#00FFA3" },
            { label: "USDT", value: portfolio.usdt, color: "#26A17B" },
          ].map((item) => (
            <div key={item.label} className="flex items-center gap-2 text-xs">
              <div className="w-2 h-2 rounded-full" style={{ backgroundColor: item.color }} />
              <span className="text-gray-400">{item.label}</span>
              <span className="text-white">{item.value}%</span>
            </div>
          ))}
        </div>
      </div>

      {/* Active positions */}
      <div className="space-y-3">
        <div className="text-xs text-gray-400 font-mono uppercase">Active Positions</div>
        {positions.map((pos, i) => (
          <motion.div
            key={pos.symbol}
            className={`p-4 rounded-2xl border ${pos.pnl >= 0 ? "bg-emerald-500/5 border-emerald-500/20" : "bg-red-500/5 border-red-500/20"}`}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            whileHover={{ scale: 1.01 }}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className="font-bold text-white">{pos.symbol}</span>
                <span
                  className={`px-2 py-0.5 rounded text-xs font-mono ${pos.side === "LONG" ? "bg-emerald-500/20 text-emerald-400" : "bg-red-500/20 text-red-400"}`}
                >
                  {pos.side} {pos.leverage}x
                </span>
              </div>
              <motion.div
                className={`text-lg font-bold ${pos.pnl >= 0 ? "text-emerald-400" : "text-red-400"}`}
                animate={{ scale: [1, 1.05, 1] }}
                transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY }}
              >
                {pos.pnl >= 0 ? "+" : ""}${pos.pnl.toFixed(0)}
              </motion.div>
            </div>

            <div className="grid grid-cols-2 gap-4 text-xs mb-3">
              <div>
                <span className="text-gray-500">Entry:</span>
                <span className="text-white ml-2">${pos.entry.toLocaleString()}</span>
              </div>
              <div>
                <span className="text-gray-500">Current:</span>
                <span className="text-white ml-2">${pos.current.toLocaleString()}</span>
              </div>
              <div>
                <span className="text-gray-500">TP:</span>
                <span className="text-emerald-400 ml-2">${pos.tp.toLocaleString()}</span>
              </div>
              <div>
                <span className="text-gray-500">SL:</span>
                <span className="text-red-400 ml-2">${pos.sl.toLocaleString()}</span>
              </div>
            </div>

            {/* Progress to TP */}
            <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-gradient-to-r from-cyan-500 to-emerald-500 rounded-full"
                style={{ width: `${Math.min(100, ((pos.current - pos.entry) / (pos.tp - pos.entry)) * 100)}%` }}
              />
            </div>

            {/* Quick actions */}
            <div className="flex gap-2 mt-3">
              <button className="flex-1 py-2 rounded-lg bg-white/5 text-xs text-gray-400 font-mono">Adjust</button>
              <button className="flex-1 py-2 rounded-lg bg-white/5 text-xs text-gray-400 font-mono">Close 50%</button>
              <button className="flex-1 py-2 rounded-lg bg-red-500/20 text-xs text-red-400 font-mono">Close All</button>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Quick trade panel */}
      <motion.div
        className="p-4 rounded-2xl bg-white/5 border border-cyan-500/20"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="text-xs text-gray-400 font-mono uppercase mb-4">Quick Trade</div>

        {/* Amount slider */}
        <div className="mb-4">
          <div className="flex justify-between text-xs text-gray-400 mb-2">
            <span>Amount</span>
            <span className="text-white">{orderAmount}%</span>
          </div>
          <input
            type="range"
            min="0"
            max="100"
            value={orderAmount}
            onChange={(e) => setOrderAmount(Number(e.target.value))}
            className="w-full h-2 bg-white/10 rounded-full appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:bg-cyan-400 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:shadow-[0_0_10px_#00F5FF]"
          />
        </div>

        {/* Leverage slider */}
        <div className="mb-4">
          <div className="flex justify-between text-xs text-gray-400 mb-2">
            <span>Leverage</span>
            <span className="text-white">{leverage}x</span>
          </div>
          <input
            type="range"
            min="1"
            max="50"
            value={leverage}
            onChange={(e) => setLeverage(Number(e.target.value))}
            className="w-full h-2 bg-white/10 rounded-full appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:bg-purple-400 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:shadow-[0_0_10px_#8B5CF6]"
          />
        </div>

        {/* Long/Short buttons */}
        <div className="grid grid-cols-2 gap-3">
          <motion.button
            className="py-4 rounded-xl bg-emerald-500 text-black font-bold text-lg"
            whileTap={{ scale: 0.95 }}
          >
            🟢 LONG
          </motion.button>
          <motion.button className="py-4 rounded-xl bg-red-500 text-white font-bold text-lg" whileTap={{ scale: 0.95 }}>
            🔴 SHORT
          </motion.button>
        </div>
      </motion.div>
    </div>
  )
}
