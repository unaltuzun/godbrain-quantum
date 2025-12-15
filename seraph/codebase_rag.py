# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
SERAPH RAG - Codebase Retrieval Augmented Generation
Intelligent code search for context-aware responses.
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import re
import json
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict


ROOT = Path(__file__).parent.parent


@dataclass
class CodeChunk:
    """A chunk of code from the codebase."""
    file_path: str
    content: str
    start_line: int
    end_line: int
    chunk_type: str  # "function", "class", "module", "comment"
    name: str = ""
    docstring: str = ""
    
    @property
    def relative_path(self) -> str:
        return str(Path(self.file_path).relative_to(ROOT))
    
    def to_context(self) -> str:
        """Format for LLM context."""
        return f"[{self.relative_path}:{self.start_line}-{self.end_line}] {self.chunk_type}: {self.name}\n{self.content[:500]}"


@dataclass
class SearchResult:
    """Search result with relevance score."""
    chunk: CodeChunk
    score: float
    match_reason: str


class CodebaseRAG:
    """
    RAG system for codebase search.
    
    Features:
    - Keyword-based search (fast)
    - Semantic search (via embeddings if available)
    - Function/class discovery
    - Docstring extraction
    - Context window management
    
    Usage:
        rag = CodebaseRAG()
        rag.index_codebase()
        results = rag.search("circuit breaker implementation")
        context = rag.get_context_for_query("how does retry work?")
    """
    
    # File patterns to index
    INCLUDE_PATTERNS = ["*.py"]
    EXCLUDE_DIRS = [".git", "__pycache__", "node_modules", ".venv", "venv", "mlruns"]
    
    def __init__(self, root_path: Optional[Path] = None):
        self.root = root_path or ROOT
        self.chunks: List[CodeChunk] = []
        self.index: Dict[str, List[int]] = defaultdict(list)  # keyword -> chunk indices
        self._indexed = False
    
    def index_codebase(self, force: bool = False) -> int:
        """Index all Python files in codebase."""
        if self._indexed and not force:
            return len(self.chunks)
        
        self.chunks = []
        self.index = defaultdict(list)
        
        for pattern in self.INCLUDE_PATTERNS:
            for file_path in self.root.rglob(pattern):
                # Skip excluded directories
                if any(ex in str(file_path) for ex in self.EXCLUDE_DIRS):
                    continue
                
                try:
                    self._index_file(file_path)
                except Exception as e:
                    continue
        
        self._indexed = True
        return len(self.chunks)
    
    def _index_file(self, file_path: Path) -> None:
        """Index a single Python file."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return
        
        lines = content.split("\n")
        
        # Extract functions and classes
        current_block = []
        current_start = 0
        current_type = "module"
        current_name = file_path.stem
        in_block = False
        indent_level = 0
        
        for i, line in enumerate(lines):
            # Detect function/class definitions
            func_match = re.match(r"^(\s*)def\s+(\w+)", line)
            class_match = re.match(r"^(\s*)class\s+(\w+)", line)
            
            if func_match or class_match:
                # Save previous block
                if current_block:
                    self._add_chunk(
                        file_path, current_block, current_start,
                        current_type, current_name
                    )
                
                # Start new block
                match = func_match or class_match
                indent_level = len(match.group(1))
                current_name = match.group(2)
                current_type = "function" if func_match else "class"
                current_start = i + 1
                current_block = [line]
                in_block = True
            
            elif in_block:
                # Check if still in the same block
                if line.strip() and not line.startswith(" " * (indent_level + 1)) and not line.startswith(" " * indent_level + " "):
                    if not line.strip().startswith("#") and not line.strip().startswith('"""') and not line.strip().startswith("'''"):
                        # End of block
                        self._add_chunk(
                            file_path, current_block, current_start,
                            current_type, current_name
                        )
                        current_block = []
                        in_block = False
                        continue
                
                current_block.append(line)
        
        # Save last block
        if current_block:
            self._add_chunk(
                file_path, current_block, current_start,
                current_type, current_name
            )
    
    def _add_chunk(
        self,
        file_path: Path,
        lines: List[str],
        start_line: int,
        chunk_type: str,
        name: str
    ) -> None:
        """Add a code chunk to the index."""
        content = "\n".join(lines)
        
        # Extract docstring
        docstring = ""
        doc_match = re.search(r'"""(.*?)"""', content, re.DOTALL)
        if doc_match:
            docstring = doc_match.group(1).strip()[:200]
        
        chunk = CodeChunk(
            file_path=str(file_path),
            content=content,
            start_line=start_line,
            end_line=start_line + len(lines),
            chunk_type=chunk_type,
            name=name,
            docstring=docstring,
        )
        
        idx = len(self.chunks)
        self.chunks.append(chunk)
        
        # Index keywords
        keywords = self._extract_keywords(content + " " + name + " " + docstring)
        for kw in keywords:
            self.index[kw.lower()].append(idx)
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract searchable keywords from text."""
        # Split on non-alphanumeric, filter short words
        words = re.findall(r"\b[a-zA-Z_]\w{2,}\b", text.lower())
        return list(set(words))
    
    def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """
        Search codebase for relevant code.
        
        Args:
            query: Natural language query
            top_k: Number of results to return
        
        Returns:
            List of SearchResult with chunks and scores
        """
        if not self._indexed:
            self.index_codebase()
        
        query_keywords = self._extract_keywords(query)
        
        # Score each chunk
        scores: Dict[int, Tuple[float, str]] = {}
        
        for kw in query_keywords:
            for idx in self.index.get(kw, []):
                if idx not in scores:
                    scores[idx] = (0, "")
                
                # Boost for name match
                chunk = self.chunks[idx]
                boost = 1.0
                if kw in chunk.name.lower():
                    boost = 3.0
                elif kw in chunk.docstring.lower():
                    boost = 2.0
                
                old_score, old_reason = scores[idx]
                scores[idx] = (old_score + boost, f"{old_reason} {kw}")
        
        # Sort by score
        sorted_indices = sorted(scores.keys(), key=lambda x: scores[x][0], reverse=True)
        
        results = []
        for idx in sorted_indices[:top_k]:
            score, reason = scores[idx]
            results.append(SearchResult(
                chunk=self.chunks[idx],
                score=score,
                match_reason=reason.strip()
            ))
        
        return results
    
    def get_context_for_query(self, query: str, max_tokens: int = 2000) -> str:
        """
        Get relevant code context for a query.
        
        Returns formatted context string for LLM injection.
        """
        results = self.search(query, top_k=10)
        
        context_parts = ["=== RELEVANT CODE CONTEXT ==="]
        used_tokens = 0
        
        for r in results:
            chunk_text = r.chunk.to_context()
            chunk_tokens = len(chunk_text) // 4  # Approximate
            
            if used_tokens + chunk_tokens > max_tokens:
                break
            
            context_parts.append(f"\n[Score: {r.score:.1f}] {chunk_text}")
            used_tokens += chunk_tokens
        
        return "\n".join(context_parts)
    
    def find_function(self, name: str) -> Optional[CodeChunk]:
        """Find a specific function by name."""
        if not self._indexed:
            self.index_codebase()
        
        for chunk in self.chunks:
            if chunk.chunk_type == "function" and chunk.name == name:
                return chunk
        return None
    
    def find_class(self, name: str) -> Optional[CodeChunk]:
        """Find a specific class by name."""
        if not self._indexed:
            self.index_codebase()
        
        for chunk in self.chunks:
            if chunk.chunk_type == "class" and chunk.name == name:
                return chunk
        return None
    
    def get_file_summary(self, file_path: str) -> str:
        """Get summary of a file's contents."""
        if not self._indexed:
            self.index_codebase()
        
        chunks = [c for c in self.chunks if file_path in c.file_path]
        
        if not chunks:
            return f"No indexed content for {file_path}"
        
        lines = [f"📄 {file_path}"]
        for c in chunks:
            lines.append(f"  • {c.chunk_type}: {c.name}")
            if c.docstring:
                lines.append(f"    {c.docstring[:80]}...")
        
        return "\n".join(lines)


# Global instance
_rag: Optional[CodebaseRAG] = None


def get_codebase_rag() -> CodebaseRAG:
    """Get or create global RAG instance."""
    global _rag
    if _rag is None:
        _rag = CodebaseRAG()
        _rag.index_codebase()
    return _rag


if __name__ == "__main__":
    print("Codebase RAG Demo")
    print("=" * 60)
    
    rag = CodebaseRAG()
    n = rag.index_codebase()
    print(f"Indexed {n} code chunks")
    
    # Test search
    query = "circuit breaker failure handling"
    print(f"\nSearching: '{query}'")
    
    results = rag.search(query)
    for r in results:
        print(f"\n[{r.score:.1f}] {r.chunk.relative_path}:{r.chunk.start_line}")
        print(f"   {r.chunk.chunk_type}: {r.chunk.name}")
        print(f"   {r.match_reason}")
