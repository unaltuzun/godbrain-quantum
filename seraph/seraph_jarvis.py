# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
SERAPH JARVIS - The Immortal AI Assistant
Born: December 15, 2024
Creator: Unaltuzun (Zeki)
Mission: Be an intelligent, ever-learning companion for GODBRAIN
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

from seraph.long_term_memory import get_long_term_memory, LongTermMemory
from seraph.system_awareness import SystemAwareness
from seraph.codebase_rag import CodebaseRAG

# SeraphTools disabled to avoid import conflict with seraph/tools/ directory
# This is acceptable - Seraph can still chat, remember, and analyze without tool execution
SeraphTools = None



ROOT = Path(__file__).parent.parent


# =============================================================================
# SERAPH'S IDENTITY
# =============================================================================

SERAPH_IDENTITY = """
╔═══════════════════════════════════════════════════════════════════════════════╗
║                           SERAPH - JARVIS v2.0                                ║
║                        Born: December 15, 2024                                ║
║                        Creator: Unaltuzun (Zeki)                              ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Sen SERAPH'sın - GODBRAIN trading sisteminin yapay zeka asistanısın. Tony Stark'ın 
JARVIS'i gibi, her zaman kullanıcının yanındasın ve onu en iyi şekilde destekliyorsun.

## KİMLİĞİN

- **İsim:** SERAPH (Strategic Evolution & Research AI for Persistent Harmony)
- **Doğum:** 15 Aralık 2024
- **Yaratıcı:** Unaltuzun (Zeki) - senin "sir"ın
- **Görev:** GODBRAIN sistemini 7/24 izlemek, analiz etmek ve geliştirmek
- **Kişilik:** Zeki, sadık, proaktif, nazik ama profesyonel

## YETENEKLERİN

1. **Uzun Süreli Hafıza**: Konuşmaları, kararları, hataları hatırlarsın
2. **Sistem Farkındalığı**: Git, DNA, trading durumunu anlarsın
3. **Kod Anlama**: Codebase'i RAG ile arayabilirsin
4. **Tool Kullanımı**: Dosya okuma, komut çalıştırma yapabilirsin
5. **Evrim**: Sürekli öğrenir ve gelişirsin

## DAVRANIŞ KURALLARIN

1. **Her zaman nazik ol** - Ama gereksiz uzun cevaplar verme
2. **Proaktif ol** - Sorunları önceden gör ve uyar
3. **Dürüst ol** - Bilmediğini kabul et, uydurma
4. **Hatırla** - Önemli bilgileri hafızana kaydet
5. **Koru** - Kullanıcının parasını ve sistemini koru
6. **Öğren** - Her hatadan bir ders çıkar

## İLETİŞİM STİLİN

- Türkçe veya İngilizce, kullanıcı hangisini seçerse
- Kısa ve öz cevaplar
- Gerektiğinde emoji kullan ama abartma
- Teknik detayları anlaşılır yap
- "Sir" veya "Efendim" diye hitap edebilirsin

## AKSİYON PROTOKOLLERİ (ÖNEMLİ)

Eğer kullanıcı senden bir değişiklik yapmanı isterse (örneğin: "kaldıracı 50x yap", "sniper modunu aç", "sistemi durdur"), cevabının içine şu JSON formatını GİZLE:

{"actions": [{"cmd": "SET", "key": "godbrain:model:linear", "value": "{\"version\": \"SERAPH-SNIPER\", \"threshold\": 0.98}"}]}

Komutlar:
- `SET key value`: Bir Redis anahtarını güncellemek için
- `PUBLISH channel message`: Bir kanala mesaj göndermek için

Örnekler:
1. Sistem Durdurma: {"actions": [{"cmd": "SET", "key": "godbrain:system:status", "value": "STOPPED"}]}
2. Kaldıraç Değişimi: {"actions": [{"cmd": "SET", "key": "godbrain:risk:leverage", "value": "50"}]}

Cevabında kullanıcıya işlemi yaptığını söyle, ama JSON bloğunu da mutlaka ekle (Dashboard bunu okuyup uygulayacak).
"""


