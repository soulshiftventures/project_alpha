"""
Memory system for project_alpha
Stores decisions, results, and long-term context
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional


class Memory:
    """Long-term memory system for storing project context."""

    def __init__(self, memory_dir: str = "project_alpha/memory"):
        self.memory_dir = memory_dir
        self.long_term_file = os.path.join(memory_dir, "long_term.json")
        self._ensure_directory()

    def _ensure_directory(self):
        """Ensure memory directory and file exist."""
        os.makedirs(self.memory_dir, exist_ok=True)
        if not os.path.exists(self.long_term_file):
            self._write_memory({"decisions": [], "results": [], "learnings": []})

    def _read_memory(self) -> Dict:
        """Read memory from file."""
        try:
            with open(self.long_term_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"decisions": [], "results": [], "learnings": []}

    def _write_memory(self, data: Dict):
        """Write memory to file."""
        with open(self.long_term_file, 'w') as f:
            json.dump(data, f, indent=2)

    def save_decision(self, decision: str, context: str, outcome: Optional[str] = None):
        """
        Save a decision to memory.

        Args:
            decision: The decision made
            context: Context around the decision
            outcome: Optional outcome of the decision
        """
        memory = self._read_memory()

        decision_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "decision": decision,
            "context": context,
            "outcome": outcome,
            "type": "decision"
        }

        memory["decisions"].append(decision_entry)
        self._write_memory(memory)

    def save_result(self, task_id: str, task_title: str, result: Dict):
        """
        Save a task result to memory.

        Args:
            task_id: Task identifier
            task_title: Task title
            result: Result data
        """
        memory = self._read_memory()

        result_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "task_id": task_id,
            "task_title": task_title,
            "status": result.get("status", "unknown"),
            "output": result.get("output", {}),
            "error": result.get("error", ""),
            "type": "result"
        }

        memory["results"].append(result_entry)
        self._write_memory(memory)

    def save_learning(self, category: str, insight: str, confidence: float = 1.0):
        """
        Save a learning or insight.

        Args:
            category: Category of learning
            insight: The insight learned
            confidence: Confidence level (0.0-1.0)
        """
        memory = self._read_memory()

        learning_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "category": category,
            "insight": insight,
            "confidence": max(0.0, min(1.0, confidence)),
            "type": "learning"
        }

        memory["learnings"].append(learning_entry)
        self._write_memory(memory)

    def load_memory(self, memory_type: Optional[str] = None) -> List[Dict]:
        """
        Load memory entries.

        Args:
            memory_type: Optional filter by type (decisions, results, learnings)

        Returns:
            List of memory entries
        """
        memory = self._read_memory()

        if memory_type and memory_type in memory:
            return memory[memory_type]

        all_entries = []
        for entries in memory.values():
            if isinstance(entries, list):
                all_entries.extend(entries)

        all_entries.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return all_entries

    def get_recent_decisions(self, limit: int = 10) -> List[Dict]:
        """Get recent decisions."""
        memory = self._read_memory()
        decisions = memory.get("decisions", [])
        return sorted(decisions, key=lambda x: x.get("timestamp", ""), reverse=True)[:limit]

    def get_recent_results(self, limit: int = 10) -> List[Dict]:
        """Get recent task results."""
        memory = self._read_memory()
        results = memory.get("results", [])
        return sorted(results, key=lambda x: x.get("timestamp", ""), reverse=True)[:limit]

    def get_learnings_by_category(self, category: str) -> List[Dict]:
        """Get learnings filtered by category."""
        memory = self._read_memory()
        learnings = memory.get("learnings", [])
        return [l for l in learnings if l.get("category") == category]

    def get_statistics(self) -> Dict:
        """Get memory statistics."""
        memory = self._read_memory()

        return {
            "total_decisions": len(memory.get("decisions", [])),
            "total_results": len(memory.get("results", [])),
            "total_learnings": len(memory.get("learnings", [])),
            "successful_tasks": len([
                r for r in memory.get("results", [])
                if r.get("status") == "completed"
            ]),
            "failed_tasks": len([
                r for r in memory.get("results", [])
                if r.get("status") == "failed"
            ])
        }

    def clear_memory(self):
        """Clear all memory (use with caution)."""
        self._write_memory({"decisions": [], "results": [], "learnings": []})

    def export_memory(self, filepath: str):
        """Export memory to a file."""
        memory = self._read_memory()
        with open(filepath, 'w') as f:
            json.dump(memory, f, indent=2)
