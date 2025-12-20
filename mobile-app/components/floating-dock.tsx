"use client"

import type React from "react"

import { motion } from "framer-motion"
import { Home, Atom, BarChart3, Zap, Shield, Brain } from "lucide-react"

type Screen = "home" | "lab" | "markets" | "positions" | "risk" | "ai"

interface FloatingDockProps {
  activeScreen: Screen
  onScreenChange: (screen: Screen) => void
}

const navItems: { id: Screen; icon: React.ReactNode; label: string }[] = [
  { id: "home", icon: <Home className="w-5 h-5" />, label: "Home" },
  { id: "lab", icon: <Atom className="w-5 h-5" />, label: "Lab" },
  { id: "markets", icon: <BarChart3 className="w-5 h-5" />, label: "Markets" },
  { id: "positions", icon: <Zap className="w-5 h-5" />, label: "Execute" },
  { id: "risk", icon: <Shield className="w-5 h-5" />, label: "Risk" },
  { id: "ai", icon: <Brain className="w-5 h-5" />, label: "AI" },
]

export function FloatingDock({ activeScreen, onScreenChange }: FloatingDockProps) {
  return (
    <motion.div
      className="fixed bottom-4 left-4 right-4 z-50"
      initial={{ y: 100, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ delay: 0.5 }}
    >
      <div className="flex items-center justify-around p-2 rounded-2xl bg-black/80 backdrop-blur-xl border border-cyan-500/20 shadow-[0_0_30px_rgba(0,245,255,0.1)]">
        {navItems.map((item) => (
          <motion.button
            key={item.id}
            className={`relative flex flex-col items-center gap-1 p-3 rounded-xl transition-colors ${
              activeScreen === item.id ? "text-cyan-400" : "text-gray-500"
            }`}
            onClick={() => onScreenChange(item.id)}
            whileTap={{ scale: 0.9 }}
          >
            {activeScreen === item.id && (
              <motion.div
                className="absolute inset-0 bg-cyan-500/10 rounded-xl"
                layoutId="activeTab"
                transition={{ type: "spring", stiffness: 300, damping: 30 }}
              />
            )}
            <motion.div
              className="relative z-10"
              animate={
                activeScreen === item.id
                  ? {
                      y: [0, -2, 0],
                      filter: [
                        "drop-shadow(0 0 5px #00F5FF)",
                        "drop-shadow(0 0 10px #00F5FF)",
                        "drop-shadow(0 0 5px #00F5FF)",
                      ],
                    }
                  : {}
              }
              transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY }}
            >
              {item.icon}
            </motion.div>
            <span className="relative z-10 text-[10px] font-mono">{item.label}</span>
          </motion.button>
        ))}
      </div>
    </motion.div>
  )
}
