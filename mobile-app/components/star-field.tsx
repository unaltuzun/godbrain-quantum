"use client"

import { motion } from "framer-motion"
import { useMemo } from "react"

export function StarField() {
  const stars = useMemo(
    () =>
      [...Array(80)].map((_, i) => ({
        id: i,
        // Use seeded values for consistent SSR/client
        x: ((i * 17 + 31) % 100),
        y: ((i * 23 + 47) % 100),
        size: 0.5 + (i % 4) * 0.5,
        duration: 2 + (i % 5) * 0.6,
        delay: (i % 20) * 0.1,
      })),
    [],
  )

  return (
    <div className="fixed inset-0 pointer-events-none">
      {stars.map((star) => (
        <motion.div
          key={star.id}
          className="absolute rounded-full bg-white"
          style={{
            left: `${star.x}%`,
            top: `${star.y}%`,
            width: star.size,
            height: star.size,
          }}
          animate={{
            opacity: [0.2, 0.8, 0.2],
            scale: [0.8, 1.2, 0.8],
          }}
          transition={{
            duration: star.duration,
            repeat: Number.POSITIVE_INFINITY,
            delay: star.delay,
          }}
        />
      ))}

      {/* Occasional shooting star */}
      <motion.div
        className="absolute w-20 h-0.5 bg-gradient-to-r from-cyan-400 to-transparent"
        initial={{ x: "100vw", y: "10vh", opacity: 0 }}
        animate={{
          x: ["-20vw"],
          y: ["60vh"],
          opacity: [0, 1, 1, 0],
        }}
        transition={{
          duration: 1.5,
          repeat: Number.POSITIVE_INFINITY,
          repeatDelay: 8,
        }}
      />
    </div>
  )
}
