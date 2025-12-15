# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
GODBRAIN Intent Classifier for Seraph Router
Smart query classification for optimal Local/Cloud LLM routing.
═══════════════════════════════════════════════════════════════════════════════
"""

import re
import math
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class QueryIntent(Enum):
    """Query intent categories."""
    GREETING = "greeting"           # Simple greetings
    STATUS = "status"               # System/trading status queries
    ANALYSIS = "analysis"           # Market/performance analysis
    TRADING = "trading"             # Trade execution requests
    CODE = "code"                   # Code-related queries
    STRATEGY = "strategy"           # Strategy/DNA related
    EMERGENCY = "emergency"         # Urgent/panic situations
    GENERAL = "general"             # General questions


class QueryComplexity(Enum):
    """Query complexity levels."""
    TRIVIAL = 1     # Can be answered with simple lookup
    SIMPLE = 2      # Requires basic reasoning
    MODERATE = 3    # Requires context understanding
    COMPLEX = 4     # Requires deep analysis
    CRITICAL = 5    # Requires maximum accuracy


@dataclass
class IntentResult:
    """Result of intent classification."""
    intent: QueryIntent
    complexity: QueryComplexity
    confidence: float  # 0-1
    keywords: List[str]
    suggested_router: str  # "local" or "cloud"
    reasoning: str
    
    @property
    def should_use_cloud(self) -> bool:
        return self.suggested_router == "cloud"
    
    @property
    def should_use_local(self) -> bool:
        return self.suggested_router == "local"


class IntentClassifier:
    """
    Intent classifier for optimal LLM routing.
    
    Analyzes queries to determine:
    - Intent category (greeting, trading, code, etc.)
    - Complexity level (trivial to critical)
    - Suggested router (local for simple, cloud for complex)
    
    Maintains 95%+ cost savings while maximizing response quality.
    
    Usage:
        classifier = IntentClassifier()
        result = classifier.classify("What's the current DOGE price?")
        
        if result.should_use_cloud:
            response = cloud_llm.generate(query)
        else:
            response = local_llm.generate(query)
    """
    
    # Keyword patterns for each intent
    INTENT_PATTERNS: Dict[QueryIntent, List[str]] = {
        QueryIntent.GREETING: [
            r"^(hi|hello|hey|merhaba|selam|yo)\b",
            r"^good (morning|afternoon|evening)",
            r"^what'?s up",
        ],
        QueryIntent.STATUS: [
            r"\b(status|durum|state|health)\b",
            r"\b(how (is|are)|nasıl)\b",
            r"\b(running|çalışıyor|active)\b",
            r"\b(equity|balance|bakiye)\b",
            r"\b(position|pozisyon)\b",
        ],
        QueryIntent.ANALYSIS: [
            r"\b(analyze|analiz|analysis)\b",
            r"\b(performance|performans)\b",
            r"\b(compare|karşılaştır)\b",
            r"\b(trend|pattern|desen)\b",
            r"\b(sharpe|drawdown|pnl)\b",
            r"\b(backtest|monte carlo)\b",
        ],
        QueryIntent.TRADING: [
            r"\b(buy|sell|trade|long|short)\b",
            r"\b(al|sat|işlem)\b",
            r"\b(execute|order|emir)\b",
            r"\b(leverage|kaldıraç)\b",
            r"\b(entry|exit|giriş|çıkış)\b",
        ],
        QueryIntent.CODE: [
            r"\b(code|kod|function|class|module)\b",
            r"\b(fix|modify|change|değiştir)\b",
            r"\b(implement|ekle|add)\b",
            r"\b(bug|error|hata)\b",
            r"\b(file|dosya|\.py)\b",
        ],
        QueryIntent.STRATEGY: [
            r"\b(dna|genetics|genetik)\b",
            r"\b(strategy|strateji)\b",
            r"\b(evolution|evrim)\b",
            r"\b(fitness|parameter|parametre)\b",
            r"\b(optimize|optimizasyon)\b",
        ],
        QueryIntent.EMERGENCY: [
            r"\b(panic|panik|emergency|acil)\b",
            r"\b(stop|dur|halt)\b",
            r"\b(urgent|kritik|critical)\b",
            r"\b(loss|kayıp|crash|çöküş)\b",
            r"\b(all|hepsi|everything)\b.*(close|kapat)",
        ],
    }
    
    # Complexity indicators
    COMPLEXITY_BOOSTERS = [
        (r"\b(why|neden|how|nasıl)\b.*\?", 1),  # Questions add complexity
        (r"\b(analyze|analiz|compare|karşılaştır)\b", 1),
        (r"\b(optimize|improve|geliştir)\b", 1),
        (r"\b(because|çünkü|since|therefore)\b", 1),
        (r"\b(if|else|when|while)\b", 1),
        (r"\d{4,}", 1),  # Long numbers (timestamps, IDs)
        (r"\b(multiple|several|all|tüm|hepsi)\b", 1),
    ]
    
    COMPLEXITY_REDUCERS = [
        (r"^\w+ ?\?$", -2),  # Single word questions
        (r"^(yes|no|evet|hayır)", -2),
        (r"^(ok|okay|tamam)", -2),
    ]
    
    # Router rules
    ALWAYS_CLOUD = [QueryIntent.TRADING, QueryIntent.EMERGENCY, QueryIntent.CODE]
    ALWAYS_LOCAL = [QueryIntent.GREETING]
    
    def __init__(self):
        self._cache: Dict[str, IntentResult] = {}
        self._max_cache = 100
    
    def classify(self, query: str) -> IntentResult:
        """
        Classify a query's intent and complexity.
        
        Returns IntentResult with routing suggestion.
        """
        # Check cache
        cache_key = query.lower().strip()[:100]
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        query_lower = query.lower().strip()
        
        # Detect intent
        intent, intent_confidence, keywords = self._detect_intent(query_lower)
        
        # Calculate complexity
        complexity = self._calculate_complexity(query_lower, intent)
        
        # Determine router
        router, reasoning = self._determine_router(intent, complexity, query_lower)
        
        result = IntentResult(
            intent=intent,
            complexity=complexity,
            confidence=intent_confidence,
            keywords=keywords,
            suggested_router=router,
            reasoning=reasoning
        )
        
        # Cache result
        if len(self._cache) >= self._max_cache:
            self._cache.clear()
        self._cache[cache_key] = result
        
        return result
    
    def _detect_intent(self, query: str) -> Tuple[QueryIntent, float, List[str]]:
        """Detect query intent using pattern matching."""
        scores: Dict[QueryIntent, Tuple[float, List[str]]] = {}
        
        for intent, patterns in self.INTENT_PATTERNS.items():
            matched_keywords = []
            score = 0
            
            for pattern in patterns:
                matches = re.findall(pattern, query, re.IGNORECASE)
                if matches:
                    score += len(matches)
                    if isinstance(matches[0], tuple):
                        matched_keywords.extend([m for m in matches[0] if m])
                    else:
                        matched_keywords.extend(matches)
            
            if score > 0:
                scores[intent] = (score, matched_keywords)
        
        if not scores:
            return QueryIntent.GENERAL, 0.5, []
        
        # Find highest scoring intent
        best_intent = max(scores.keys(), key=lambda i: scores[i][0])
        best_score, keywords = scores[best_intent]
        
        # Normalize confidence
        confidence = min(1.0, best_score / 3)
        
        return best_intent, confidence, keywords
    
    def _calculate_complexity(self, query: str, intent: QueryIntent) -> QueryComplexity:
        """Calculate query complexity."""
        # Base complexity by intent
        base_complexity = {
            QueryIntent.GREETING: 1,
            QueryIntent.STATUS: 2,
            QueryIntent.GENERAL: 2,
            QueryIntent.ANALYSIS: 3,
            QueryIntent.STRATEGY: 3,
            QueryIntent.CODE: 4,
            QueryIntent.TRADING: 4,
            QueryIntent.EMERGENCY: 5,
        }
        
        score = base_complexity.get(intent, 2)
        
        # Apply boosters
        for pattern, boost in self.COMPLEXITY_BOOSTERS:
            if re.search(pattern, query, re.IGNORECASE):
                score += boost
        
        # Apply reducers
        for pattern, reduction in self.COMPLEXITY_REDUCERS:
            if re.search(pattern, query, re.IGNORECASE):
                score += reduction  # reduction is negative
        
        # Length factor
        words = len(query.split())
        if words > 30:
            score += 1
        elif words < 5:
            score -= 1
        
        # Clamp to valid range
        score = max(1, min(5, score))
        
        return QueryComplexity(score)
    
    def _determine_router(
        self,
        intent: QueryIntent,
        complexity: QueryComplexity,
        query: str
    ) -> Tuple[str, str]:
        """Determine which router to use."""
        
        # Emergency always cloud
        if intent in self.ALWAYS_CLOUD:
            return "cloud", f"{intent.value} intent requires cloud for accuracy"
        
        # Greetings always local
        if intent in self.ALWAYS_LOCAL:
            return "local", f"{intent.value} is simple, local is sufficient"
        
        # Complexity-based routing
        if complexity.value >= 4:
            return "cloud", f"Complexity {complexity.value}/5 requires cloud processing"
        
        if complexity.value <= 2:
            return "local", f"Complexity {complexity.value}/5 is suitable for local"
        
        # Moderate complexity - check for specific patterns
        # If query mentions money/trading keywords, use cloud
        money_pattern = r"\b(\$|usd|usdt|btc|eth|profit|loss)\b"
        if re.search(money_pattern, query, re.IGNORECASE):
            return "cloud", "Financial context detected, using cloud for accuracy"
        
        # Default moderate to local (cost optimization)
        return "local", f"Moderate complexity ({complexity.value}/5), local preferred for cost"
    
    def get_stats(self) -> Dict:
        """Get classifier statistics."""
        return {
            "cache_size": len(self._cache),
            "intents_cached": {
                intent.value: sum(1 for r in self._cache.values() if r.intent == intent)
                for intent in QueryIntent
            }
        }


# Global instance
_classifier: Optional[IntentClassifier] = None


def get_intent_classifier() -> IntentClassifier:
    """Get or create global classifier instance."""
    global _classifier
    if _classifier is None:
        _classifier = IntentClassifier()
    return _classifier


def classify_query(query: str) -> IntentResult:
    """Convenience function to classify a query."""
    return get_intent_classifier().classify(query)


if __name__ == "__main__":
    print("Intent Classifier Demo")
    print("=" * 60)
    
    classifier = IntentClassifier()
    
    test_queries = [
        "Merhaba!",
        "What's the current equity?",
        "Analyze DOGE performance over last 7 days",
        "BUY 500 USDT worth of DOGE at market price",
        "Fix the bug in circuit_breaker.py",
        "What's the current DNA fitness?",
        "PANIC! Close all positions immediately!",
        "How's the weather?",
        "Compare current strategy with the previous generation",
        "Why did the sharpe ratio drop?",
    ]
    
    print(f"\n{'Query':<50} {'Intent':<12} {'Cmplx':<8} {'Router':<8}")
    print("-" * 80)
    
    for query in test_queries:
        result = classifier.classify(query)
        print(f"{query[:48]:<50} {result.intent.value:<12} {result.complexity.value:<8} {result.suggested_router:<8}")
    
    print(f"\nClassifier Stats: {classifier.get_stats()}")
