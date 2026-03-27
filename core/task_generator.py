import uuid
from datetime import datetime, timezone
from typing import List, Dict


class TaskGenerator:
    """Generates structured tasks from high-level goals."""

    def __init__(self):
        self.project_name = "project_alpha"

    def generate_tasks(self, goal: str) -> List[Dict]:
        """
        Generate 5-8 ordered tasks from a goal string.

        Args:
            goal: High-level goal description

        Returns:
            List of structured task dictionaries
        """
        tasks = []
        timestamp = datetime.now(timezone.utc).isoformat()

        task_definitions = self._decompose_goal(goal)

        for idx, task_def in enumerate(task_definitions):
            task = {
                "project": self.project_name,
                "task_id": str(uuid.uuid4()),
                "title": task_def["title"],
                "description": task_def["description"],
                "status": "pending",
                "priority": task_def.get("priority", "medium"),
                "dependencies": task_def.get("dependencies", []),
                "assigned_agent": task_def.get("assigned_agent", "builder"),
                "input": task_def.get("input", {}),
                "output": {},
                "error": "",
                "created_at": timestamp,
                "updated_at": timestamp
            }
            tasks.append(task)

        return tasks

    def _decompose_goal(self, goal: str) -> List[Dict]:
        """
        Decompose goal into structured task definitions.

        Args:
            goal: High-level goal string

        Returns:
            List of task definition dictionaries
        """
        goal_lower = goal.lower()

        if "website" in goal_lower or "web" in goal_lower:
            return self._generate_web_tasks(goal)
        elif "automation" in goal_lower or "automate" in goal_lower:
            return self._generate_automation_tasks(goal)
        elif "content" in goal_lower or "write" in goal_lower:
            return self._generate_content_tasks(goal)
        else:
            return self._generate_generic_tasks(goal)

    def _generate_web_tasks(self, goal: str) -> List[Dict]:
        """Generate tasks for web development goals."""
        return [
            {
                "title": "Design system architecture",
                "description": f"Design architecture for: {goal}",
                "assigned_agent": "builder",
                "priority": "high",
                "input": {"goal": goal}
            },
            {
                "title": "Set up project structure",
                "description": "Create project folders and initialize configuration",
                "assigned_agent": "builder",
                "priority": "high",
                "input": {}
            },
            {
                "title": "Implement backend logic",
                "description": "Build server-side functionality and APIs",
                "assigned_agent": "builder",
                "priority": "high",
                "input": {}
            },
            {
                "title": "Implement frontend interface",
                "description": "Build user interface components",
                "assigned_agent": "builder",
                "priority": "medium",
                "input": {}
            },
            {
                "title": "Set up database",
                "description": "Configure database schema and connections",
                "assigned_agent": "automation",
                "priority": "medium",
                "input": {}
            },
            {
                "title": "Implement testing",
                "description": "Create unit and integration tests",
                "assigned_agent": "builder",
                "priority": "medium",
                "input": {}
            },
            {
                "title": "Deploy to production",
                "description": "Configure deployment pipeline and deploy",
                "assigned_agent": "automation",
                "priority": "low",
                "input": {}
            }
        ]

    def _generate_automation_tasks(self, goal: str) -> List[Dict]:
        """Generate tasks for automation goals."""
        return [
            {
                "title": "Analyze automation requirements",
                "description": f"Analyze requirements for: {goal}",
                "assigned_agent": "automation",
                "priority": "high",
                "input": {"goal": goal}
            },
            {
                "title": "Design automation workflow",
                "description": "Design the automation workflow and steps",
                "assigned_agent": "automation",
                "priority": "high",
                "input": {}
            },
            {
                "title": "Implement core automation logic",
                "description": "Build the main automation functionality",
                "assigned_agent": "automation",
                "priority": "high",
                "input": {}
            },
            {
                "title": "Add error handling",
                "description": "Implement error handling and retry logic",
                "assigned_agent": "automation",
                "priority": "medium",
                "input": {}
            },
            {
                "title": "Create monitoring",
                "description": "Set up monitoring and logging",
                "assigned_agent": "automation",
                "priority": "medium",
                "input": {}
            },
            {
                "title": "Test automation end-to-end",
                "description": "Run complete automation tests",
                "assigned_agent": "automation",
                "priority": "medium",
                "input": {}
            }
        ]

    def _generate_content_tasks(self, goal: str) -> List[Dict]:
        """Generate tasks for content creation goals."""
        return [
            {
                "title": "Research topic",
                "description": f"Research content topic: {goal}",
                "assigned_agent": "content",
                "priority": "high",
                "input": {"goal": goal}
            },
            {
                "title": "Create content outline",
                "description": "Develop detailed content outline",
                "assigned_agent": "content",
                "priority": "high",
                "input": {}
            },
            {
                "title": "Write first draft",
                "description": "Write initial content draft",
                "assigned_agent": "content",
                "priority": "high",
                "input": {}
            },
            {
                "title": "Review and edit",
                "description": "Review content for quality and accuracy",
                "assigned_agent": "content",
                "priority": "medium",
                "input": {}
            },
            {
                "title": "Finalize content",
                "description": "Finalize and format content",
                "assigned_agent": "content",
                "priority": "medium",
                "input": {}
            }
        ]

    def _generate_generic_tasks(self, goal: str) -> List[Dict]:
        """Generate generic tasks for unspecified goals."""
        return [
            {
                "title": "Analyze goal requirements",
                "description": f"Analyze requirements for: {goal}",
                "assigned_agent": "builder",
                "priority": "high",
                "input": {"goal": goal}
            },
            {
                "title": "Design solution",
                "description": "Design solution architecture",
                "assigned_agent": "builder",
                "priority": "high",
                "input": {}
            },
            {
                "title": "Implement core functionality",
                "description": "Build core features",
                "assigned_agent": "builder",
                "priority": "high",
                "input": {}
            },
            {
                "title": "Add supporting features",
                "description": "Implement supporting functionality",
                "assigned_agent": "builder",
                "priority": "medium",
                "input": {}
            },
            {
                "title": "Test implementation",
                "description": "Test all functionality",
                "assigned_agent": "builder",
                "priority": "medium",
                "input": {}
            },
            {
                "title": "Document solution",
                "description": "Create documentation",
                "assigned_agent": "content",
                "priority": "low",
                "input": {}
            }
        ]
