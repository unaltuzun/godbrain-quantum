"use client"

import { Card } from "@/components/ui/card"

const metrics = [
  { label: "Value at Risk (95%)", value: "$24,580", subtext: "1-day VaR" },
  { label: "Max Drawdown", value: "-8.4%", subtext: "Last 30 days" },
  { label: "Portfolio Exposure", value: "68%", subtext: "of total equity" },
]

export function RiskMetrics() {
  return (
    <Card className="p-4 md:p-6 bg-card border-border">
      <h3 className="text-base md:text-lg font-semibold mb-4">Risk Metrics</h3>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {metrics.map((metric, index) => (
          <div key={index} className="space-y-1">
            <p className="text-xs md:text-sm text-muted-foreground">{metric.label}</p>
            <p className="text-xl md:text-2xl font-bold">{metric.value}</p>
            <p className="text-xs text-muted-foreground">{metric.subtext}</p>
          </div>
        ))}
      </div>
    </Card>
  )
}
