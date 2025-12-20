"use client"

import { TrendingUp, DollarSign, Target, Award } from "lucide-react"
import { Card } from "@/components/ui/card"

export function MetricsRow() {
  const metrics = [
    {
      icon: DollarSign,
      label: "Total Equity",
      value: "$1,247,891",
      change: "+3.24%",
      isPositive: true,
    },
    {
      icon: TrendingUp,
      label: "Daily P&L",
      value: "+$42,347",
      change: "+2.18%",
      isPositive: true,
    },
    {
      icon: Target,
      label: "Sharpe Ratio",
      value: "2.45",
      subtext: "Excellent",
      gauge: 2.45,
      maxGauge: 3,
    },
    {
      icon: Award,
      label: "VOLTRAN Score",
      value: "87",
      subtext: "Top 5%",
      badge: "Elite",
    },
  ]

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
      {metrics.map((metric, index) => {
        const Icon = metric.icon
        return (
          <Card key={index} className="p-4 md:p-6 bg-card border-border">
            <div className="flex items-start justify-between mb-3">
              <div className="p-2 rounded-lg bg-blue-500/10">
                <Icon className="w-4 h-4 md:w-5 md:h-5 text-blue-500" />
              </div>
              {metric.badge && (
                <span className="px-2 py-1 text-xs font-semibold bg-blue-500/20 text-blue-400 rounded">
                  {metric.badge}
                </span>
              )}
            </div>

            <div className="space-y-1">
              <p className="text-xs md:text-sm text-muted-foreground">{metric.label}</p>
              <p className="text-xl md:text-2xl font-bold">{metric.value}</p>

              {metric.change && (
                <p className={`text-xs md:text-sm font-medium ${metric.isPositive ? "text-gain" : "text-loss"}`}>
                  {metric.change}
                </p>
              )}

              {metric.subtext && <p className="text-xs text-muted-foreground">{metric.subtext}</p>}

              {metric.gauge !== undefined && (
                <div className="mt-2 w-full bg-muted rounded-full h-1.5">
                  <div
                    className="bg-blue-500 h-1.5 rounded-full transition-all"
                    style={{ width: `${(metric.gauge / metric.maxGauge!) * 100}%` }}
                  />
                </div>
              )}
            </div>
          </Card>
        )
      })}
    </div>
  )
}
