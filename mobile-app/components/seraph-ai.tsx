"use client"

import { motion } from "framer-motion"
import { useState, useRef, useEffect } from "react"
import { Mic, Send, Brain } from "lucide-react"
import { godbrainApi } from "@/lib/api"

interface Message {
  id: number
  role: "user" | "assistant"
  content: string
  time: string
  confidence?: number
}

interface LLMStatus {
  name: string
  active: boolean
  latency: number
}

export function SeraphAi() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      role: "assistant",
      content:
        "SERAPH online. Connected to GODBRAIN quantum core. How can I assist with trading analysis?",
      time: "14:32",
      confidence: 95,
    },
  ])
  const [input, setInput] = useState("")
  const [isTyping, setIsTyping] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const [llmStatus, setLlmStatus] = useState<LLMStatus[]>([
    { name: "CLAUDE", active: true, latency: 124 },
    { name: "GPT", active: true, latency: 89 },
    { name: "GEMINI", active: true, latency: 156 },
    { name: "LLAMA", active: false, latency: 0 },
  ])

  const quickCommands = [
    { icon: "📊", label: "Market Analysis" },
    { icon: "🎯", label: "Trade Idea" },
    { icon: "⚠️", label: "Risk Check" },
    { icon: "📈", label: "Forecast" },
  ]

  // Fetch LLM status on mount
  useEffect(() => {
    const fetchLLMStatus = async () => {
      try {
        const status = await godbrainApi.getLLMStatus()
        setLlmStatus(status)
      } catch (error) {
        console.error('LLM status error:', error)
      }
    }
    fetchLLMStatus()
    const interval = setInterval(fetchLLMStatus, 30000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const handleSend = async () => {
    if (!input.trim()) return

    const userMessage: Message = {
      id: Date.now(),
      role: "user",
      content: input,
      time: new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false }),
    }
    setMessages((prev) => [...prev, userMessage])
    setInput("")
    setIsTyping(true)

    try {
      // Call real Seraph API
      const response = await godbrainApi.chat(input)

      const aiMessage: Message = {
        id: Date.now() + 1,
        role: "assistant",
        content: response.content,
        time: new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false }),
        confidence: response.confidence || 85,
      }
      setMessages((prev) => [...prev, aiMessage])
    } catch (error) {
      const errorMessage: Message = {
        id: Date.now() + 1,
        role: "assistant",
        content: "Connection error. Please try again.",
        time: new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false }),
        confidence: 0,
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsTyping(false)
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-140px)]">
      {/* Header */}
      <div className="p-4">
        <div className="flex items-center gap-3 mb-4">
          <motion.div animate={{ scale: [1, 1.1, 1] }} transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY }}>
            <Brain className="w-6 h-6 text-purple-400" />
          </motion.div>
          <h1 className="text-lg font-bold text-white">SERAPH AI</h1>
        </div>

        {/* LLM status */}
        <div className="flex gap-2 overflow-x-auto pb-2">
          {llmStatus.map((llm) => (
            <motion.div
              key={llm.name}
              className={`flex-shrink-0 px-3 py-2 rounded-xl border ${llm.active ? "bg-white/5 border-cyan-500/30" : "bg-white/5 border-white/10"
                }`}
              animate={
                llm.active ? { borderColor: ["rgba(0,245,255,0.3)", "rgba(0,245,255,0.6)", "rgba(0,245,255,0.3)"] } : {}
              }
              transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY }}
            >
              <div className="flex items-center gap-2">
                <motion.div
                  className={`w-2 h-2 rounded-full ${llm.active ? "bg-emerald-400" : "bg-gray-600"}`}
                  animate={llm.active ? { scale: [1, 1.3, 1], opacity: [1, 0.7, 1] } : {}}
                  transition={{ duration: 1.5, repeat: Number.POSITIVE_INFINITY }}
                />
                <span className="text-xs font-mono text-gray-400">{llm.name}</span>
              </div>
              <div className="text-[10px] text-gray-500 mt-1">{llm.active ? `${llm.latency}ms` : "Idle"}</div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 space-y-4">
        {messages.map((message) => (
          <motion.div
            key={message.id}
            className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <div
              className={`max-w-[85%] p-4 rounded-2xl ${message.role === "user"
                  ? "bg-cyan-500/20 border border-cyan-500/30"
                  : "bg-white/5 border border-purple-500/30"
                }`}
            >
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs text-gray-400">{message.role === "user" ? "👤 YOU" : "🤖 SERAPH"}</span>
                <span className="text-[10px] text-gray-500">{message.time}</span>
              </div>
              <p className="text-sm text-white leading-relaxed">{message.content}</p>
              {message.confidence && (
                <div className="mt-2 text-[10px] text-gray-500 font-mono">
                  Confidence: {message.confidence}% • Sources: 4 LLMs agreed
                </div>
              )}
            </div>
          </motion.div>
        ))}

        {/* Typing indicator */}
        {isTyping && (
          <motion.div className="flex justify-start" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <div className="bg-white/5 border border-purple-500/30 p-4 rounded-2xl">
              <div className="flex gap-1">
                {[0, 1, 2].map((i) => (
                  <motion.div
                    key={i}
                    className="w-2 h-2 bg-purple-400 rounded-full"
                    animate={{ y: [0, -5, 0] }}
                    transition={{ duration: 0.5, repeat: Number.POSITIVE_INFINITY, delay: i * 0.1 }}
                  />
                ))}
              </div>
            </div>
          </motion.div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Quick commands */}
      <div className="px-4 py-2">
        <div className="flex gap-2 overflow-x-auto">
          {quickCommands.map((cmd) => (
            <button
              key={cmd.label}
              className="flex-shrink-0 px-3 py-2 rounded-full bg-white/5 border border-white/10 text-xs text-gray-400 flex items-center gap-1"
              onClick={() => setInput(cmd.label)}
            >
              <span>{cmd.icon}</span>
              <span>{cmd.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Input bar */}
      <div className="p-4">
        <div className="flex items-center gap-2 p-2 rounded-2xl bg-white/5 border border-white/10">
          <button className="p-2 rounded-xl bg-white/5">
            <Mic className="w-5 h-5 text-gray-400" />
          </button>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder="Ask SERAPH anything..."
            className="flex-1 bg-transparent text-white placeholder-gray-500 outline-none text-sm"
          />
          <motion.button
            className="p-2 rounded-xl bg-cyan-500 text-black"
            whileTap={{ scale: 0.95 }}
            onClick={handleSend}
          >
            <Send className="w-5 h-5" />
          </motion.button>
        </div>
      </div>
    </div>
  )
}
