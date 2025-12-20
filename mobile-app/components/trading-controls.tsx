"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Slider } from "@/components/ui/slider"
import { Input } from "@/components/ui/input"

export function TradingControls() {
  const [leverage, setLeverage] = useState([5])
  const [positionSize, setPositionSize] = useState("1000")
  const [calculatedValue, setCalculatedValue] = useState(5000)

  const handleCalculate = () => {
    const size = Number.parseFloat(positionSize) || 0
    setCalculatedValue(size * leverage[0])
  }

  return (
    <Card className="bg-card border-border">
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-semibold">TRADING CONTROLS</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Leverage Slider */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Leverage</span>
            <span className="text-lg font-bold text-chart-1">{leverage[0]}x</span>
          </div>
          <Slider
            value={leverage}
            onValueChange={setLeverage}
            min={1}
            max={20}
            step={1}
            className="[&_[role=slider]]:h-5 [&_[role=slider]]:w-5"
          />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>1x</span>
            <span>5x</span>
            <span>10x</span>
            <span>15x</span>
            <span>20x</span>
          </div>
        </div>

        {/* Position Size Calculator */}
        <div className="space-y-3">
          <label className="text-sm text-muted-foreground">Position Size Calculator</label>
          <div className="flex gap-2">
            <Input
              type="number"
              value={positionSize}
              onChange={(e) => setPositionSize(e.target.value)}
              placeholder="Enter amount"
              className="flex-1"
            />
            <Button onClick={handleCalculate} className="px-6">
              Calculate
            </Button>
          </div>
          <div className="p-3 bg-muted/30 rounded-lg">
            <div className="text-xs text-muted-foreground">Total Exposure</div>
            <div className="text-2xl font-bold text-chart-1 tabular-nums">${calculatedValue.toLocaleString()}</div>
          </div>
        </div>

        {/* Quick Close Buttons */}
        <div className="space-y-2">
          <label className="text-sm text-muted-foreground">Quick Close Positions</label>
          <div className="grid grid-cols-2 gap-2">
            <Button variant="outline" className="w-full bg-transparent">
              Close BTC
            </Button>
            <Button variant="outline" className="w-full bg-transparent">
              Close ETH
            </Button>
            <Button variant="outline" className="w-full bg-transparent">
              Close SOL
            </Button>
            <Button variant="outline" className="w-full bg-transparent">
              Close All
            </Button>
          </div>
        </div>

        {/* Master Kill Switch */}
        <div className="pt-4 border-t border-border">
          <Button
            variant="destructive"
            className="w-full h-14 text-lg font-bold bg-loss hover:bg-loss/90 shadow-lg shadow-loss/20"
          >
            🚨 EMERGENCY KILL SWITCH
          </Button>
          <p className="text-xs text-muted-foreground text-center mt-2">Closes all positions and cancels all orders</p>
        </div>
      </CardContent>
    </Card>
  )
}
