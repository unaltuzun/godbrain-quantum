"use client"

import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { XCircle, PauseCircle, AlertTriangle } from "lucide-react"

export function QuickActions() {
  return (
    <Card className="p-4 md:p-6 bg-card border-border">
      <h3 className="text-base md:text-lg font-semibold mb-4">Quick Actions</h3>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <Button variant="outline" className="h-auto py-3 px-4 flex flex-col items-center gap-2 bg-transparent">
          <XCircle className="w-5 h-5" />
          <span className="text-sm font-medium">Close All Positions</span>
        </Button>

        <Button variant="outline" className="h-auto py-3 px-4 flex flex-col items-center gap-2 bg-transparent">
          <PauseCircle className="w-5 h-5" />
          <span className="text-sm font-medium">Pause Trading</span>
        </Button>

        <Button
          variant="outline"
          className="h-auto py-3 px-4 flex flex-col items-center gap-2 border-loss text-loss hover:bg-loss/10 bg-transparent"
        >
          <AlertTriangle className="w-5 h-5" />
          <span className="text-sm font-medium">Emergency Stop</span>
        </Button>
      </div>
    </Card>
  )
}
