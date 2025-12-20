"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"

interface FeedItem {
  id: string
  type: "whale" | "sentiment" | "orderbook" | "system"
  message: string
  timestamp: Date
}

export function LiveFeed() {
  const [feed, setFeed] = useState<FeedItem[]>([
    { id: "1", type: "whale", message: "Large BTC buy detected: 234.5 BTC @ $94,320", timestamp: new Date() },
    { id: "2", type: "sentiment", message: "Market sentiment shifted to BULLISH (+12%)", timestamp: new Date() },
    { id: "3", type: "orderbook", message: "ETH imbalance: 67% buy pressure", timestamp: new Date() },
  ])
  const [isExpanded, setIsExpanded] = useState(false)

  useEffect(() => {
    const messages = [
      { type: "whale" as const, message: "🐋 Whale alert: 1.2M USDT moved to exchange" },
      { type: "sentiment" as const, message: "Fear & Greed index: 72 → 75 (Greed)" },
      { type: "orderbook" as const, message: "BTC order book: 58% buy wall at $94k" },
      { type: "system" as const, message: "⚙️ GODBRAIN model updated - v2.3.1" },
      { type: "whale" as const, message: "🐋 Large SOL accumulation detected" },
      { type: "sentiment" as const, message: "Social volume spike: +234% on $ETH" },
    ]

    const interval = setInterval(() => {
      const randomMessage = messages[Math.floor(Math.random() * messages.length)]
      const newItem: FeedItem = {
        id: Date.now().toString(),
        type: randomMessage.type,
        message: randomMessage.message,
        timestamp: new Date(),
      }
      setFeed((prev) => [newItem, ...prev].slice(0, 20))
    }, 5000)

    return () => clearInterval(interval)
  }, [])

  const getIcon = (type: string) => {
    switch (type) {
      case "whale":
        return "🐋"
      case "sentiment":
        return "📊"
      case "orderbook":
        return "📈"
      case "system":
        return "⚙️"
      default:
        return "•"
    }
  }

  const displayedFeed = isExpanded ? feed : feed.slice(0, 4)

  return (
    <Card className="bg-card border-border relative overflow-hidden">
      <div className="absolute inset-0 nasa-grid opacity-10 pointer-events-none" />

      <CardHeader className="flex flex-row items-center justify-between pb-3 relative z-10">
        <CardTitle className="text-base font-semibold flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-chart-1 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-chart-1"></span>
          </span>
          LIVE FEED
        </CardTitle>
        <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => setIsExpanded(!isExpanded)}>
          {isExpanded ? "Collapse" : "Expand"}
        </Button>
      </CardHeader>
      <CardContent className="relative z-10">
        <div className="space-y-2 max-h-[300px] overflow-y-auto custom-scrollbar">
          {displayedFeed.map((item, index) => (
            <div
              key={item.id}
              className="flex items-start gap-2 p-2 rounded-lg bg-muted/30 hover:bg-muted/50 transition-all duration-300 text-sm border border-transparent hover:border-chart-1/30 relative overflow-hidden animate-slide-in"
              style={{ animationDelay: `${index * 50}ms` }}
            >
              <div className="absolute inset-0 opacity-0 hover:opacity-100 transition-opacity">
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-chart-1/10 to-transparent animate-scan-horizontal" />
              </div>

              <span className="text-base flex-shrink-0 relative z-10">{getIcon(item.type)}</span>
              <div className="flex-1 min-w-0 relative z-10">
                <div className="text-xs text-foreground break-words font-mono">{item.message}</div>
                <div className="text-[10px] text-muted-foreground mt-1 flex items-center gap-1">
                  <span className="w-1 h-1 rounded-full bg-chart-1/50" />
                  {item.timestamp.toLocaleTimeString()}
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
