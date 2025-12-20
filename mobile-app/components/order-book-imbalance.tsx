"use client"

import { Card } from "@/components/ui/card"

const orderBookData = [
  { price: 44125, bids: 75, asks: 25 },
  { price: 44120, bids: 65, asks: 35 },
  { price: 44115, bids: 55, asks: 45 },
  { price: 44110, bids: 45, asks: 55 },
  { price: 44105, bids: 30, asks: 70 },
]

export function OrderBookImbalance() {
  return (
    <Card className="p-4 md:p-6 bg-card border-border">
      <h3 className="text-base md:text-lg font-semibold mb-4">Order Book Imbalance</h3>

      <div className="space-y-3">
        {orderBookData.map((level, index) => {
          const total = level.bids + level.asks
          const bidPercent = (level.bids / total) * 100
          const askPercent = (level.asks / total) * 100

          return (
            <div key={index} className="space-y-1">
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>${level.price}</span>
                <span>
                  {level.bids} / {level.asks}
                </span>
              </div>
              <div className="flex h-6 rounded overflow-hidden">
                <div className="bg-gain/30 flex items-center justify-start px-2" style={{ width: `${bidPercent}%` }}>
                  <span className="text-xs font-medium text-gain">{bidPercent.toFixed(0)}%</span>
                </div>
                <div className="bg-loss/30 flex items-center justify-end px-2" style={{ width: `${askPercent}%` }}>
                  <span className="text-xs font-medium text-loss">{askPercent.toFixed(0)}%</span>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </Card>
  )
}
