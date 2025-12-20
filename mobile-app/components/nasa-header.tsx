"use client"

import { motion } from "framer-motion"
import { Menu } from "lucide-react"
import { useState, useEffect } from "react"

export function NasaHeader() {
  const [systemHealth, setSystemHealth] = useState(98)

  useEffect(() => {
    const interval = setInterval(() => {
      setSystemHealth(95 + Math.random() * 5)
    }, 3000)
    return () => clearInterval(interval)
  }, [])

  return (
    <header className="sticky top-0 z-40 backdrop-blur-xl bg-black/60 border-b border-cyan-500/20">
      <div className="flex items-center justify-between p-4">
        {/* Menu */}
        <motion.button className="p-2 rounded-lg bg-white/5 border border-cyan-500/30" whileTap={{ scale: 0.95 }}>
          <Menu className="w-5 h-5 text-cyan-400" />
        </motion.button>

        {/* Logo */}
        <motion.div
          className="flex items-center gap-2"
          animate={{
            textShadow: [
              "0 0 10px rgba(0,245,255,0.3)",
              "0 0 20px rgba(0,245,255,0.6)",
              "0 0 10px rgba(0,245,255,0.3)",
            ],
          }}
          transition={{ duration: 3, repeat: Number.POSITIVE_INFINITY }}
        >
          <span className="text-lg font-bold tracking-wider">
            <span className="text-cyan-400">GODBRAIN</span>
            <span className="text-white ml-1">QUANTUM</span>
          </span>
        </motion.div>

        {/* System status orb */}
        <motion.div
          className="relative w-10 h-10 flex items-center justify-center"
          animate={{
            boxShadow: [
              "0 0 10px rgba(16, 185, 129, 0.3)",
              "0 0 25px rgba(16, 185, 129, 0.6)",
              "0 0 10px rgba(16, 185, 129, 0.3)",
            ],
          }}
          transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY }}
        >
          <div className="absolute inset-0 bg-emerald-500/20 rounded-full" />
          <motion.div
            className="w-4 h-4 bg-emerald-400 rounded-full"
            animate={{ scale: [1, 1.2, 1] }}
            transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY }}
          />
          <span className="absolute -bottom-1 text-[8px] text-emerald-400 font-mono">{systemHealth.toFixed(0)}%</span>
        </motion.div>
      </div>
    </header>
  )
}
