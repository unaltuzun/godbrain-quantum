"use client"

import { Card } from "@/components/ui/card"

const signals = [
  { label: "Technical", strength: 75, color: "bg-blue-500" },
  { label: "Sentiment", strength: 58, color: "bg-purple-500" },
  { label: "On-chain", strength: 82, color: "bg-cyan-500" },
  { label: "Order Flow", strength: 68, color: "bg-teal-500" },
]

export function SignalBars() {
  return (
    <Card className="p-4 md:p-6 bg-card border-border">
      <h3 className="text-base md:text-lg font-semibold mb-4">Signal Strength</h3>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {signals.map((signal, index) => (
          <div key={index} className="space-y-2">
            <div className="flex justify-between items-end mb-1">
              <span className="text-xs md:text-sm font-medium">{signal.label}</span>
              <span className="text-lg md:text-xl font-bold">{signal.strength}</span>
            </div>
            <div className="h-2 bg-muted rounded-full overflow-hidden">
              <div
                className={`h-full ${signal.color} transition-all rounded-full`}
                style={{ width: `${signal.strength}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </Card>
  )
}
