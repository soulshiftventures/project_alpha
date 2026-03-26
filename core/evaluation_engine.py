from typing import Dict


class EvaluationEngine:
    """Evaluates task outcomes and determines next actions."""

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.retry_counts = {}

    def evaluate(self, task: Dict, result: Dict) -> str:
        """
        Evaluate task result and determine action.

        Args:
            task: Task dictionary
            result: Result dictionary from result collector

        Returns:
            Action string: "proceed" or "retry"
        """
        task_id = task["task_id"]
        status = result.get("status", "failed")

        if status == "completed":
            if task_id in self.retry_counts:
                del self.retry_counts[task_id]
            return "proceed"

        elif status == "failed":
            retry_count = self.retry_counts.get(task_id, 0)

            if retry_count < self.max_retries:
                self.retry_counts[task_id] = retry_count + 1
                return "retry"
            else:
                if task_id in self.retry_counts:
                    del self.retry_counts[task_id]
                return "proceed"

        return "proceed"

    def get_retry_count(self, task_id: str) -> int:
        """
        Get current retry count for a task.

        Args:
            task_id: Task ID

        Returns:
            Number of retries attempted
        """
        return self.retry_counts.get(task_id, 0)

    def reset_retry_count(self, task_id: str):
        """
        Reset retry count for a task.

        Args:
            task_id: Task ID
        """
        if task_id in self.retry_counts:
            del self.retry_counts[task_id]
