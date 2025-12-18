# -*- coding: utf-8 -*-
"""
GODBRAIN ALPHA - Sentiment Analysis
Twitter, Reddit, News sentiment aggregation
"""

from .aggregator import SentimentAggregator, CombinedSentiment
from .fear_greed import FearGreedIndex

__all__ = ['SentimentAggregator', 'CombinedSentiment', 'FearGreedIndex']
