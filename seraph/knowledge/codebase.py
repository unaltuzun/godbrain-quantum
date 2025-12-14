# ==============================================================================
# CODEBASE INDEX - Code Understanding Engine
# ==============================================================================
"""
Index and understand the GodBrain codebase.

Seraph learns:
- What each module does
- Function signatures and purposes
- Critical code paths
- Common patterns
"""

import os
import re
import json
import logging
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("seraph.knowledge.codebase")


@dataclass
class CodeEntity:
    """A code entity (function, class, module)"""
    name: str
    type: str  # "function", "class", "module"
    file_path: str
    line_number: int
    docstring: Optional[str]
    signature: Optional[str]
    importance: str  # "critical", "high", "medium", "low"


class CodebaseIndex:
    """
    Index of the GodBrain codebase.
    
    Enables Seraph to:
    - Understand what code exists
    - Find relevant functions
    - Know critical paths
    - Suggest improvements
    """
    
    # Critical files that Seraph must understand
    CRITICAL_FILES = [
        "core/god_dashboard.py",
        "market_feed.py",
        "agg.py",
        "engines/decision_engine.py",
        "quantum_lab/quantum_daemon.py",
        "genetics/blackjack_lab.py"
    ]
    
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).parent.parent.parent
        self._entities: Dict[str, CodeEntity] = {}
        self._index()
    
    def _index(self):
        """Index the codebase"""
        for py_file in self.project_root.rglob("*.py"):
            # Skip __pycache__, venv, etc.
            if any(skip in str(py_file) for skip in ["__pycache__", "venv", ".venv", "node_modules"]):
                continue
            
            try:
                self._index_file(py_file)
            except Exception as e:
                logger.debug(f"Failed to index {py_file}: {e}")
        
        logger.info(f"Indexed {len(self._entities)} code entities")
    
    def _index_file(self, file_path: Path):
        """Index a single Python file"""
        relative_path = str(file_path.relative_to(self.project_root))
        importance = "critical" if relative_path in self.CRITICAL_FILES else "medium"
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return
        
        # Find functions
        func_pattern = r'def\s+(\w+)\s*\((.*?)\).*?(?:"""(.*?)"""|\'\'\'(.*?)\'\'\')?'
        for match in re.finditer(func_pattern, content, re.DOTALL):
            name = match.group(1)
            params = match.group(2)
            docstring = match.group(3) or match.group(4) or ""
            
            # Get line number
            line_num = content[:match.start()].count('\n') + 1
            
            entity_id = f"{relative_path}::{name}"
            self._entities[entity_id] = CodeEntity(
                name=name,
                type="function",
                file_path=relative_path,
                line_number=line_num,
                docstring=docstring.strip()[:200] if docstring else None,
                signature=f"def {name}({params})",
                importance=importance
            )
        
        # Find classes
        class_pattern = r'class\s+(\w+).*?(?:"""(.*?)"""|\'\'\'(.*?)\'\'\')?'
        for match in re.finditer(class_pattern, content, re.DOTALL):
            name = match.group(1)
            docstring = match.group(2) or match.group(3) or ""
            line_num = content[:match.start()].count('\n') + 1
            
            entity_id = f"{relative_path}::{name}"
            self._entities[entity_id] = CodeEntity(
                name=name,
                type="class",
                file_path=relative_path,
                line_number=line_num,
                docstring=docstring.strip()[:200] if docstring else None,
                signature=f"class {name}",
                importance=importance
            )
    
    def search(self, query: str, limit: int = 10) -> List[CodeEntity]:
        """
        Search for code entities.
        
        Args:
            query: Search query
            limit: Max results
        
        Returns:
            Matching entities
        """
        query_lower = query.lower()
        results = []
        
        for entity in self._entities.values():
            score = 0
            
            # Name match
            if query_lower in entity.name.lower():
                score += 10
            
            # Docstring match
            if entity.docstring and query_lower in entity.docstring.lower():
                score += 5
            
            # File path match
            if query_lower in entity.file_path.lower():
                score += 3
            
            # Importance boost
            if entity.importance == "critical":
                score *= 2
            elif entity.importance == "high":
                score *= 1.5
            
            if score > 0:
                results.append((score, entity))
        
        # Sort by score
        results.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in results[:limit]]
    
    def get_critical_functions(self) -> List[CodeEntity]:
        """Get all critical functions"""
        return [e for e in self._entities.values() 
                if e.importance == "critical" and e.type == "function"]
    
    def get_module_summary(self, module_path: str) -> Dict[str, Any]:
        """Get summary of a module"""
        entities = [e for e in self._entities.values() if e.file_path == module_path]
        
        return {
            "path": module_path,
            "functions": [e.name for e in entities if e.type == "function"],
            "classes": [e.name for e in entities if e.type == "class"],
            "total_entities": len(entities)
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        return {
            "total_entities": len(self._entities),
            "functions": len([e for e in self._entities.values() if e.type == "function"]),
            "classes": len([e for e in self._entities.values() if e.type == "class"]),
            "critical": len([e for e in self._entities.values() if e.importance == "critical"]),
            "files_indexed": len(set(e.file_path for e in self._entities.values()))
        }

