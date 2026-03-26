import json
import os
from typing import List, Dict, Optional
from datetime import datetime


class StateManager:
    """Manages task state persistence."""

    def __init__(self, tasks_file: str = "project_alpha/tasks/tasks.json"):
        self.tasks_file = tasks_file
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Ensure tasks file exists."""
        if not os.path.exists(self.tasks_file):
            os.makedirs(os.path.dirname(self.tasks_file), exist_ok=True)
            with open(self.tasks_file, 'w') as f:
                json.dump([], f)

    def load_tasks(self) -> List[Dict]:
        """
        Load all tasks from storage.

        Returns:
            List of task dictionaries
        """
        try:
            with open(self.tasks_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save_tasks(self, tasks: List[Dict]):
        """
        Save all tasks to storage.

        Args:
            tasks: List of task dictionaries to save
        """
        with open(self.tasks_file, 'w') as f:
            json.dump(tasks, f, indent=2)

    def add_task(self, task: Dict):
        """
        Add a new task to storage.

        Args:
            task: Task dictionary to add
        """
        tasks = self.load_tasks()
        tasks.append(task)
        self.save_tasks(tasks)

    def update_task(self, task_id: str, updates: Dict):
        """
        Update an existing task.

        Args:
            task_id: ID of task to update
            updates: Dictionary of fields to update
        """
        tasks = self.load_tasks()
        updated = False

        for task in tasks:
            if task["task_id"] == task_id:
                task.update(updates)
                task["updated_at"] = datetime.utcnow().isoformat()
                updated = True
                break

        if updated:
            self.save_tasks(tasks)
        else:
            raise ValueError(f"Task {task_id} not found")

    def get_task(self, task_id: str) -> Optional[Dict]:
        """
        Get a specific task by ID.

        Args:
            task_id: ID of task to retrieve

        Returns:
            Task dictionary or None if not found
        """
        tasks = self.load_tasks()
        for task in tasks:
            if task["task_id"] == task_id:
                return task
        return None

    def get_pending_tasks(self) -> List[Dict]:
        """
        Get all tasks with pending status.

        Returns:
            List of pending task dictionaries
        """
        tasks = self.load_tasks()
        return [task for task in tasks if task["status"] == "pending"]

    def get_tasks_by_status(self, status: str) -> List[Dict]:
        """
        Get all tasks with a specific status.

        Args:
            status: Status to filter by

        Returns:
            List of task dictionaries matching status
        """
        tasks = self.load_tasks()
        return [task for task in tasks if task["status"] == status]

    def get_all_tasks(self) -> List[Dict]:
        """
        Get all tasks.

        Returns:
            List of all task dictionaries
        """
        return self.load_tasks()

    def clear_tasks(self):
        """Clear all tasks from storage."""
        self.save_tasks([])
