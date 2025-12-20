"use client"

import { useEffect, useState } from "react"
import { Moon, Sun, Activity } from "lucide-react"
import { Button } from "@/components/ui/button"

interface HeaderProps {
  isDarkMode: boolean
  onToggleDarkMode: () => void
}

export function Header({ isDarkMode, onToggleDarkMode }: HeaderProps) {
  const [currentTime, setCurrentTime] = useState("")
  const [systemStatus, setSystemStatus] = useState<"operational" | "degraded" | "down">("operational")

  useEffect(() => {
    const updateTime = () => {
      const now = new Date()
      setCurrentTime(
        now.toLocaleTimeString("en-US", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          hour12: false,
        }),
      )
    }
    updateTime()
    const interval = setInterval(updateTime, 1000)
    return () => clearInterval(interval)
  }, [])

  const statusColors = {
    operational: "bg-gain",
    degraded: "bg-yellow-500",
    down: "bg-loss",
  }

  return (
    <header className="sticky top-0 z-50 bg-card border-b border-border">
      <div className="px-4 md:px-6 py-3 md:py-4 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 md:gap-4">
          <div className="flex items-center gap-2">
            <Activity className="w-6 h-6 md:w-7 md:h-7 text-blue-500" />
            <h1 className="text-lg md:text-xl font-bold bg-gradient-to-r from-blue-400 to-blue-600 bg-clip-text text-transparent">
              GODBRAIN QUANTUM
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-3 md:gap-4">
          <div className="hidden sm:flex items-center gap-2 text-sm md:text-base font-mono">
            <span className="text-muted-foreground">{currentTime}</span>
          </div>

          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 md:w-2.5 md:h-2.5 rounded-full ${statusColors[systemStatus]} animate-pulse`} />
            <span className="hidden sm:inline text-xs md:text-sm font-medium">
              {systemStatus === "operational" ? "Operational" : systemStatus === "degraded" ? "Degraded" : "Down"}
            </span>
          </div>

          <Button variant="ghost" size="icon" onClick={onToggleDarkMode} className="w-9 h-9 md:w-10 md:h-10">
            {isDarkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
          </Button>
        </div>
      </div>
    </header>
  )
}
