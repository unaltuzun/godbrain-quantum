"use client"

import { motion } from "framer-motion"
import { useState, useEffect } from "react"
import { godbrainApi } from "@/lib/api"

export function QuantumStatusRing() {
  const [metrics, setMetrics] = useState({
    voltran: 94.2,
    dnaGen: 19877,
    epoch: 313,
    riskVar: 2.1,
  })

  useEffect(() => {
    // Fetch from GODBRAIN API
    const fetchData = async () => {
      try {
        const data = await godbrainApi.getStatus()
        setMetrics({
          voltran: data?.voltran_score ?? 85.0,
          dnaGen: data?.dna_generation ?? 7060,
          epoch: data?.epoch ?? 313,
          riskVar: data?.risk_var ?? 1.0,
        })
      } catch (error) {
        console.error('API error:', error)
      }
    }

    fetchData()
    const interval = setInterval(fetchData, 5000) // Refresh every 5 seconds
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="relative p-6">
      {/* Background glow */}
      <div className="absolute inset-0 flex items-center justify-center">
        <motion.div
          className="w-64 h-64 rounded-full bg-cyan-500/5 blur-3xl"
          animate={{
            scale: [1, 1.2, 1],
            opacity: [0.3, 0.5, 0.3],
          }}
          transition={{ duration: 4, repeat: Number.POSITIVE_INFINITY }}
        />
      </div>

      {/* Main ring container */}
      <div className="relative flex items-center justify-center">
        {/* Outer rotating ring */}
        <motion.div
          className="absolute w-72 h-72"
          animate={{ rotate: 360 }}
          transition={{ duration: 60, repeat: Number.POSITIVE_INFINITY, ease: "linear" }}
        >
          <svg viewBox="0 0 200 200" className="w-full h-full">
            <defs>
              <linearGradient id="ringGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#00F5FF" stopOpacity="0.8" />
                <stop offset="50%" stopColor="#8B5CF6" stopOpacity="0.6" />
                <stop offset="100%" stopColor="#00F5FF" stopOpacity="0.8" />
              </linearGradient>
            </defs>
            <circle
              cx="100"
              cy="100"
              r="95"
              fill="none"
              stroke="url(#ringGradient)"
              strokeWidth="1"
              strokeDasharray="10 5"
            />
          </svg>
        </motion.div>

        {/* Inner counter-rotating ring */}
        <motion.div
          className="absolute w-60 h-60"
          animate={{ rotate: -360 }}
          transition={{ duration: 40, repeat: Number.POSITIVE_INFINITY, ease: "linear" }}
        >
          <svg viewBox="0 0 200 200" className="w-full h-full">
            <circle
              cx="100"
              cy="100"
              r="95"
              fill="none"
              stroke="#8B5CF6"
              strokeWidth="0.5"
              strokeDasharray="4 8"
              strokeOpacity="0.4"
            />
          </svg>
        </motion.div>

        {/* Metric segments */}
        <div className="absolute w-80 h-80">
          {/* Top - VOLTRAN */}
          <motion.div
            className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-2 text-center"
            animate={{ y: [-2, 2, -2] }}
            transition={{ duration: 3, repeat: Number.POSITIVE_INFINITY }}
          >
            <div className="px-4 py-2 rounded-lg bg-black/60 border border-cyan-500/30 backdrop-blur-sm">
              <div className="text-[10px] text-gray-400 font-mono">VOLTRAN</div>
              <motion.div
                className="text-lg font-bold text-cyan-400"
                animate={{ textShadow: ["0 0 10px #00F5FF", "0 0 20px #00F5FF", "0 0 10px #00F5FF"] }}
                transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY }}
              >
                {metrics.voltran.toFixed(1)}
              </motion.div>
            </div>
          </motion.div>

          {/* Right - DNA GEN */}
          <motion.div
            className="absolute right-0 top-1/2 translate-x-2 -translate-y-1/2 text-center"
            animate={{ x: [2, -2, 2] }}
            transition={{ duration: 3, repeat: Number.POSITIVE_INFINITY, delay: 0.5 }}
          >
            <div className="px-4 py-2 rounded-lg bg-black/60 border border-purple-500/30 backdrop-blur-sm">
              <div className="text-[10px] text-gray-400 font-mono">DNA GEN</div>
              <motion.div className="text-lg font-bold text-purple-400">{metrics.dnaGen.toLocaleString()}</motion.div>
            </div>
          </motion.div>

          {/* Bottom - EPOCH */}
          <motion.div
            className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-2 text-center"
            animate={{ y: [2, -2, 2] }}
            transition={{ duration: 3, repeat: Number.POSITIVE_INFINITY, delay: 1 }}
          >
            <div className="px-4 py-2 rounded-lg bg-black/60 border border-emerald-500/30 backdrop-blur-sm">
              <div className="text-[10px] text-gray-400 font-mono">EPOCH</div>
              <motion.div className="text-lg font-bold text-emerald-400">{metrics.epoch}</motion.div>
            </div>
          </motion.div>

          {/* Left - RISK VAR */}
          <motion.div
            className="absolute left-0 top-1/2 -translate-x-2 -translate-y-1/2 text-center"
            animate={{ x: [-2, 2, -2] }}
            transition={{ duration: 3, repeat: Number.POSITIVE_INFINITY, delay: 1.5 }}
          >
            <div className="px-4 py-2 rounded-lg bg-black/60 border border-amber-500/30 backdrop-blur-sm">
              <div className="text-[10px] text-gray-400 font-mono">RISK VAR</div>
              <motion.div className="text-lg font-bold text-amber-400">{metrics.riskVar.toFixed(1)}%</motion.div>
            </div>
          </motion.div>
        </div>

        {/* Central core */}
        <motion.div
          className="relative w-32 h-32"
          animate={{
            boxShadow: [
              "0 0 30px rgba(0, 245, 255, 0.3), inset 0 0 30px rgba(0, 245, 255, 0.1)",
              "0 0 60px rgba(0, 245, 255, 0.5), inset 0 0 40px rgba(0, 245, 255, 0.2)",
              "0 0 30px rgba(0, 245, 255, 0.3), inset 0 0 30px rgba(0, 245, 255, 0.1)",
            ],
          }}
          transition={{ duration: 3, repeat: Number.POSITIVE_INFINITY }}
        >
          <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/20 to-purple-600/20 rounded-full" />
          <div className="absolute inset-2 bg-black rounded-full flex items-center justify-center">
            {/* Particle effects */}
            {[...Array(8)].map((_, i) => (
              <motion.div
                key={i}
                className="absolute w-1 h-1 bg-cyan-400 rounded-full"
                animate={{
                  x: [0, Math.cos((i * Math.PI) / 4) * 40, 0],
                  y: [0, Math.sin((i * Math.PI) / 4) * 40, 0],
                  opacity: [1, 0.3, 1],
                }}
                transition={{
                  duration: 3,
                  repeat: Number.POSITIVE_INFINITY,
                  delay: i * 0.2,
                }}
              />
            ))}
            <motion.span
              className="text-3xl z-10"
              animate={{ rotate: [0, 360] }}
              transition={{ duration: 20, repeat: Number.POSITIVE_INFINITY, ease: "linear" }}
            >
              ⚛️
            </motion.span>
          </div>
        </motion.div>
      </div>

      {/* Status text */}
      <motion.div
        className="text-center mt-8 text-sm text-gray-400 font-mono"
        animate={{ opacity: [0.5, 1, 0.5] }}
        transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY }}
      >
        QUANTUM CORE ACTIVE • ALL SYSTEMS NOMINAL
      </motion.div>
    </div>
  )
}
