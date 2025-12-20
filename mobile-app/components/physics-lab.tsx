"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

export function PhysicsLab() {
  const [dnaCount, setDnaCount] = useState(147523)
  const [showAnomaly, setShowAnomaly] = useState(false)
  const [scanProgress, setScanProgress] = useState(0)

  useEffect(() => {
    const interval = setInterval(() => {
      setDnaCount((prev) => prev + Math.floor(Math.random() * 10))

      // Random anomaly alert (5% chance)
      if (Math.random() > 0.95) {
        setShowAnomaly(true)
        setTimeout(() => setShowAnomaly(false), 5000)
      }
    }, 2000)

    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    const scanInterval = setInterval(() => {
      setScanProgress((prev) => (prev + 1) % 100)
    }, 30)
    return () => clearInterval(scanInterval)
  }, [])

  const metrics = [
    { label: "f_stab", value: 0.847, data: [0.82, 0.83, 0.85, 0.84, 0.847] },
    { label: "f_energy", value: -12.4, data: [-15.2, -14.1, -13.5, -12.8, -12.4] },
  ]

  return (
    <Card className="bg-card border-border relative overflow-hidden">
      <div className="absolute inset-0 nasa-grid opacity-20 pointer-events-none" />
      <div
        className="absolute inset-0 nasa-scan pointer-events-none"
        style={{ transform: `translateY(${scanProgress}%)` }}
      />

      <CardHeader className="flex flex-row items-center justify-between pb-2 relative z-10">
        <CardTitle className="text-base font-semibold flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-chart-1 animate-pulse-glow" />
          PHYSICS LAB
        </CardTitle>
        <Badge variant="outline" className="bg-chart-1/20 text-chart-1 border-chart-1/50 animate-pulse-border">
          ACTIVE
        </Badge>
      </CardHeader>
      <CardContent className="space-y-4 relative z-10">
        {showAnomaly && (
          <div className="bg-loss/20 border border-loss/50 rounded-lg p-3 animate-alert-flash">
            <div className="flex items-center gap-2 text-loss text-sm font-semibold">
              <span className="text-lg animate-bounce">⚠️</span>
              ANOMALY DETECTED - Lineage 7 divergence
            </div>
          </div>
        )}

        <div className="space-y-3">
          <div className="flex items-center justify-between p-3 rounded-lg bg-chart-1/5 border border-chart-1/30 relative overflow-hidden">
            <div className="absolute inset-0 holographic-shimmer pointer-events-none" />
            <div className="relative z-10">
              <span className="text-sm text-muted-foreground block mb-1">DNA Generations</span>
              <span className="text-xs text-chart-1 font-mono">LINEAGE EVOLUTION ACTIVE</span>
            </div>
            <span className="text-3xl font-bold text-chart-1 tabular-nums tracking-tight relative z-10 animate-count-up">
              {dnaCount.toLocaleString()}
            </span>
          </div>

          {metrics.map((metric) => (
            <div
              key={metric.label}
              className="space-y-2 p-3 rounded-lg bg-muted/20 border border-border/50 relative overflow-hidden"
            >
              <div className="absolute top-0 right-0 w-24 h-24 bg-chart-1/5 rounded-full blur-2xl animate-pulse-slow" />

              <div className="flex items-center justify-between relative z-10">
                <span className="text-sm text-muted-foreground font-mono">{metric.label}</span>
                <span className="text-sm font-semibold tabular-nums text-chart-1">{metric.value.toFixed(3)}</span>
              </div>

              <div className="flex items-end gap-1 h-12 relative">
                {metric.data.map((val, idx) => {
                  const height = Math.abs((val / Math.max(...metric.data.map(Math.abs))) * 100)
                  const isLatest = idx === metric.data.length - 1
                  return (
                    <div key={idx} className="flex-1 relative group">
                      <div
                        className={`w-full bg-chart-1/40 rounded-sm transition-all duration-500 ${
                          isLatest ? "animate-bar-pulse shadow-glow-blue" : ""
                        }`}
                        style={{ height: `${height}%` }}
                      />
                      {isLatest && (
                        <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-1 h-1 bg-chart-1 rounded-full animate-ping" />
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          ))}

          <div className="pt-2 border-t border-border">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground flex items-center gap-2">
                <span className="relative w-3 h-3">
                  <span className="absolute inset-0 border-2 border-chart-1 rounded-full animate-orbit" />
                  <span className="absolute inset-1 bg-chart-1 rounded-full" />
                </span>
                Lineage Depth
              </span>
              <div className="flex items-center gap-2">
                <div className="w-24 h-2 bg-muted rounded-full overflow-hidden relative">
                  <div
                    className="h-full bg-gradient-to-r from-chart-1/50 via-chart-1 to-chart-1/50 rounded-full animate-progress-glow"
                    style={{ width: "73%" }}
                  />
                </div>
                <span className="text-sm font-semibold tabular-nums text-chart-1">L7/10</span>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
