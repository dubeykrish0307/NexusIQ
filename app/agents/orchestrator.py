from dataclasses import dataclass, field
from app.agents.base import AgentResponse


@dataclass
class OrchestrationResult:
    """
    The final, combined output of running multiple agents on a task.
    This is what the API and UI will eventually receive.
    """
    task: str
    agent_responses: list[AgentResponse]
    final_report: str = ""


class Orchestrator:
    """
    Coordinates multiple specialized agents to complete complex tasks.
    Day 6: skeleton only — agent registry and the run loop.
    Day 7-8: Extractor, Analyst, Validator, Synthesizer get registered here.
    """

    def __init__(self):
        self.agents = {}

    def register_agent(self, agent_key: str, agent):
        """
        Add an agent to the orchestrator's available roster.
        Called once at startup for each specialized agent we build.
        """
        self.agents[agent_key] = agent
        print(f"  Registered agent: {agent_key}")

    def list_agents(self) -> list[str]:
        """Return the names of all currently registered agents."""
        return list(self.agents.keys())