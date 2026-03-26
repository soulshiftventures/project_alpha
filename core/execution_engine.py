from typing import Dict
import importlib


class ExecutionEngine:
    """Routes tasks to appropriate agents and executes them."""

    def __init__(self):
        self.agents = {}
        self._load_agents()

    def _load_agents(self):
        """Dynamically load all available agents."""
        agent_modules = {
            "builder": "project_alpha.agents.execution.builder_agent",
            "automation": "project_alpha.agents.execution.automation_agent",
            "content": "project_alpha.agents.execution.content_agent"
        }

        for agent_name, module_path in agent_modules.items():
            try:
                module = importlib.import_module(module_path)
                agent_class_name = ''.join(word.capitalize() for word in agent_name.split('_')) + 'Agent'
                agent_class = getattr(module, agent_class_name)
                self.agents[agent_name] = agent_class()
            except (ImportError, AttributeError) as e:
                print(f"Warning: Could not load agent {agent_name}: {e}")

    def execute_task(self, task: Dict) -> Dict:
        """
        Execute a task by routing to the appropriate agent.

        Args:
            task: Task dictionary to execute

        Returns:
            Dictionary with status, output, and error fields
        """
        assigned_agent = task.get("assigned_agent", "builder")

        if assigned_agent not in self.agents:
            return {
                "status": "failed",
                "output": {},
                "error": f"Agent '{assigned_agent}' not found"
            }

        try:
            agent = self.agents[assigned_agent]
            result = agent.execute(task)

            if result.get("status") == "success":
                return {
                    "status": "success",
                    "output": result.get("output", {}),
                    "error": ""
                }
            else:
                return {
                    "status": "failed",
                    "output": {},
                    "error": result.get("error", "Unknown error")
                }
        except Exception as e:
            return {
                "status": "failed",
                "output": {},
                "error": f"Execution error: {str(e)}"
            }

    def execute_business_task(self, task: Dict, business: Dict) -> Dict:
        """
        Execute a task with business context awareness.

        Args:
            task: Task dictionary to execute
            business: Business dictionary for context

        Returns:
            Dictionary with status, output, and error fields
        """
        assigned_agent = task.get("assigned_agent", "builder")

        if assigned_agent not in self.agents:
            return {
                "status": "failed",
                "output": {},
                "error": f"Agent '{assigned_agent}' not found"
            }

        try:
            # Enhance task with business context
            enhanced_task = task.copy()
            enhanced_task["input"] = task.get("input", {}).copy()
            enhanced_task["input"]["business_context"] = {
                "idea": business["opportunity"]["idea"],
                "stage": business["stage"],
                "metrics": business["metrics"]
            }

            agent = self.agents[assigned_agent]
            result = agent.execute(enhanced_task)

            if result.get("status") == "success":
                return {
                    "status": "success",
                    "output": result.get("output", {}),
                    "error": ""
                }
            else:
                return {
                    "status": "failed",
                    "output": {},
                    "error": result.get("error", "Unknown error")
                }
        except Exception as e:
            return {
                "status": "failed",
                "output": {},
                "error": f"Execution error: {str(e)}"
            }

    def get_available_agents(self) -> list:
        """
        Get list of available agent names.

        Returns:
            List of agent names
        """
        return list(self.agents.keys())
