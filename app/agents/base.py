import json
from dataclasses import dataclass, field
from typing import Callable, Optional

from openai import OpenAI

from app.core.config import settings


@dataclass
class AgentResponse:
    agent_name: str
    output: str
    structured_data: Optional[dict]
    tool_calls_made: list[str] = field(default_factory=list)
    success: bool = True
    error: Optional[str] = None


class BaseAgent:
    """Runs the chat + tool-calling loop. Each agent only brings its prompt and tools."""

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
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message},
        ]
        tool_calls_made = []

        for _ in range(max_tool_iterations):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools or None,
                temperature=settings.DEFAULT_TEMPERATURE,
            )
            message = response.choices[0].message

            if not message.tool_calls:
                return AgentResponse(
                    agent_name=self.name,
                    output=message.content,
                    structured_data=self._try_parse_json(message.content),
                    tool_calls_made=tool_calls_made,
                )

            messages.append(message)
            for tool_call in message.tool_calls:
                name = tool_call.function.name
                tool_calls_made.append(name)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(self._call_tool(name, tool_call.function.arguments)),
                })

        return AgentResponse(
            agent_name=self.name,
            output="Agent reached maximum tool iterations without a final answer.",
            structured_data=None,
            tool_calls_made=tool_calls_made,
            success=False,
            error="max_iterations_exceeded",
        )

    def _call_tool(self, name: str, arguments: str):
        args = json.loads(arguments)
        if name not in self.tool_functions:
            return f"Error: tool '{name}' not implemented."
        try:
            return self.tool_functions[name](**args)
        except Exception as e:
            return f"Error running tool: {str(e)}"

    def _try_parse_json(self, text: str) -> dict | None:
        # Models like to wrap JSON in ``` fences or add a sentence around it,
        # so cut it down to the outermost braces before parsing.
        if not text:
            return None

        cleaned = text.strip()
        fence = "```json" if "```json" in cleaned else "```" if "```" in cleaned else None
        if fence:
            start = cleaned.find(fence) + len(fence)
            end = cleaned.find("```", start)
            if end != -1:
                cleaned = cleaned[start:end].strip()

        first, last = cleaned.find("{"), cleaned.rfind("}")
        if first != -1 and last > first:
            cleaned = cleaned[first:last + 1]

        try:
            return json.loads(cleaned)
        except (json.JSONDecodeError, TypeError):
            return None
