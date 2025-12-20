"use client"

import { useEffect, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"

interface BootSequenceProps {
  onComplete: () => void
  progress: number
  setProgress: (p: number) => void
}

const systems = [
  { name: "PHYSICS LAB", icon: "⚛️", delay: 0 },
  { name: "NEURAL MATRIX", icon: "🧠", delay: 300 },
  { name: "MARKET FEED", icon: "📡", delay: 600 },
  { name: "QUANTUM BRIDGE", icon: "🌌", delay: 900 },
]

export function BootSequence({ onComplete, progress, setProgress }: BootSequenceProps) {
  const [currentText, setCurrentText] = useState("")
  const [systemStatus, setSystemStatus] = useState<Record<string, number>>({})
  const [phase, setPhase] = useState<"logo" | "init" | "systems" | "complete">("logo")

  const fullText = "INITIALIZING QUANTUM CORES..."

  useEffect(() => {
    // Logo phase
    const logoTimer = setTimeout(() => setPhase("init"), 1500)
    return () => clearTimeout(logoTimer)
  }, [])

  useEffect(() => {
    if (phase === "init") {
      // Typing effect
      let i = 0
      const typeInterval = setInterval(() => {
        if (i <= fullText.length) {
          setCurrentText(fullText.slice(0, i))
          i++
        } else {
          clearInterval(typeInterval)
          setPhase("systems")
        }
      }, 50)
      return () => clearInterval(typeInterval)
    }
  }, [phase])

  useEffect(() => {
    if (phase === "systems") {
      systems.forEach((system) => {
        setTimeout(() => {
          const interval = setInterval(() => {
            setSystemStatus((prev) => {
              const current = prev[system.name] || 0
              if (current >= 100) {
                clearInterval(interval)
                return prev
              }
              return { ...prev, [system.name]: current + Math.random() * 15 }
            })
          }, 100)
        }, system.delay)
      })

      // Overall progress
      const progressInterval = setInterval(() => {
        setProgress((prev: number) => {
          if (prev >= 100) {
            clearInterval(progressInterval)
            setTimeout(() => setPhase("complete"), 500)
            return 100
          }
          return prev + 2
        })
      }, 50)

      return () => clearInterval(progressInterval)
    }
  }, [phase, setProgress])

  useEffect(() => {
    if (phase === "complete") {
      const timer = setTimeout(onComplete, 1000)
      return () => clearTimeout(timer)
    }
  }, [phase, onComplete])

  return (
    <div className="fixed inset-0 bg-black flex items-center justify-center overflow-hidden">
      {/* Animated star field background */}
      <div className="absolute inset-0" suppressHydrationWarning>
        {[...Array(100)].map((_, i) => {
          // Use seeded values based on index for consistent SSR/client rendering
          const left = ((i * 17 + 31) % 100);
          const top = ((i * 23 + 47) % 100);
          const duration = 2 + (i % 5) * 0.5;
          const delay = (i % 20) * 0.1;
          return (
            <motion.div
              key={i}
              className="absolute w-0.5 h-0.5 bg-white rounded-full"
              style={{
                left: `${left}%`,
                top: `${top}%`,
              }}
              animate={{
                opacity: [0.2, 1, 0.2],
                scale: [0.5, 1, 0.5],
              }}
              transition={{
                duration: duration,
                repeat: Number.POSITIVE_INFINITY,
                delay: delay,
              }}
            />
          );
        })}
      </div>

      {/* Grid overlay */}
      <div className="absolute inset-0 opacity-10">
        <div
          className="w-full h-full"
          style={{
            backgroundImage: `
              linear-gradient(to right, #00F5FF 1px, transparent 1px),
              linear-gradient(to bottom, #00F5FF 1px, transparent 1px)
            `,
            backgroundSize: "40px 40px",
          }}
        />
      </div>

      {/* Scanning line */}
      <motion.div
        className="absolute left-0 right-0 h-1 bg-gradient-to-r from-transparent via-cyan-400 to-transparent"
        animate={{ y: ["-100vh", "100vh"] }}
        transition={{ duration: 3, repeat: Number.POSITIVE_INFINITY, ease: "linear" }}
      />

      <div className="relative z-10 flex flex-col items-center gap-8 px-6 w-full max-w-md">
        {/* Logo */}
        <AnimatePresence>
          <motion.div
            className="relative"
            initial={{ opacity: 0, scale: 0.5 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8, ease: "easeOut" }}
          >
            {/* Orbital rings */}
            <motion.div
              className="absolute inset-0 -m-8"
              animate={{ rotate: 360 }}
              transition={{ duration: 20, repeat: Number.POSITIVE_INFINITY, ease: "linear" }}
            >
              <div className="w-full h-full border border-cyan-500/30 rounded-full" />
            </motion.div>
            <motion.div
              className="absolute inset-0 -m-12"
              animate={{ rotate: -360 }}
              transition={{ duration: 30, repeat: Number.POSITIVE_INFINITY, ease: "linear" }}
            >
              <div className="w-full h-full border border-purple-500/20 rounded-full" />
            </motion.div>

            {/* Core logo */}
            <motion.div
              className="w-24 h-24 relative"
              animate={{
                boxShadow: [
                  "0 0 20px rgba(0, 245, 255, 0.3)",
                  "0 0 60px rgba(0, 245, 255, 0.6)",
                  "0 0 20px rgba(0, 245, 255, 0.3)",
                ],
              }}
              transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY }}
            >
              <div className="absolute inset-0 bg-gradient-to-br from-cyan-500 to-purple-600 rounded-2xl opacity-20" />
              <div className="absolute inset-1 bg-black rounded-xl flex items-center justify-center">
                <motion.span
                  className="text-4xl"
                  animate={{ rotate: [0, 360] }}
                  transition={{ duration: 10, repeat: Number.POSITIVE_INFINITY, ease: "linear" }}
                >
                  ⚛️
                </motion.span>
              </div>
            </motion.div>
          </motion.div>
        </AnimatePresence>

        {/* Title */}
        <motion.div
          className="text-center"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
        >
          <h1 className="text-2xl font-bold tracking-wider">
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-purple-500">GODBRAIN</span>
            <span className="text-white ml-2">QUANTUM</span>
          </h1>
        </motion.div>

        {/* Typing text */}
        <motion.div
          className="h-6 font-mono text-sm text-cyan-400"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1 }}
        >
          {currentText}
          <motion.span
            animate={{ opacity: [1, 0, 1] }}
            transition={{ duration: 0.5, repeat: Number.POSITIVE_INFINITY }}
          >
            _
          </motion.span>
        </motion.div>

        {/* System progress bars */}
        {phase !== "logo" && (
          <motion.div
            className="w-full space-y-3"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
          >
            {systems.map((system) => (
              <motion.div
                key={system.name}
                className="flex items-center gap-3"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: system.delay / 1000 + 1.5 }}
              >
                <span className="text-lg">{system.icon}</span>
                <div className="flex-1">
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-gray-400 font-mono">{system.name}</span>
                    <span className="text-cyan-400 font-mono">
                      {Math.min(100, Math.floor(systemStatus[system.name] || 0))}%
                    </span>
                  </div>
                  <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                    <motion.div
                      className="h-full bg-gradient-to-r from-cyan-500 to-cyan-400 rounded-full"
                      style={{ width: `${Math.min(100, systemStatus[system.name] || 0)}%` }}
                      animate={{
                        boxShadow:
                          (systemStatus[system.name] || 0) >= 100
                            ? ["0 0 10px #00F5FF", "0 0 20px #00F5FF", "0 0 10px #00F5FF"]
                            : "none",
                      }}
                      transition={{ duration: 1, repeat: Number.POSITIVE_INFINITY }}
                    />
                  </div>
                </div>
              </motion.div>
            ))}
          </motion.div>
        )}

        {/* Complete message */}
        <AnimatePresence>
          {phase === "complete" && (
            <motion.div
              className="flex items-center gap-2 text-emerald-400 font-mono"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
            >
              <motion.div
                className="w-3 h-3 bg-emerald-400 rounded-full"
                animate={{
                  boxShadow: ["0 0 10px #10B981", "0 0 30px #10B981", "0 0 10px #10B981"],
                }}
                transition={{ duration: 0.5, repeat: Number.POSITIVE_INFINITY }}
              />
              SYSTEM ONLINE
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
