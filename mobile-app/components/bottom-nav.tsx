"use client"

import { Button } from "@/components/ui/button"

interface BottomNavProps {
  activeTab: string
  onTabChange: (tab: string) => void
}

export function BottomNav({ activeTab, onTabChange }: BottomNavProps) {
  const tabs = [
    { id: "dashboard", label: "Dashboard", icon: "📊" },
    { id: "positions", label: "Positions", icon: "💼" },
    { id: "signals", label: "Signals", icon: "📡" },
    { id: "settings", label: "Settings", icon: "⚙️" },
  ]

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-card border-t border-border md:hidden z-50">
      <div className="grid grid-cols-4 gap-1 p-2">
        {tabs.map((tab) => (
          <Button
            key={tab.id}
            variant="ghost"
            className={`flex flex-col items-center gap-1 h-auto py-2 ${
              activeTab === tab.id ? "bg-chart-1/20 text-chart-1" : "text-muted-foreground"
            }`}
            onClick={() => onTabChange(tab.id)}
          >
            <span className="text-xl">{tab.icon}</span>
            <span className="text-xs font-medium">{tab.label}</span>
          </Button>
        ))}
      </div>
    </nav>
  )
}
