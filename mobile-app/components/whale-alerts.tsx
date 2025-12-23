"use client"

import { Card } from "@/components/ui/card"
import { TrendingUp, TrendingDown, Clock } from "lucide-react"
import { useEffect, useState } from "react"
import { godbrainApi } from "@/lib/api"

export function WhaleAlerts() {
  const [alerts, setAlerts] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchAnomalies = async () => {
      try {
        const data = await godbrainApi.getAnomalies()
        setAlerts(data)
      } catch (e) {
        console.error(e)
      } finally {
        setLoading(false)
      }
    }
    fetchAnomalies()
    const interval = setInterval(fetchAnomalies, 30000)
    return () => clearInterval(interval)
  }, [])

  return (
    <Card className="p-4 md:p-6 bg-card border-border">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-base md:text-lg font-semibold">Market Intelligence</h3>
        {alerts.length > 0 && alerts[0].is_stale && (
          <span className="text-[10px] text-orange-500 flex items-center gap-1 animate-pulse">
            <Clock className="w-2 h-2" /> OBSERVATION ONLY (STALE)
          </span>
        )}
      </div>

      <div className="space-y-3">
        {alerts.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground text-sm font-mono leading-relaxed">
            {loading ? "SCANNING BLOOMBERG/ON-CHAIN..." : "NO RECENT WHALE ANOMALIES"}
          </div>
        ) : (
          alerts.map((alert) => (
            <div key={alert.id} className={`flex items-center gap-3 p-3 rounded-lg border border-border transition-all ${alert.is_stale ? 'opacity-40 grayscale' : 'bg-muted/50 hover:border-cyan-500/30'}`}>
              <div className={`p-2 rounded-lg ${(alert.type === "buy" || alert.type === "accumulation") ? "bg-emerald-500/20 text-emerald-500" : "bg-red-500/20 text-red-500"}`}>
                {(alert.type === "buy" || alert.type === "accumulation") ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-semibold text-sm">{alert.amount || alert.magnitude || "N/A"}</span>
                  <span className="text-xs font-medium text-blue-500">{alert.asset || alert.symbol || "CRYPTO"}</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span className="truncate max-w-[120px]">{alert.wallet || alert.description || "Unknown Source"}</span>
                  <span>•</span>
                  <span>{alert.age_hours ? `${alert.age_hours}h ago` : (alert.time || "N/A")}</span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </Card>
  )
}
