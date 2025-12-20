"use client"

import { Card } from "@/components/ui/card"

export function SentimentGauge() {
  const sentiment = 42 // -100 to +100

  const getSentimentLabel = (value: number) => {
    if (value < -60) return "Extreme Fear"
    if (value < -20) return "Fear"
    if (value < 20) return "Neutral"
    if (value < 60) return "Greed"
    return "Extreme Greed"
  }

  const getSentimentColor = (value: number) => {
    if (value < -60) return "text-loss"
    if (value < -20) return "text-orange-500"
    if (value < 20) return "text-muted-foreground"
    if (value < 60) return "text-gain"
    return "text-gain"
  }

  const position = ((sentiment + 100) / 200) * 100

  return (
    <Card className="p-4 md:p-6 bg-card border-border">
      <h3 className="text-base md:text-lg font-semibold mb-4">Market Sentiment</h3>

      <div className="space-y-4">
        <div className="relative h-3 bg-gradient-to-r from-loss via-muted to-gain rounded-full">
          <div
            className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-5 h-5 bg-foreground rounded-full border-2 border-background shadow-lg transition-all"
            style={{ left: `${position}%` }}
          />
        </div>

        <div className="flex justify-between text-xs text-muted-foreground">
          <span>Extreme Fear</span>
          <span>Neutral</span>
          <span>Extreme Greed</span>
        </div>

        <div className="text-center">
          <div className="text-3xl md:text-4xl font-bold mb-1">{sentiment}</div>
          <div className={`text-sm md:text-base font-semibold ${getSentimentColor(sentiment)}`}>
            {getSentimentLabel(sentiment)}
          </div>
        </div>
      </div>
    </Card>
  )
}
