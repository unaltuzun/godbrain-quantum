"use client"

import { useState, useMemo } from "react"
import { LineChart, Line, ResponsiveContainer, YAxis } from "recharts"

const TIME_RANGES = [
  { label: "1D", value: "1D" },
  { label: "1W", value: "1W" },
  { label: "1M", value: "1M" },
  { label: "3M", value: "3M" },
  { label: "1Y", value: "1Y" },
  { label: "ALL", value: "ALL" },
]

interface StockChartProps {
  symbol: string
  isPositive: boolean
}

// Generate realistic chart data
function generateChartData(timeRange: string, isPositive: boolean) {
  const points = timeRange === "1D" ? 100 : timeRange === "1W" ? 168 : timeRange === "1M" ? 240 : 365
  const data = []
  let basePrice = 100
  const volatility = 0.02
  const trend = isPositive ? 0.0005 : -0.0005

  for (let i = 0; i < points; i++) {
    const randomChange = (Math.random() - 0.5) * volatility
    basePrice = basePrice * (1 + randomChange + trend)
    data.push({
      time: i,
      value: basePrice,
    })
  }

  return data
}

export function StockChart({ symbol, isPositive }: StockChartProps) {
  const [selectedRange, setSelectedRange] = useState("1D")
  const chartData = useMemo(() => generateChartData(selectedRange, isPositive), [selectedRange, isPositive])

  const minValue = Math.min(...chartData.map((d) => d.value))
  const maxValue = Math.max(...chartData.map((d) => d.value))
  const padding = (maxValue - minValue) * 0.1

  return (
    <div className="flex flex-col h-full">
      {/* Chart */}
      <div className="flex-1 -mx-4">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 10, right: 0, left: 0, bottom: 10 }}>
            <defs>
              <linearGradient id={`gradient-${symbol}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={isPositive ? "#00C805" : "#FF3B30"} stopOpacity={0.2} />
                <stop offset="100%" stopColor={isPositive ? "#00C805" : "#FF3B30"} stopOpacity={0} />
              </linearGradient>
            </defs>
            <YAxis domain={[minValue - padding, maxValue + padding]} hide />
            <Line
              type="monotone"
              dataKey="value"
              stroke={isPositive ? "#00C805" : "#FF3B30"}
              strokeWidth={2}
              dot={false}
              fill={`url(#gradient-${symbol})`}
              animationDuration={300}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Time Range Selector */}
      <div className="flex justify-between items-center pt-4 pb-2">
        {TIME_RANGES.map((range) => (
          <button
            key={range.value}
            onClick={() => setSelectedRange(range.value)}
            className={`px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
              selectedRange === range.value
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {range.label}
          </button>
        ))}
      </div>
    </div>
  )
}
