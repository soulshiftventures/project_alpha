from typing import Dict


class ResultCollector:
    """Collects and processes agent execution results."""

    def collect_result(self, task: Dict, execution_result: Dict) -> Dict:
        """
        Process agent execution result and update task.

        Args:
            task: Original task dictionary
            execution_result: Result from execution engine

        Returns:
            Dictionary with updates to apply to task
        """
        status = execution_result.get("status", "failed")
        output = execution_result.get("output", {})
        error = execution_result.get("error", "")

        if status == "success":
            return {
                "status": "completed",
                "output": output,
                "error": ""
            }
        else:
            return {
                "status": "failed",
                "output": {},
                "error": error
            }

    def format_result(self, result: Dict) -> str:
        """
        Format result for display.

        Args:
            result: Result dictionary

        Returns:
            Formatted string representation
        """
        status = result.get("status", "unknown")

        if status == "completed":
            output = result.get("output", {})
            return f"✓ Completed: {output}"
        elif status == "failed":
            error = result.get("error", "Unknown error")
            return f"✗ Failed: {error}"
        else:
            return f"? Unknown status: {status}"
