# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
GOD'S EYES - News Collector
Fetches real-time crypto news from RSS feeds.
═══════════════════════════════════════════════════════════════════════════════
"""

import time
import feedparser
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class NewsItem:
    title: str
    link: str
    published: str
    source: str
    summary: str
    timestamp: float

class NewsCollector:
    """
    Collects news from RSS feeds.
    Sources: CoinDesk, Cointelegraph, Decrypt, Bitcoin Magazine.
    """
    
    SOURCES = {
        "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "Cointelegraph": "https://cointelegraph.com/rss",
        "Decrypt": "https://decrypt.co/feed",
        "BitcoinMagazine": "https://bitcoinmagazine.com/.rss/full/",
        "U.Today": "https://u.today/rss"
    }
    
    def __init__(self):
        self.cache: List[NewsItem] = []
        self.last_update = 0
        self.update_interval = 300  # 5 minutes
    
    def fetch_news(self, force: bool = False) -> List[NewsItem]:
        """Fetch news from all sources."""
        now = time.time()
        if not force and (now - self.last_update < self.update_interval) and self.cache:
            return self.cache
            
        all_news = []
        
        for source_name, url in self.SOURCES.items():
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:5]:  # Get top 5 from each
                    # Parse date safely
                    published = getattr(entry, "published", str(datetime.now()))
                    timestamp = time.mktime(entry.published_parsed) if hasattr(entry, "published_parsed") and entry.published_parsed else now
                    
                    item = NewsItem(
                        title=entry.title,
                        link=entry.link,
                        published=published,
                        source=source_name,
                        summary=self._clean_summary(getattr(entry, "summary", "")),
                        timestamp=timestamp
                    )
                    all_news.append(item)
            except Exception as e:
                print(f"[NewsCollector] Error fetching {source_name}: {e}")
                continue
        
        # Sort by timestamp (newest first)
        all_news.sort(key=lambda x: x.timestamp, reverse=True)
        
        self.cache = all_news
        self.last_update = now
        return all_news

    def get_latest_headlines(self, limit: int = 10) -> str:
        """Get formatted headlines for LLM consumption."""
        news = self.fetch_news()
        output = []
        for i, item in enumerate(news[:limit]):
            output.append(f"{i+1}. [{item.source}] {item.title} ({item.published})")
        return "\n".join(output)
    
    def _clean_summary(self, summary: str) -> str:
        """Remove HTML tags from summary."""
        import re
        clean = re.compile('<.*?>')
        return re.sub(clean, '', summary)[:200] + "..."

# Global instance
_collector = None

def get_news_collector():
    global _collector
    if _collector is None:
        _collector = NewsCollector()
    return _collector