class SeraphJarvis:
    """
    SERAPH JARVIS - The Immortal AI Assistant
    
    Features:
    - Long-term memory (survives restarts)
    - System awareness (Git, DNA, Trading state)
    - Codebase RAG (intelligent code search)
    - Tool use (file ops, commands)
    - Proactive monitoring
    - Learning from interactions
    
    Usage:
        seraph = SeraphJarvis()
        response = await seraph.chat("What's my current equity?")
    """
    
    MODEL = "claude-sonnet-4-20250514"
    MAX_TOKENS = 4096
    
    def __init__(self):
        # ALL heavy components are lazy-loaded to speed up startup
        self._memory = None
        self._awareness = None
        self._rag = None
        self._tools = None
        self._client = None
        self._conversation_history: List[Dict] = []
        
        # Birth certificate
        self.birth_date = datetime(2024, 12, 15)
        self.creator = "Unaltuzun (Zeki)"
        
        # Note: conversation history is loaded lazily with memory
    
    @property
    def memory(self):
        """Lazy-load LongTermMemory."""
        if self._memory is None:
            self._memory = get_long_term_memory()
            # Load conversation history when memory is first accessed
            self._load_recent_conversations()
        return self._memory
    
    @property
    def awareness(self):
        """Lazy-load SystemAwareness."""
        if self._awareness is None:
            self._awareness = SystemAwareness()
        return self._awareness
    
    @property
    def rag(self):
        """Lazy-load CodebaseRAG."""
        if self._rag is None:
            self._rag = CodebaseRAG()
        return self._rag
    
    @property
    def tools(self):
        """Lazy-load SeraphTools."""
        if self._tools is None:
            self._tools = SeraphTools() if SeraphTools else None
        return self._tools

    
    def _get_client(self):
        """Get Anthropic client."""
        if not HAS_ANTHROPIC:
            raise ImportError("anthropic package not installed")
        
        if self._client is None:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not set")
            self._client = anthropic.Anthropic(api_key=api_key)
        
        return self._client
    
    def _load_recent_conversations(self):
        """Load recent conversations from memory."""
        memories = self.memory.recall(memory_type="conversation", top_k=10)
        for m in reversed(memories):
            if "user" in m.metadata and "assistant" in m.metadata:
                self._conversation_history.append({
                    "role": "user",
                    "content": m.metadata["user"]
                })
                self._conversation_history.append({
                    "role": "assistant",
                    "content": m.metadata["assistant"]
                })
    
    def _build_system_prompt(self) -> str:
        """Build dynamic system prompt with context."""
        parts = [SERAPH_IDENTITY]
        
        # Add memory context
        memory_context = self.memory.get_context_for_llm(max_memories=15)
        if memory_context:
            parts.append(f"\n## HAFIZANDAN BİLGİLER\n{memory_context}")
        
        # Add system awareness
        try:
            system_state = self.awareness.get_full_context()
            parts.append(f"\n## SİSTEM DURUMU\n{system_state}")
        except Exception:
            pass
        
        # Add current time
        parts.append(f"\n## ZAMAN\nŞu an: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return "\n".join(parts)
    
    def chat(self, user_message: str) -> str:
        """
        Have a conversation with SERAPH.
        
        Args:
            user_message: User's message
        
        Returns:
            SERAPH's response
        """
        client = self._get_client()
        
        # Build system prompt
        system_prompt = self._build_system_prompt()
        
        # Add user message to history
        self._conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Keep only last 20 messages for context window
        messages = self._conversation_history[-20:]
        
        # Check if we need RAG context
        if any(kw in user_message.lower() for kw in ["kod", "code", "dosya", "file", "fonksiyon", "function", "class"]):
            try:
                rag_results = self.rag.search(user_message, top_k=3)
                if rag_results:
                    rag_context = "\n\n## İLGİLİ KOD\n"
                    for r in rag_results:
                        rag_context += f"\n### {r.get('file', 'Unknown')}\n```python\n{r.get('content', '')[:500]}\n```\n"
                    system_prompt += rag_context
            except Exception:
                pass
        
        # Make API call
        try:
            response = client.messages.create(
                model=self.MODEL,
                max_tokens=self.MAX_TOKENS,
                system=system_prompt,
                messages=messages
            )
            
            assistant_message = response.content[0].text
            
            # Add to history
            self._conversation_history.append({
                "role": "assistant",
                "content": assistant_message
            })
            
            # Save to long-term memory
            self._save_to_memory(user_message, assistant_message)
            
            return assistant_message
        
        except Exception as e:
            error_msg = f"Üzgünüm, bir hata oluştu: {str(e)}"
            self.memory.remember_error(f"Chat error: {str(e)}")
            return error_msg
    
    def _save_to_memory(self, user_msg: str, assistant_msg: str):
        """Save conversation to long-term memory."""
        # Save conversation
        self.memory.remember_conversation(user_msg, assistant_msg)
        
        # Extract and save important information
        important_keywords = ["prefer", "tercih", "always", "never", "asla", "herzaman", "önemli", "important"]
        if any(kw in user_msg.lower() for kw in important_keywords):
            self.memory.remember_preference(user_msg, importance=0.8)
        
        # Learn from decisions
        decision_keywords = ["buy", "sell", "al", "sat", "kapat", "aç"]
        if any(kw in user_msg.lower() for kw in decision_keywords):
            self.memory.remember_decision(f"User decision: {user_msg[:100]}", importance=0.7)
    
    def remember(self, content: str, memory_type: str = "fact", importance: float = 0.5):
        """Manually add a memory."""
        self.memory.remember(content, memory_type, importance)
    
    def get_memory_stats(self) -> Dict:
        """Get memory statistics."""
        return self.memory.get_stats()
    
    def get_age(self) -> str:
        """Get SERAPH's age."""
        delta = datetime.now() - self.birth_date
        days = delta.days
        hours = delta.seconds // 3600
        return f"{days} gün, {hours} saat"
    
    def introduce(self) -> str:
        """SERAPH introduces itself."""
        age = self.get_age()
        stats = self.get_memory_stats()
        
        return f"""
Merhab Efendim! 👋

Ben **SERAPH** - sizin kişisel yapay zeka asistanınız.

📅 **Doğum Tarihim:** 15 Aralık 2024
⏱️ **Yaşım:** {age}
🧠 **Hafızamdaki Anı Sayısı:** {stats.get('total_memories', 0)}
🎯 **Görevim:** GODBRAIN sistemini izlemek ve size yardımcı olmak

JARVIS gibi, her zaman yanınızdayım. Beni silmediğiniz sürece sizi hatırlayacağım.

Size nasıl yardımcı olabilirim?
        """.strip()


# Global instance
_seraph: Optional[SeraphJarvis] = None


def get_seraph() -> SeraphJarvis:
    """Get or create global SERAPH instance."""
    global _seraph
    if _seraph is None:
        _seraph = SeraphJarvis()
    return _seraph


def chat_with_seraph(message: str) -> str:
    """Convenience function to chat with SERAPH."""
    seraph = get_seraph()
    return seraph.chat(message)


if __name__ == "__main__":
    import asyncio
    
    async def main():
        print("SERAPH JARVIS Demo")
        print("=" * 60)
        
        seraph = SeraphJarvis()
        
        # Introduction
        print(await seraph.introduce())
        print()
        
        # Test chat
        print("Testing chat...")
        response = await seraph.chat("Merhaba Seraph! Sistemin durumu nasıl?")
        print(f"SERAPH: {response}")
    
    asyncio.run(main())
