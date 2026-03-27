"""
Planning Engine for project_alpha
Uses AI to generate detailed task plans from opportunities
"""

import json
import uuid
from datetime import datetime, timezone
from typing import List, Dict
from core.ai_client import AIClient


class PlanningEngine:
    """Engine for generating AI-powered task plans."""

    def __init__(self):
        self.ai_client = AIClient()
        self.project_name = "project_alpha"

    def create_task_plan(self, opportunity: Dict) -> List[Dict]:
        """
        Generate detailed task plan for an opportunity using AI.

        Args:
            opportunity: Opportunity dictionary with idea and description

        Returns:
            List of task dictionaries matching task schema
        """
        idea = opportunity.get("idea", "Unknown opportunity")
        description = opportunity.get("description", "")

        prompt = f"""Create a detailed execution plan for this opportunity:

Title: {idea}
Description: {description}

Generate 5-8 concrete, actionable tasks to implement this opportunity.

For each task, provide:
- title: Clear, action-oriented task name
- description: Detailed description of what needs to be done
- priority: high, medium, or low
- assigned_agent: builder, automation, or content

Guidelines:
- Start with research/planning tasks
- Include implementation tasks
- Add testing/validation tasks
- End with deployment/launch tasks
- Tasks should be sequential and build on each other

Return as JSON array:
[
  {{
    "title": "task name",
    "description": "detailed description",
    "priority": "high|medium|low",
    "assigned_agent": "builder|automation|content"
  }}
]

Return ONLY valid JSON, no additional text."""

        response = self.ai_client.ask_ai(
            prompt=prompt,
            system_prompt="You are a project manager creating detailed execution plans.",
            temperature=0.7
        )

        try:
            task_definitions = json.loads(response)
            if isinstance(task_definitions, list) and len(task_definitions) > 0:
                return self._convert_to_tasks(task_definitions, opportunity)
            else:
                return self._generate_fallback_plan(opportunity)
        except json.JSONDecodeError:
            return self._generate_fallback_plan(opportunity)

    def _convert_to_tasks(self, task_definitions: List[Dict], opportunity: Dict) -> List[Dict]:
        """Convert task definitions to full task schema."""
        tasks = []
        timestamp = datetime.now(timezone.utc).isoformat()

        for idx, task_def in enumerate(task_definitions):
            if not isinstance(task_def, dict):
                continue

            task = {
                "project": self.project_name,
                "task_id": str(uuid.uuid4()),
                "title": task_def.get("title", f"Task {idx + 1}")[:200],
                "description": task_def.get("description", "")[:500],
                "status": "pending",
                "priority": self._normalize_priority(task_def.get("priority", "medium")),
                "dependencies": [],
                "assigned_agent": self._normalize_agent(task_def.get("assigned_agent", "builder")),
                "input": {
                    "opportunity": opportunity.get("idea", ""),
                    "context": opportunity.get("description", "")
                },
                "output": {},
                "error": "",
                "created_at": timestamp,
                "updated_at": timestamp
            }
            tasks.append(task)

        return tasks

    def _normalize_priority(self, priority: str) -> str:
        """Normalize priority value."""
        priority_lower = str(priority).lower()
        if priority_lower in ["high", "medium", "low"]:
            return priority_lower
        return "medium"

    def _normalize_agent(self, agent: str) -> str:
        """Normalize agent name."""
        agent_lower = str(agent).lower()
        if agent_lower in ["builder", "automation", "content"]:
            return agent_lower
        return "builder"

    def _generate_fallback_plan(self, opportunity: Dict) -> List[Dict]:
        """Generate fallback plan if AI fails."""
        idea = opportunity.get("idea", "Unknown")
        timestamp = datetime.now(timezone.utc).isoformat()

        return [
            {
                "project": self.project_name,
                "task_id": str(uuid.uuid4()),
                "title": "Research and validate opportunity",
                "description": f"Research {idea} market, validate demand, analyze competitors",
                "status": "pending",
                "priority": "high",
                "dependencies": [],
                "assigned_agent": "content",
                "input": {"opportunity": idea},
                "output": {},
                "error": "",
                "created_at": timestamp,
                "updated_at": timestamp
            },
            {
                "project": self.project_name,
                "task_id": str(uuid.uuid4()),
                "title": "Design system architecture",
                "description": f"Design technical architecture for {idea}",
                "status": "pending",
                "priority": "high",
                "dependencies": [],
                "assigned_agent": "builder",
                "input": {"opportunity": idea},
                "output": {},
                "error": "",
                "created_at": timestamp,
                "updated_at": timestamp
            },
            {
                "project": self.project_name,
                "task_id": str(uuid.uuid4()),
                "title": "Implement core functionality",
                "description": f"Build core features for {idea}",
                "status": "pending",
                "priority": "high",
                "dependencies": [],
                "assigned_agent": "builder",
                "input": {"opportunity": idea},
                "output": {},
                "error": "",
                "created_at": timestamp,
                "updated_at": timestamp
            },
            {
                "project": self.project_name,
                "task_id": str(uuid.uuid4()),
                "title": "Set up automation workflows",
                "description": f"Configure automation for {idea}",
                "status": "pending",
                "priority": "medium",
                "dependencies": [],
                "assigned_agent": "automation",
                "input": {"opportunity": idea},
                "output": {},
                "error": "",
                "created_at": timestamp,
                "updated_at": timestamp
            },
            {
                "project": self.project_name,
                "task_id": str(uuid.uuid4()),
                "title": "Test and validate system",
                "description": f"Comprehensive testing of {idea}",
                "status": "pending",
                "priority": "medium",
                "dependencies": [],
                "assigned_agent": "automation",
                "input": {"opportunity": idea},
                "output": {},
                "error": "",
                "created_at": timestamp,
                "updated_at": timestamp
            }
        ]

    def create_stage_tasks(self, business: Dict, stage: str) -> List[Dict]:
        """
        Generate stage-specific tasks for a business.

        Args:
            business: Business dictionary
            stage: Current stage name

        Returns:
            List of tasks appropriate for the stage
        """
        opportunity = business["opportunity"]
        idea = opportunity.get("idea", "Unknown")
        description = opportunity.get("description", "")
        metrics = business.get("metrics", {})

        prompt = ""
        task_count = "3-5"
        primary_agent = "builder"

        if stage == "VALIDATING":
            task_count = "3-5"
            prompt = f"""Generate quick validation tests for this opportunity:

Title: {idea}
Description: {description}

Create {task_count} fast validation tasks focusing on:
- Market demand validation
- Technical feasibility check
- Competitor analysis
- Cost-benefit analysis

These should be QUICK tests that can be executed rapidly.

Return as JSON array:
[
  {{
    "title": "task name",
    "description": "detailed description",
    "priority": "high",
    "assigned_agent": "content|builder"
  }}
]"""

        elif stage == "BUILDING":
            task_count = "5-8"
            prompt = f"""Generate full implementation plan for this opportunity:

Title: {idea}
Description: {description}
Validation Score: {metrics.get('validation_score', 0.0)}

Create {task_count} detailed implementation tasks including:
- Architecture design
- Core feature development
- Integration setup
- Testing strategy
- Documentation

Return as JSON array with same structure."""

        elif stage == "SCALING":
            task_count = "4-6"
            prompt = f"""Generate scaling strategy for this opportunity:

Title: {idea}
Description: {description}
Build Progress: {metrics.get('build_progress', 0.0)}

Create {task_count} scaling tasks focusing on:
- Infrastructure scaling
- Performance optimization
- User acquisition strategies
- Monitoring setup
- Capacity planning

Return as JSON array with same structure."""

        elif stage == "OPERATING":
            task_count = "3-4"
            prompt = f"""Generate operational maintenance tasks for this opportunity:

Title: {idea}
Description: {description}
Performance: {metrics.get('performance', 0.0)}

Create {task_count} ongoing maintenance tasks:
- System monitoring
- Performance tracking
- Issue resolution
- Routine updates

Return as JSON array with same structure."""

        elif stage == "OPTIMIZING":
            task_count = "4-5"
            prompt = f"""Generate optimization tasks for this underperforming opportunity:

Title: {idea}
Description: {description}
Current Performance: {metrics.get('performance', 0.0)}

Create {task_count} improvement tasks focusing on:
- Performance bottleneck analysis
- Code optimization
- User experience improvements
- Cost reduction strategies

Return as JSON array with same structure."""

        else:
            # Fallback for unknown stages
            return []

        response = self.ai_client.ask_ai(
            prompt=prompt,
            system_prompt=f"You are a project manager creating {stage} stage tasks.",
            temperature=0.7
        )

        try:
            task_definitions = json.loads(response)
            if isinstance(task_definitions, list) and len(task_definitions) > 0:
                return self._convert_to_tasks(task_definitions, opportunity)
            else:
                return self._generate_stage_fallback(stage, opportunity)
        except json.JSONDecodeError:
            return self._generate_stage_fallback(stage, opportunity)

    def _generate_stage_fallback(self, stage: str, opportunity: Dict) -> List[Dict]:
        """Generate fallback tasks for a specific stage."""
        idea = opportunity.get("idea", "Unknown")
        timestamp = datetime.now(timezone.utc).isoformat()

        tasks_by_stage = {
            "VALIDATING": [
                ("Validate market demand", "Research market demand and target audience", "content", "high"),
                ("Check technical feasibility", "Assess technical requirements and feasibility", "builder", "high"),
                ("Analyze competition", "Research competitors and market positioning", "content", "high")
            ],
            "BUILDING": [
                ("Design system architecture", f"Design technical architecture for {idea}", "builder", "high"),
                ("Implement core features", f"Build core functionality for {idea}", "builder", "high"),
                ("Set up testing", f"Create test suite for {idea}", "automation", "medium"),
                ("Create documentation", f"Write technical documentation for {idea}", "content", "medium")
            ],
            "SCALING": [
                ("Optimize performance", f"Optimize system performance for {idea}", "automation", "high"),
                ("Scale infrastructure", f"Scale infrastructure for {idea}", "builder", "high"),
                ("Implement monitoring", f"Set up monitoring for {idea}", "automation", "medium")
            ],
            "OPERATING": [
                ("Monitor system health", f"Monitor system health for {idea}", "automation", "medium"),
                ("Track performance metrics", f"Track and analyze performance for {idea}", "automation", "medium")
            ],
            "OPTIMIZING": [
                ("Analyze bottlenecks", f"Identify performance bottlenecks in {idea}", "builder", "high"),
                ("Optimize code", f"Optimize critical code paths in {idea}", "builder", "high"),
                ("Improve user experience", f"Enhance user experience for {idea}", "content", "medium")
            ]
        }

        stage_tasks = tasks_by_stage.get(stage, [])
        result = []

        for title, desc, agent, priority in stage_tasks:
            task = {
                "project": self.project_name,
                "task_id": str(uuid.uuid4()),
                "title": title,
                "description": desc,
                "status": "pending",
                "priority": priority,
                "dependencies": [],
                "assigned_agent": agent,
                "input": {"opportunity": idea},
                "output": {},
                "error": "",
                "created_at": timestamp,
                "updated_at": timestamp
            }
            result.append(task)

        return result

    def refine_task_plan(self, tasks: List[Dict], feedback: str) -> List[Dict]:
        """
        Refine existing task plan based on feedback.

        Args:
            tasks: Current task list
            feedback: Refinement feedback

        Returns:
            Refined task list
        """
        task_summary = "\n".join([
            f"{i+1}. {t['title']} ({t['assigned_agent']})"
            for i, t in enumerate(tasks)
        ])

        prompt = f"""Refine this task plan based on feedback:

Current tasks:
{task_summary}

Feedback: {feedback}

Provide updated task list as JSON array maintaining the same structure."""

        response = self.ai_client.ask_ai(prompt=prompt, temperature=0.7)

        try:
            refined = json.loads(response)
            if isinstance(refined, list):
                return self._convert_to_tasks(refined, {"idea": "Refined plan"})
        except json.JSONDecodeError:
            pass

        return tasks
