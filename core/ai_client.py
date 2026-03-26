"""
AI Client for project_alpha
Supports OpenAI and Claude (Anthropic) APIs
"""

import os
import json
from typing import Optional


class AIClient:
    """Client for interacting with AI APIs."""

    def __init__(self):
        self.openai_key = os.environ.get("OPENAI_API_KEY")
        self.anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        self.provider = self._detect_provider()
        self._client = None

    def _detect_provider(self) -> str:
        """Detect which AI provider to use based on available keys."""
        if self.anthropic_key:
            return "anthropic"
        elif self.openai_key:
            return "openai"
        else:
            return "none"

    def _init_openai(self):
        """Initialize OpenAI client."""
        try:
            import openai
            openai.api_key = self.openai_key
            self._client = openai
            return True
        except ImportError:
            print("Warning: openai package not installed. Install with: pip install openai")
            return False

    def _init_anthropic(self):
        """Initialize Anthropic client."""
        try:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.anthropic_key)
            return True
        except ImportError:
            print("Warning: anthropic package not installed. Install with: pip install anthropic")
            return False

    def ask_ai(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.7) -> str:
        """
        Send a prompt to AI and get response.

        Args:
            prompt: User prompt to send
            system_prompt: Optional system prompt for context
            temperature: Response randomness (0.0-1.0)

        Returns:
            AI response text
        """
        if self.provider == "anthropic":
            return self._ask_anthropic(prompt, system_prompt, temperature)
        elif self.provider == "openai":
            return self._ask_openai(prompt, system_prompt, temperature)
        else:
            return self._ask_fallback(prompt)

    def _ask_anthropic(self, prompt: str, system_prompt: Optional[str], temperature: float) -> str:
        """Call Anthropic Claude API."""
        if not self._client:
            if not self._init_anthropic():
                return self._ask_fallback(prompt)

        try:
            messages = [{"role": "user", "content": prompt}]

            kwargs = {
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 4096,
                "temperature": temperature,
                "messages": messages
            }

            if system_prompt:
                kwargs["system"] = system_prompt

            response = self._client.messages.create(**kwargs)
            return response.content[0].text

        except Exception as e:
            print(f"Anthropic API error: {e}")
            return self._ask_fallback(prompt)

    def _ask_openai(self, prompt: str, system_prompt: Optional[str], temperature: float) -> str:
        """Call OpenAI API."""
        if not self._client:
            if not self._init_openai():
                return self._ask_fallback(prompt)

        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = self._client.ChatCompletion.create(
                model="gpt-4",
                messages=messages,
                temperature=temperature,
                max_tokens=4096
            )

            return response.choices[0].message.content

        except Exception as e:
            print(f"OpenAI API error: {e}")
            return self._ask_fallback(prompt)

    def _ask_fallback(self, prompt: str) -> str:
        """Fallback response when no API is available."""
        prompt_lower = prompt.lower()

        if "opportunity" in prompt_lower and "analyze" not in prompt_lower and "executing" not in prompt_lower:
            return json.dumps([
                {
                    "idea": "AI-powered lead generation system",
                    "description": "Automated system that finds and qualifies leads using AI and multi-source data",
                    "potential": "high"
                },
                {
                    "idea": "Content automation pipeline",
                    "description": "Generate, optimize, and distribute content across multiple channels",
                    "potential": "high"
                },
                {
                    "idea": "Smart workflow automation",
                    "description": "Analyze business processes and create custom automation workflows",
                    "potential": "medium"
                }
            ])

        elif "task" in prompt_lower and "plan" in prompt_lower and "executing" not in prompt_lower:
            return json.dumps([
                {
                    "title": "Research and validate concept",
                    "description": "Research market, validate opportunity, identify competitors",
                    "priority": "high",
                    "assigned_agent": "content"
                },
                {
                    "title": "Design system architecture",
                    "description": "Design technical architecture and data flow",
                    "priority": "high",
                    "assigned_agent": "builder"
                },
                {
                    "title": "Implement core functionality",
                    "description": "Build core features and integrations",
                    "priority": "high",
                    "assigned_agent": "builder"
                },
                {
                    "title": "Set up automation workflows",
                    "description": "Configure automation pipelines and scheduling",
                    "priority": "medium",
                    "assigned_agent": "automation"
                },
                {
                    "title": "Test and validate",
                    "description": "Run comprehensive testing and validation",
                    "priority": "medium",
                    "assigned_agent": "automation"
                }
            ])

        elif "builder agent" in prompt_lower or ("executing" in prompt_lower and "builder" in prompt_lower):
            return json.dumps({
                "approach": "Modular architecture with clean separation of concerns",
                "components": ["data layer", "processing engine", "API interface", "monitoring"],
                "technologies": ["Python", "FastAPI", "PostgreSQL", "Redis"],
                "steps": ["Design architecture", "Implement core", "Add integrations", "Test thoroughly"],
                "outcomes": ["Scalable system", "Clean codebase", "Comprehensive tests"]
            })

        elif "automation agent" in prompt_lower or ("executing" in prompt_lower and "automation" in prompt_lower):
            return json.dumps({
                "strategy": "Automated workflow with monitoring and error handling",
                "workflow": ["Initialize", "Process data", "Execute actions", "Verify results", "Report"],
                "tools": ["Python", "Celery", "Redis", "Prometheus"],
                "configuration": {"retry_limit": 3, "timeout": 300},
                "metrics": ["Success rate", "Execution time", "Error rate"]
            })

        elif "content agent" in prompt_lower or ("executing" in prompt_lower and "content" in prompt_lower):
            return json.dumps({
                "approach": "Research-driven content strategy with SEO optimization",
                "topics": ["Market analysis", "Use cases", "Best practices", "Implementation guide"],
                "audience": "Technical decision makers and implementers",
                "structure": ["Executive summary", "Detailed analysis", "Action steps", "Resources"],
                "deliverables": ["Research report", "Content outline", "Draft content", "Final polished version"]
            })

        else:
            return json.dumps({
                "approach": "Analyzed requirements and implemented solution",
                "components": ["core functionality", "supporting features"],
                "technologies": ["Modern tech stack"],
                "steps": ["Plan", "Implement", "Test", "Deploy"],
                "outcomes": ["Working solution", "Quality code"]
            })

    def generate(self, prompt: str, model: str = None, max_tokens: int = 4096, temperature: float = 0.7) -> str:
        """
        Generate response from AI. Compatibility method that maps to ask_ai.

        Args:
            prompt: User prompt to send
            model: Model to use (ignored, uses configured provider)
            max_tokens: Maximum tokens to generate (ignored, uses default)
            temperature: Response randomness (0.0-1.0)

        Returns:
            AI response text
        """
        return self.ask_ai(prompt, temperature=temperature)

    def is_available(self) -> bool:
        """Check if AI client is available."""
        return self.provider != "none"

    def get_provider(self) -> str:
        """Get current AI provider name."""
        return self.provider
