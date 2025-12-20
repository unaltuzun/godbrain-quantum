"use client"

import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { X } from "lucide-react"

const positions = [
  { symbol: "BTC/USD", side: "LONG", size: 2.45, entry: 43250, current: 44120, pnl: 2133.5 },
  { symbol: "ETH/USD", side: "LONG", size: 12.8, entry: 2280, current: 2340, pnl: 768.0 },
  { symbol: "AAPL", side: "SHORT", size: 500, entry: 178.5, current: 176.2, pnl: 1150.0 },
  { symbol: "TSLA", side: "LONG", size: 100, entry: 242.1, current: 248.5, pnl: 640.0 },
]

export function PositionsTable() {
  return (
    <Card className="p-4 md:p-6 bg-card border-border">
      <h3 className="text-base md:text-lg font-semibold mb-4">Live Positions</h3>

      <div className="overflow-x-auto -mx-4 md:mx-0">
        <div className="inline-block min-w-full align-middle">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                <th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground">Symbol</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground">Side</th>
                <th className="px-4 py-2 text-right text-xs font-medium text-muted-foreground">Size</th>
                <th className="px-4 py-2 text-right text-xs font-medium text-muted-foreground hidden sm:table-cell">
                  Entry
                </th>
                <th className="px-4 py-2 text-right text-xs font-medium text-muted-foreground">P&L</th>
                <th className="px-4 py-2 text-right text-xs font-medium text-muted-foreground"></th>
              </tr>
            </thead>
            <tbody>
              {positions.map((pos, index) => (
                <tr key={index} className="border-b border-border last:border-0">
                  <td className="px-4 py-3 text-sm font-medium">{pos.symbol}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`text-xs font-semibold px-2 py-1 rounded ${
                        pos.side === "LONG" ? "bg-gain/20 text-gain" : "bg-loss/20 text-loss"
                      }`}
                    >
                      {pos.side}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-right">{pos.size}</td>
                  <td className="px-4 py-3 text-sm text-right text-muted-foreground hidden sm:table-cell">
                    ${pos.entry.toFixed(2)}
                  </td>
                  <td
                    className={`px-4 py-3 text-sm font-semibold text-right ${pos.pnl >= 0 ? "text-gain" : "text-loss"}`}
                  >
                    {pos.pnl >= 0 ? "+" : ""}${pos.pnl.toFixed(2)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Button variant="ghost" size="icon" className="w-7 h-7 md:w-8 md:h-8">
                      <X className="w-4 h-4" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </Card>
  )
}
