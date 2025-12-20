"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

interface LLMStatus {
  name: string
  model: string
  status: "active" | "idle" | "error"
  responseTime: number
  costToday: number
}

export function MultiLlmStatus() {
  const [llms, setLlms] = useState<LLMStatus[]>([
    { name: "Claude", model: "Sonnet 3.5", status: "active", responseTime: 842, costToday: 4.23 },
    { name: "GPT", model: "4o", status: "idle", responseTime: 1203, costToday: 2.87 },
    { name: "Gemini", model: "Pro", status: "idle", responseTime: 967, costToday: 1.45 },
    { name: "Llama", model: "3.1 405B", status: "active", responseTime: 1542, costToday: 0.89 },
  ])

  useEffect(() => {
    const interval = setInterval(() => {
      setLlms((prev) =>
        prev.map((llm) => ({
          ...llm,
          responseTime: llm.responseTime + Math.floor(Math.random() * 100 - 50),
          costToday: Number.parseFloat((llm.costToday + Math.random() * 0.05).toFixed(2)),
        })),
      )
    }, 3000)

    return () => clearInterval(interval)
  }, [])

  const getStatusColor = (status: string) => {
    switch (status) {
      case "active":
        return "bg-gain/20 text-gain border-gain/50"
      case "idle":
        return "bg-muted/20 text-muted-foreground border-muted"
      case "error":
        return "bg-loss/20 text-loss border-loss/50"
      default:
        return ""
    }
  }

  return (
    <Card className="bg-card border-border relative overflow-hidden">
      <div className="absolute inset-0 nasa-grid opacity-10 pointer-events-none" />

      <CardHeader className="pb-3 relative z-10">
        <CardTitle className="text-base font-semibold flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-chart-1 animate-pulse-glow" />
          MULTI-LLM STATUS
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 relative z-10">
        <div className="grid grid-cols-2 gap-3">
          {llms.map((llm) => (
            <div
              key={llm.name}
              className={`p-3 rounded-lg border transition-all duration-500 relative overflow-hidden ${
                llm.status === "active"
                  ? "border-chart-1 bg-chart-1/5 shadow-glow-blue animate-card-active"
                  : "border-border bg-muted/20"
              }`}
            >
              {llm.status === "active" && (
                <>
                  <div className="absolute inset-0 bg-gradient-to-br from-chart-1/10 to-transparent pointer-events-none" />
                  <div className="absolute top-0 right-0 w-16 h-16 bg-chart-1/20 rounded-full blur-2xl animate-pulse-slow" />
                </>
              )}

              <div className="flex items-start justify-between mb-2 relative z-10">
                <div>
                  <div className="font-semibold text-sm flex items-center gap-1.5">
                    {llm.status === "active" && <span className="w-1.5 h-1.5 rounded-full bg-gain animate-pulse" />}
                    {llm.name}
                  </div>
                  <div className="text-xs text-muted-foreground font-mono">{llm.model}</div>
                </div>
                <Badge variant="outline" className={`text-[10px] px-1.5 py-0.5 ${getStatusColor(llm.status)}`}>
                  {llm.status.toUpperCase()}
                </Badge>
              </div>

              <div className="space-y-1.5 text-xs relative z-10">
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">Response</span>
                  <div className="flex items-center gap-1">
                    <div className="w-8 h-1 bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full bg-chart-1 rounded-full transition-all duration-1000"
                        style={{ width: `${Math.min(((2000 - llm.responseTime) / 2000) * 100, 100)}%` }}
                      />
                    </div>
                    <span className="font-semibold tabular-nums min-w-[45px] text-right">{llm.responseTime}ms</span>
                  </div>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Cost Today</span>
                  <span className="font-semibold tabular-nums text-chart-1">${llm.costToday}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
