"use client"

import { Card } from "@/components/ui/card"
import { TrendingUp, TrendingDown } from "lucide-react"

const alerts = [
  {
    id: 1,
    type: "buy",
    amount: "$12.5M",
    asset: "BTC",
    time: "2m ago",
    wallet: "0x742d...4a8f",
  },
  {
    id: 2,
    type: "sell",
    amount: "$8.2M",
    asset: "ETH",
    time: "15m ago",
    wallet: "0x9a3c...7e2d",
  },
  {
    id: 3,
    type: "buy",
    amount: "$5.8M",
    asset: "BTC",
    time: "32m ago",
    wallet: "0x1f8b...9c4a",
  },
]

export function WhaleAlerts() {
  return (
    <Card className="p-4 md:p-6 bg-card border-border">
      <h3 className="text-base md:text-lg font-semibold mb-4">On-Chain Whale Alerts</h3>

      <div className="space-y-3">
        {alerts.map((alert) => (
          <div key={alert.id} className="flex items-center gap-3 p-3 rounded-lg bg-muted/50 border border-border">
            <div className={`p-2 rounded-lg ${alert.type === "buy" ? "bg-gain/20 text-gain" : "bg-loss/20 text-loss"}`}>
              {alert.type === "buy" ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="font-semibold text-sm">{alert.amount}</span>
                <span className="text-xs font-medium text-blue-500">{alert.asset}</span>
              </div>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span className="truncate">{alert.wallet}</span>
                <span>•</span>
                <span>{alert.time}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  )
}
