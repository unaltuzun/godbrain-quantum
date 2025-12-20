"use client"

import { motion } from "framer-motion"
import { useState, useEffect } from "react"
import { AlertTriangle } from "lucide-react"

interface Genome {
  id: number
  x: number
  y: number
  fitness: number
  alive: boolean
}

export function PhysicsLabScreen() {
  const [activeUniverse, setActiveUniverse] = useState(1)
  const [genomes, setGenomes] = useState<Genome[]>([])
  const [metrics, setMetrics] = useState({
    generation: 19877,
    lineage: 32,
    alive: 656,
    fStab: 0.054,
    fEnergy: 1.872,
    bestFit: 98.4,
  })
  const [hasAnomaly, setHasAnomaly] = useState(true)

  // Initialize genomes
  useEffect(() => {
    const initial = [...Array(50)].map((_, i) => ({
      id: i,
      x: Math.random() * 100,
      y: Math.random() * 100,
      fitness: Math.random() * 100,
      alive: Math.random() > 0.2,
    }))
    setGenomes(initial)
  }, [])

  // Animate genomes
  useEffect(() => {
    const interval = setInterval(() => {
      setGenomes((prev) =>
        prev.map((g) => ({
          ...g,
          x: Math.max(0, Math.min(100, g.x + (Math.random() - 0.5) * 5)),
          y: Math.max(0, Math.min(100, g.y + (Math.random() - 0.5) * 5)),
          fitness: Math.max(0, Math.min(100, g.fitness + (Math.random() - 0.5) * 10)),
        })),
      )
      setMetrics((prev) => ({
        ...prev,
        generation: prev.generation + Math.floor(Math.random() * 3),
        alive: Math.max(500, Math.min(800, prev.alive + Math.floor((Math.random() - 0.5) * 20))),
        fStab: Math.max(0, prev.fStab + (Math.random() - 0.5) * 0.01),
        fEnergy: Math.max(0, prev.fEnergy + (Math.random() - 0.5) * 0.1),
        bestFit: Math.min(100, Math.max(90, prev.bestFit + (Math.random() - 0.5) * 0.5)),
      }))
    }, 1000)
    return () => clearInterval(interval)
  }, [])

  const universes = [1, 2, 3, 4, 5, 6]

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <motion.span
          className="text-2xl"
          animate={{ rotate: [0, 360] }}
          transition={{ duration: 10, repeat: Number.POSITIVE_INFINITY, ease: "linear" }}
        >
          ⚛️
        </motion.span>
        <h1 className="text-lg font-bold text-white">QUANTUM PHYSICS LAB</h1>
      </div>

      {/* Universe selector */}
      <div className="flex gap-2 overflow-x-auto pb-2">
        {universes.map((u) => (
          <motion.button
            key={u}
            className={`px-4 py-2 rounded-full text-sm font-mono transition-all ${
              activeUniverse === u ? "bg-cyan-500 text-black" : "bg-white/5 text-gray-400 border border-white/10"
            }`}
            whileTap={{ scale: 0.95 }}
            onClick={() => setActiveUniverse(u)}
          >
            U{u} {activeUniverse === u && "●"}
          </motion.button>
        ))}
      </div>

      {/* Phase space visualization */}
      <motion.div
        className="relative h-64 rounded-2xl bg-black/50 border border-cyan-500/20 overflow-hidden"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
      >
        {/* Grid background */}
        <div
          className="absolute inset-0 opacity-20"
          style={{
            backgroundImage: `
              linear-gradient(to right, #00F5FF 1px, transparent 1px),
              linear-gradient(to bottom, #00F5FF 1px, transparent 1px)
            `,
            backgroundSize: "20px 20px",
          }}
        />

        {/* Pareto front surface */}
        <svg className="absolute inset-0 w-full h-full">
          <defs>
            <linearGradient id="paretoGradient" x1="0%" y1="100%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#00F5FF" stopOpacity="0" />
              <stop offset="50%" stopColor="#00F5FF" stopOpacity="0.3" />
              <stop offset="100%" stopColor="#8B5CF6" stopOpacity="0.1" />
            </linearGradient>
          </defs>
          <path d="M 0 256 Q 80 200, 160 150 T 320 80 T 400 40" fill="url(#paretoGradient)" />
        </svg>

        {/* Genome particles */}
        {genomes.map((genome) => (
          <motion.div
            key={genome.id}
            className="absolute"
            style={{ left: `${genome.x}%`, top: `${genome.y}%` }}
            animate={{
              scale: genome.alive ? [1, 1.5, 1] : [1, 0.5],
              opacity: genome.alive ? 1 : 0.3,
            }}
            transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY }}
          >
            <div
              className={`w-2 h-2 rounded-full ${
                genome.fitness > 80
                  ? "bg-emerald-400 shadow-[0_0_10px_#10B981]"
                  : genome.fitness > 50
                    ? "bg-cyan-400 shadow-[0_0_8px_#00F5FF]"
                    : "bg-purple-400 shadow-[0_0_6px_#8B5CF6]"
              }`}
            />
          </motion.div>
        ))}

        {/* Axis labels */}
        <div className="absolute bottom-2 left-1/2 -translate-x-1/2 text-[10px] text-gray-500 font-mono">f_stab →</div>
        <div className="absolute left-2 top-1/2 -translate-y-1/2 -rotate-90 text-[10px] text-gray-500 font-mono">
          f_energy →
        </div>

        {/* Scanning line */}
        <motion.div
          className="absolute left-0 right-0 h-px bg-gradient-to-r from-transparent via-cyan-400 to-transparent"
          animate={{ y: [0, 256] }}
          transition={{ duration: 4, repeat: Number.POSITIVE_INFINITY, ease: "linear" }}
        />
      </motion.div>

      {/* Metrics grid */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: "GENERATION", value: metrics.generation.toLocaleString(), icon: "↑" },
          { label: "LINEAGE", value: metrics.lineage, icon: "🌳" },
          { label: "ALIVE", value: metrics.alive, icon: "●" },
          { label: "f_stab", value: metrics.fStab.toFixed(3), icon: "~" },
          { label: "f_energy", value: metrics.fEnergy.toFixed(3), icon: "⚡" },
          { label: "BEST FIT", value: `${metrics.bestFit.toFixed(1)}%`, icon: "★" },
        ].map((metric, i) => (
          <motion.div
            key={metric.label}
            className="p-3 rounded-xl bg-white/5 border border-white/10"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
          >
            <div className="text-[10px] text-gray-500 font-mono mb-1">{metric.label}</div>
            <div className="flex items-center gap-2">
              <span className="text-gray-400">{metric.icon}</span>
              <motion.span
                className="text-lg font-bold text-white"
                animate={i === 0 ? { textShadow: ["0 0 5px #00F5FF", "0 0 15px #00F5FF", "0 0 5px #00F5FF"] } : {}}
                transition={{ duration: 1, repeat: Number.POSITIVE_INFINITY }}
              >
                {metric.value}
              </motion.span>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Anomaly alert */}
      {hasAnomaly && (
        <motion.div
          className="p-4 rounded-xl bg-gradient-to-r from-red-500/20 to-orange-500/20 border border-red-500/30"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
        >
          <div className="flex items-center gap-3">
            <motion.div animate={{ scale: [1, 1.2, 1] }} transition={{ duration: 1, repeat: Number.POSITIVE_INFINITY }}>
              <AlertTriangle className="w-5 h-5 text-orange-400" />
            </motion.div>
            <div className="flex-1">
              <div className="text-sm font-medium text-orange-400">ANOMALY DETECTED</div>
              <div className="text-xs text-gray-400">Phase Transition at Gen 15,442</div>
            </div>
            <button className="text-xs text-cyan-400 font-mono" onClick={() => setHasAnomaly(false)}>
              View Details →
            </button>
          </div>
        </motion.div>
      )}
    </div>
  )
}
