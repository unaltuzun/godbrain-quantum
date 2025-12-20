"use client"

import React from "react"
import { motion } from "framer-motion"
import { useState, useEffect } from "react"
import { Shield, AlertTriangle } from "lucide-react"

export function RiskControlCenter() {
  const [riskLevel, setRiskLevel] = useState(35)
  const [holdProgress, setHoldProgress] = useState(0)
  const [isHolding, setIsHolding] = useState(false)

  const [metrics] = useState({
    var: 2.1,
    cvar: 3.4,
    maxDd: 8.2,
    exposure: 68,
  })

  const [correlations] = useState([
    [1.0, 0.8, 0.6, 0.3],
    [0.8, 1.0, 0.7, 0.4],
    [0.6, 0.7, 1.0, 0.5],
    [0.3, 0.4, 0.5, 1.0],
  ])

  const assets = ["BTC", "ETH", "SOL", "DOGE"]

  // Animate risk level
  useEffect(() => {
    const interval = setInterval(() => {
      setRiskLevel((prev) => Math.max(10, Math.min(90, prev + (Math.random() - 0.5) * 10)))
    }, 5000)
    return () => clearInterval(interval)
  }, [])

  // Handle emergency button hold
  useEffect(() => {
    let interval: NodeJS.Timeout
    if (isHolding) {
      interval = setInterval(() => {
        setHoldProgress((prev) => {
          if (prev >= 100) {
            setIsHolding(false)
            alert("EMERGENCY STOP ACTIVATED")
            return 0
          }
          return prev + 3
        })
      }, 100)
    } else {
      setHoldProgress(0)
    }
    return () => clearInterval(interval)
  }, [isHolding])

  const getRiskColor = (level: number) => {
    if (level < 30) return "#10B981"
    if (level < 60) return "#F59E0B"
    return "#EF4444"
  }

  const needleAngle = -90 + (riskLevel / 100) * 180

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <motion.div animate={{ scale: [1, 1.1, 1] }} transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY }}>
          <Shield className="w-6 h-6 text-cyan-400" />
        </motion.div>
        <h1 className="text-lg font-bold text-white">RISK MATRIX</h1>
      </div>

      {/* Main risk gauge */}
      <div className="relative h-48 flex items-center justify-center">
        <svg viewBox="0 0 200 120" className="w-64 h-40">
          <defs>
            <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#10B981" />
              <stop offset="50%" stopColor="#F59E0B" />
              <stop offset="100%" stopColor="#EF4444" />
            </linearGradient>
            <filter id="gaugeGlow">
              <feGaussianBlur stdDeviation="2" result="coloredBlur" />
              <feMerge>
                <feMergeNode in="coloredBlur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Background arc */}
          <path
            d="M 20 100 A 80 80 0 0 1 180 100"
            fill="none"
            stroke="#1a1a2e"
            strokeWidth="12"
            strokeLinecap="round"
          />

          {/* Colored arc */}
          <path
            d="M 20 100 A 80 80 0 0 1 180 100"
            fill="none"
            stroke="url(#gaugeGradient)"
            strokeWidth="12"
            strokeLinecap="round"
            filter="url(#gaugeGlow)"
          />

          {/* Needle */}
          <motion.g
            animate={{ rotate: needleAngle }}
            transition={{ type: "spring", stiffness: 50, damping: 15 }}
            style={{ transformOrigin: "100px 100px" }}
          >
            <line
              x1="100"
              y1="100"
              x2="100"
              y2="35"
              stroke={getRiskColor(riskLevel)}
              strokeWidth="3"
              strokeLinecap="round"
            />
            <circle cx="100" cy="100" r="8" fill={getRiskColor(riskLevel)} />
          </motion.g>

          {/* Labels */}
          <text x="20" y="115" fill="#10B981" fontSize="10" fontWeight="bold">
            SAFE
          </text>
          <text x="160" y="115" fill="#EF4444" fontSize="10" fontWeight="bold">
            DANGER
          </text>
          <text x="100" y="85" textAnchor="middle" fill="white" fontSize="20" fontWeight="bold">
            {riskLevel.toFixed(0)}%
          </text>
          <text x="100" y="98" textAnchor="middle" fill="#9ca3af" fontSize="8">
            RISK LEVEL
          </text>
        </svg>
      </div>

      {/* Risk metrics grid */}
      <div className="grid grid-cols-4 gap-2">
        {[
          { label: "VaR", value: `${metrics.var}%`, status: "normal" },
          { label: "CVaR", value: `${metrics.cvar}%`, status: "normal" },
          { label: "MAX DD", value: `${metrics.maxDd}%`, status: "watch" },
          { label: "EXPOSURE", value: `${metrics.exposure}%`, status: "high" },
        ].map((metric) => (
          <div key={metric.label} className="p-3 rounded-xl bg-white/5 border border-white/10 text-center">
            <div className="text-[10px] text-gray-500 font-mono mb-1">{metric.label}</div>
            <div className="text-lg font-bold text-white">{metric.value}</div>
            <div
              className={`text-[8px] font-mono ${metric.status === "normal"
                ? "text-emerald-400"
                : metric.status === "watch"
                  ? "text-amber-400"
                  : "text-red-400"
                }`}
            >
              [{metric.status.toUpperCase()}]
            </div>
          </div>
        ))}
      </div>

      {/* Correlation matrix */}
      <div className="p-4 rounded-2xl bg-white/5 border border-white/10">
        <div className="text-xs text-gray-400 font-mono uppercase mb-3">Correlation Matrix</div>
        <div className="grid grid-cols-5 gap-1">
          {/* Header row */}
          <div />
          {assets.map((asset) => (
            <div key={asset} className="text-center text-[10px] text-gray-400 font-mono">
              {asset}
            </div>
          ))}

          {/* Data rows */}
          {correlations.map((row, i) => (
            <React.Fragment key={`row-${i}`}>
              <div className="text-[10px] text-gray-400 font-mono flex items-center">
                {assets[i]}
              </div>
              {row.map((val, j) => (
                <motion.div
                  key={`${i}-${j}`}
                  className="aspect-square rounded flex items-center justify-center text-[10px] font-mono"
                  style={{
                    backgroundColor: `rgba(0, 245, 255, ${val * 0.5})`,
                    color: val > 0.5 ? "black" : "white",
                  }}
                  whileHover={{ scale: 1.1 }}
                >
                  {val.toFixed(1)}
                </motion.div>
              ))}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* Emergency controls */}
      <div className="space-y-3">
        <div className="text-xs text-gray-400 font-mono uppercase">Emergency Controls</div>

        {/* Emergency stop button */}
        <motion.button
          className="relative w-full py-6 rounded-2xl bg-red-500/20 border-2 border-red-500/50 overflow-hidden"
          onMouseDown={() => setIsHolding(true)}
          onMouseUp={() => setIsHolding(false)}
          onMouseLeave={() => setIsHolding(false)}
          onTouchStart={() => setIsHolding(true)}
          onTouchEnd={() => setIsHolding(false)}
          animate={{
            boxShadow: isHolding
              ? ["0 0 20px rgba(239,68,68,0.5)", "0 0 40px rgba(239,68,68,0.8)", "0 0 20px rgba(239,68,68,0.5)"]
              : ["0 0 10px rgba(239,68,68,0.2)", "0 0 20px rgba(239,68,68,0.4)", "0 0 10px rgba(239,68,68,0.2)"],
          }}
          transition={{ duration: 1, repeat: Number.POSITIVE_INFINITY }}
        >
          {/* Progress overlay */}
          <motion.div className="absolute inset-0 bg-red-500" style={{ width: `${holdProgress}%` }} />

          {/* Circular progress */}
          <svg className="absolute inset-0 w-full h-full pointer-events-none">
            <circle cx="50%" cy="50%" r="30" fill="none" stroke="rgba(255,255,255,0.2)" strokeWidth="4" />
            <circle
              cx="50%"
              cy="50%"
              r="30"
              fill="none"
              stroke="white"
              strokeWidth="4"
              strokeDasharray={`${holdProgress * 1.88} 188`}
              strokeLinecap="round"
              transform="rotate(-90 50% 50%)"
            />
          </svg>

          <div className="relative z-10 flex flex-col items-center gap-1">
            <AlertTriangle className="w-6 h-6 text-red-400" />
            <span className="text-red-400 font-bold">EMERGENCY STOP</span>
            <span className="text-xs text-red-400/70">Press and hold for 3 seconds</span>
          </div>
        </motion.button>

        {/* Quick actions */}
        <div className="grid grid-cols-3 gap-2">
          <button className="py-3 rounded-xl bg-amber-500/20 border border-amber-500/30 text-xs text-amber-400 font-mono">
            Pause Trading
          </button>
          <button className="py-3 rounded-xl bg-emerald-500/20 border border-emerald-500/30 text-xs text-emerald-400 font-mono">
            Close Longs
          </button>
          <button className="py-3 rounded-xl bg-red-500/20 border border-red-500/30 text-xs text-red-400 font-mono">
            Close Shorts
          </button>
        </div>
      </div>
    </div>
  )
}
