"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { NasaHeader } from "@/components/nasa-header"
import { CriticalMetrics } from "@/components/critical-metrics"
import { QuantumStatusRing } from "@/components/quantum-status-ring"
import { PhysicsLabScreen } from "@/components/physics-lab-screen"
import { MarketIntelligence } from "@/components/market-intelligence"
import { PositionsScreen } from "@/components/positions-screen"
import { RiskControlCenter } from "@/components/risk-control-center"
import { SeraphAi } from "@/components/seraph-ai"
import { FloatingDock } from "@/components/floating-dock"
import { StarField } from "@/components/star-field"

type Screen = "home" | "lab" | "markets" | "positions" | "risk" | "ai"

export function CommandCenter() {
  const [activeScreen, setActiveScreen] = useState<Screen>("home")

  return (
    <div className="min-h-screen bg-black text-white relative overflow-hidden">
      {/* Animated star field background */}
      <StarField />

      {/* Grid overlay */}
      <div className="fixed inset-0 pointer-events-none opacity-5">
        <div
          className="w-full h-full"
          style={{
            backgroundImage: `
              linear-gradient(to right, #00F5FF 1px, transparent 1px),
              linear-gradient(to bottom, #00F5FF 1px, transparent 1px)
            `,
            backgroundSize: "30px 30px",
          }}
        />
      </div>

      {/* Scanning line effect */}
      <motion.div
        className="fixed left-0 right-0 h-px bg-gradient-to-r from-transparent via-cyan-400/50 to-transparent pointer-events-none z-50"
        animate={{ y: [0, typeof window !== "undefined" ? window.innerHeight : 800] }}
        transition={{ duration: 8, repeat: Number.POSITIVE_INFINITY, ease: "linear" }}
      />

      <NasaHeader />

      <main className="relative z-10 pb-24">
        <AnimatePresence mode="wait">
          {activeScreen === "home" && (
            <motion.div
              key="home"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className="p-4 space-y-4"
            >
              <CriticalMetrics />
              <QuantumStatusRing />
            </motion.div>
          )}

          {activeScreen === "lab" && (
            <motion.div
              key="lab"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
            >
              <PhysicsLabScreen />
            </motion.div>
          )}

          {activeScreen === "markets" && (
            <motion.div
              key="markets"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
            >
              <MarketIntelligence />
            </motion.div>
          )}

          {activeScreen === "positions" && (
            <motion.div
              key="positions"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
            >
              <PositionsScreen />
            </motion.div>
          )}

          {activeScreen === "risk" && (
            <motion.div
              key="risk"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
            >
              <RiskControlCenter />
            </motion.div>
          )}

          {activeScreen === "ai" && (
            <motion.div
              key="ai"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
            >
              <SeraphAi />
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      <FloatingDock activeScreen={activeScreen} onScreenChange={setActiveScreen} />
    </div>
  )
}
