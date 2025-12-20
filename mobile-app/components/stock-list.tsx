"use client"

import { ChevronRight } from "lucide-react"

interface Stock {
  symbol: string
  name: string
  price: number
  change: number
  changePercent: number
}

interface StockListProps {
  stocks: Stock[]
  onSelectStock: (stock: Stock) => void
}

export function StockList({ stocks, onSelectStock }: StockListProps) {
  return (
    <div className="flex-1 overflow-y-auto">
      <div className="px-4 py-2">
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-2">Watchlist</h2>
      </div>
      <div className="divide-y divide-border">
        {stocks.map((stock) => (
          <button
            key={stock.symbol}
            onClick={() => onSelectStock(stock)}
            className="w-full px-4 py-4 flex items-center justify-between active:bg-muted/50 transition-colors"
          >
            <div className="flex-1 text-left">
              <div className="font-semibold text-base mb-0.5">{stock.symbol}</div>
              <div className="text-sm text-muted-foreground">{stock.name}</div>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-right">
                <div className="font-semibold text-base mb-0.5">${stock.price.toFixed(2)}</div>
                <div className={`text-sm font-medium ${stock.change >= 0 ? "text-gain" : "text-loss"}`}>
                  {stock.change >= 0 ? "+" : ""}${Math.abs(stock.change).toFixed(2)}
                </div>
              </div>
              <ChevronRight className="w-5 h-5 text-muted-foreground" />
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
