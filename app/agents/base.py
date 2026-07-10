import json
from dataclasses import dataclass, field
from typing import Optional, Callable
from openai import OpenAI

from app.core.config import settings


@dataclass
class AgentResponse:
    """
    Standardized output from any agent.
    Every agent, regardless of its specialty, returns this same shape —
    so the Orchestrator can handle all of them identically.
    """

    agent_name: str
    output: str
    structured_data: Optional[dict]
    tool_calls_made: list[str] = field(default_factory=list)
    success: bool = True
    error: Optional[str] = None


class BaseAgent:
    """
    Shared foundation for all NexusIQ agents.
    Handles the LLM call loop, including tool/function calling,
    so each specialized agent only needs to define its prompt and tools.
    """

    def __init__(
        self,
        name: str,
        system_prompt: str,
        tools: list[dict] = None,
        tool_functions: dict[str, Callable] = None,
        model: str = None,
    ):
        self.name = name
        self.system_prompt = system_prompt
        self.tools = tools or []
        self.tool_functions = tool_functions or {}
        self.model = model or settings.CHAT_MODEL
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def run(self, user_message: str, max_tool_iterations: int = 3) -> AgentResponse:
        """
        Run the agent on a single task. Handles the full tool-calling loop:
        the model can call tools multiple times before giving a final answer.
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message},
        ]

        tool_calls_made = []

        for iteration in range(max_tool_iterations):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools if self.tools else None,
                temperature=settings.DEFAULT_TEMPERATURE,
            )

            message = response.choices[0].message

            if not message.tool_calls:
                return AgentResponse(
                    agent_name=self.name,
                    output=message.content,
                    structured_data=self._try_parse_json(message.content),
                    tool_calls_made=tool_calls_made,
                    success=True,
                )

            messages.append(message)

            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)

                tool_calls_made.append(function_name)

                if function_name not in self.tool_functions:
                    result = f"Error: tool '{function_name}' not implemented."
                else:
                    try:
                        result = self.tool_functions[function_name](**function_args)
                    except Exception as e:
                        result = f"Error running tool: {str(e)}"

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(result),
                    }
                )

        return AgentResponse(
            agent_name=self.name,
            output="Agent reached maximum tool iterations without a final answer.",
            structured_data=None,
            tool_calls_made=tool_calls_made,
            success=False,
            error="max_iterations_exceeded",
        )

    def _try_parse_json(self, text: str) -> dict | None:
        """
                Robustly parse JSON from agent output.

                Models sometimes wrap JSON in markdown code blocks like:
        ```json
                    { ... }
        ```
                We strip those before parsing. We also handle the case where
                the model adds a brief explanation before or after the JSON block.
        """
        if not text:
            return None

        cleaned = text.strip()

        if "```json" in cleaned:
            start = cleaned.find("```json") + 7
            end = cleaned.find("```", start)
            if end != -1:
                cleaned = cleaned[start:end].strip()
        elif "```" in cleaned:
            start = cleaned.find("```") + 3
            end = cleaned.find("```", start)
            if end != -1:
                cleaned = cleaned[start:end].strip()

        brace_start = cleaned.find("{")
        brace_end = cleaned.rfind("}")
        if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
            cleaned = cleaned[brace_start : brace_end + 1]

        try:
            return json.loads(cleaned)
        except (json.JSONDecodeError, TypeError):
            return None
