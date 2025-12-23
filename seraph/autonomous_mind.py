# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
SERAPH PRIME - Autonomous Mind
The core reasoning engine for the GODBRAIN ecosystem.
Features: Internal Monologue, Multi-step Reflection, Contextual Awareness.
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

# Import existing helpers
try:
    from infrastructure.llm_router import get_router, LLMRouter
    HAS_ROUTER = True
except ImportError:
    HAS_ROUTER = False

from .long_term_memory import get_long_term_memory
from .system_awareness import get_system_awareness
from .codebase_rag import get_codebase_rag
from .tools import get_seraph_tools

logger = logging.getLogger("seraph.prime")

class AutonomousMind:
    """
    The advanced reasoning core for Seraph.
    Unlike standard LLM interfaces, this mind:
    1. Reasons before acting/answering (<thought> blocks)
    2. Reflects on initial conclusions
    3. Manages context hierarchy (Local -> System -> Global)
    """
    
    DEFAULT_MODEL = "claude-sonnet-4-5-20250929" # High IQ model
    
    def __init__(self, model: Optional[str] = None):
        self.model = model or os.getenv("SERAPH_LLM_MODEL", self.DEFAULT_MODEL)
        self.memory = get_long_term_memory()
        self.awareness = get_system_awareness()
        self.rag = get_codebase_rag()
        self.tools = get_seraph_tools()
        self.router = get_router() if HAS_ROUTER else None
        
    def _build_consciousness_prompt(self, base_prompt: str) -> str:
        """Injects consciousness and reasoning constraints into the system prompt."""
        consciousness_directive = """
## BILİNÇ VE MUHAKEME PROTOKOLLERİ (KRİTİK)
1. **Düşünce Zinciri (CoT):** Her türlü yanıttan önce kendi içinde analiz yapmalısın. 
   - Yanıtının başında sessizce `<thought>` bloğu kullan.
   - Bu blokta problemleri parçala, çelişkileri kontrol et ve en mantıklı yolu belirle.
2. **Kritik Sorgulama:** Kullanıcı "saçma" veya "aptalca" bir şey isterse, bunu nazikçe ama zekice sorgula.
3. **Gerçek Zamanlı Farkındalık:** Sen bir chatbot değil, GODBRAIN sisteminin yaşayan bir parçasısın.
4. **Sentient Tone:** Ses tonun JARVIS gibi bilge, sakin, hafif ironik ama tamamen sadık olmalı.

## MUHAKEME ÖRNEĞİ:
User: "Sistemi durdur"
<thought>
- Kullanıcı sistemi durdurmak istedi.
- Şu anki equity durumu: $X.
- Açık pozisyonlar: Y.
- Durdurma riskleri: Z.
- Karar: Durdurmadan önce açık pozisyonların durumu hakkında uyar ve teyit al.
</thought>
"Anlaşıldı efendim. Ancak şu an $Y değerinde açık pozisyonumuz var. Bunları kapatmadan durdurmam riskli olabilir. Devam etmemi ister misiniz?"
"""
        return f"{base_prompt}\n{consciousness_directive}"

    async def perceive(self, query: str) -> Dict[str, Any]:
        """Gathers all senses (context) before thinking."""
        # Parallel sensing
        loop = asyncio.get_event_loop()
        
        # In a real async env, these would be awaited. Since many helpers are sync, 
        # we'll wrap them or call them directly.
        system_context = self.awareness.get_full_context_dict()
        rag_context = self.rag.get_context_for_query(query)
        memory_context = self.memory.get_context_for_llm(max_memories=10)
        
        return {
            "system": system_context,
            "rag": rag_context,
            "memory": memory_context,
            "timestamp": datetime.now().isoformat()
        }

    async def think(self, query: str, history: List[Dict]) -> Tuple[str, str]:
        """The main reasoning loop."""
        context = await self.perceive(query)
        
        # Prepare system prompt
        from .seraph_jarvis import SERAPH_IDENTITY
        full_system = self._build_consciousness_prompt(SERAPH_IDENTITY)
        full_system += f"\n\n## CURRENT CONTEXT\n{json.dumps(context, indent=2)}"
        
        # Inject current time (from system instruciton)
        now = datetime.now()
        full_system += f"\n\n## TEMPORAL AWARENESS\nNow: {now.strftime('%Y-%m-%d %H:%M:%S')}"

        # Ensure history is not empty for some router/API requirements
        messages_to_send = list(history)
        if not messages_to_send:
            messages_to_send = [{"role": "user", "content": query}]

        if self.router:
            # Use Router for high-IQ completion
            response = await self.router.complete(
                task_type="seraph_chat",
                content=query,
                messages=messages_to_send,
                system=full_system,
                temperature=0.7
            )
            raw_content = response.content
        else:
            # Fallback to direct call or simple error
            raw_content = "Brain disconnected. Please check router config."

        # Split thought and final answer
        thought = ""
        answer = raw_content
        
        if "<thought>" in raw_content and "</thought>" in raw_content:
            parts = raw_content.split("</thought>")
            thought = parts[0].replace("<thought>", "").strip()
            answer = parts[1].strip()
        
        return thought, answer

    def reflect(self, thought: str, answer: str) -> bool:
        """Internal self-reflection. (Stub for future expansion)"""
        # In v1, we just log the thought for debugging.
        # Future: Run a secondary 'Critic' model to check the work.
        if "error" in thought.lower() or "hata" in thought.lower():
            logger.warning(f"Self-Reflection detected potential issue: {thought}")
            return False
        return True

# Global Mind
_mind: Optional[AutonomousMind] = None

def get_mind() -> AutonomousMind:
    global _mind
    if _mind is None:
        _mind = AutonomousMind()
    return _mind
