"use client"

import { useState, useEffect } from "react"
import { BootSequence } from "@/components/boot-sequence"
import { CommandCenter } from "@/components/command-center"

export default function GodbrainQuantum() {
  const [isBooted, setIsBooted] = useState(false)
  const [bootProgress, setBootProgress] = useState(0)

  useEffect(() => {
    document.documentElement.classList.add("dark")
  }, [])

  if (!isBooted) {
    return <BootSequence onComplete={() => setIsBooted(true)} progress={bootProgress} setProgress={setBootProgress} />
  }

  return <CommandCenter />
}
