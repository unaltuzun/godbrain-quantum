"use client"

import { motion } from "framer-motion"
import { useEffect, useState, useRef } from "react"
import { TrendingUp, TrendingDown } from "lucide-react"

interface MetricCardProps {
  title: string
  value: string
  change: string
  isPositive: boolean
  delay: number
}

function MetricCard({ title, value, change, isPositive, delay }: MetricCardProps) {
  return (
    <motion.div
      className="flex-shrink-0 w-40 p-4 rounded-2xl bg-gradient-to-br from-white/5 to-white/0 border border-cyan-500/20 backdrop-blur-sm"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      whileHover={{ scale: 1.02, borderColor: "rgba(0, 245, 255, 0.4)" }}
    >
      <div className="text-xs text-gray-400 mb-1 font-mono uppercase tracking-wider">{title}</div>
      <motion.div
        className="text-xl font-bold text-white mb-1"
        animate={{
          textShadow: ["0 0 5px rgba(0,245,255,0.2)", "0 0 15px rgba(0,245,255,0.4)", "0 0 5px rgba(0,245,255,0.2)"],
        }}
        transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY }}
      >
        {value}
      </motion.div>
      <div className={`flex items-center gap-1 text-xs ${isPositive ? "text-emerald-400" : "text-red-400"}`}>
        {isPositive ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
        {change}
      </div>

      {/* Holographic wave effect */}
      <motion.div
        className="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-cyan-500 to-purple-500 opacity-50"
        animate={{ scaleX: [0, 1, 0], x: ["-100%", "0%", "100%"] }}
        transition={{ duration: 3, repeat: Number.POSITIVE_INFINITY }}
      />
    </motion.div>
  )
}

export function CriticalMetrics() {
  const [metrics, setMetrics] = useState({
    equity: 12847.32,
    pnl: 847.21,
    sharpe: 2.34,
    voltran: 94.2,
  })

  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const interval = setInterval(() => {
      setMetrics((prev) => ({
        equity: prev.equity + (Math.random() - 0.5) * 50,
        pnl: prev.pnl + (Math.random() - 0.5) * 20,
        sharpe: Math.max(0, prev.sharpe + (Math.random() - 0.5) * 0.1),
        voltran: Math.min(100, Math.max(0, prev.voltran + (Math.random() - 0.5) * 2)),
      }))
    }, 3000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="relative">
      <div ref={scrollRef} className="flex gap-3 overflow-x-auto pb-2 scrollbar-hide">
        <MetricCard
          title="Total Equity"
          value={`$${metrics.equity.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
          change="▲ 12.4%"
          isPositive={true}
          delay={0}
        />
        <MetricCard
          title="Daily P&L"
          value={`+$${metrics.pnl.toFixed(2)}`}
          change="▲ 7.2%"
          isPositive={true}
          delay={0.1}
        />
        <MetricCard title="Sharpe" value={metrics.sharpe.toFixed(2)} change="▲ 0.12" isPositive={true} delay={0.2} />
        <MetricCard
          title="VOLTRAN"
          value={`${metrics.voltran.toFixed(1)}%`}
          change="▲ 2.1%"
          isPositive={true}
          delay={0.3}
        />
      </div>
    </div>
  )
}
