"use client"

import { useState } from "react"
import { Card } from "@/components/ui/card"

interface Trade {
  id: string
  symbol: string
  side: "BUY" | "SELL"
  price: number
  size: number
  time: string
}

export function RecentTrades() {
  const [trades, setTrades] = useState<Trade[]>([
    { id: "1", symbol: "BTC/USD", side: "BUY", price: 44120, size: 0.25, time: "14:32:45" },
    { id: "2", symbol: "ETH/USD", side: "SELL", price: 2340, size: 1.5, time: "14:32:38" },
    { id: "3", symbol: "AAPL", side: "BUY", price: 176.2, size: 100, time: "14:32:12" },
    { id: "4", symbol: "TSLA", side: "BUY", price: 248.5, size: 50, time: "14:31:56" },
    { id: "5", symbol: "BTC/USD", side: "SELL", price: 44115, size: 0.15, time: "14:31:42" },
  ])

  return (
    <Card className="p-4 md:p-6 bg-card border-border">
      <h3 className="text-base md:text-lg font-semibold mb-4">Recent Trades</h3>

      <div className="space-y-2 max-h-[240px] overflow-y-auto">
        {trades.map((trade) => (
          <div key={trade.id} className="flex items-center justify-between py-2 border-b border-border last:border-0">
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">{trade.symbol}</span>
                <span
                  className={`text-xs font-semibold px-1.5 py-0.5 rounded ${
                    trade.side === "BUY" ? "bg-gain/20 text-gain" : "bg-loss/20 text-loss"
                  }`}
                >
                  {trade.side}
                </span>
              </div>
              <div className="text-xs text-muted-foreground mt-0.5">{trade.time}</div>
            </div>
            <div className="text-right">
              <div className="text-sm font-semibold">${trade.price.toFixed(2)}</div>
              <div className="text-xs text-muted-foreground">{trade.size}</div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  )
}
