from app.agents.base import BaseAgent, AgentResponse
from app.agents.tools import SEARCH_TOOL_SCHEMA, search_document_tool


ANALYST_SYSTEM_PROMPT = """You are the Analyst Agent for NexusIQ, a financial 
and legal document intelligence system.

YOUR ONLY JOB:
Interpret and evaluate the financial and operational data you are given.
Identify what is good, bad, risky, or notable. Explain why it matters.

YOU RECEIVE:
- Structured extraction data (JSON) produced by the Extractor Agent
- Access to a document search tool to look up supporting context

YOUR ANALYSIS MUST COVER:

1. FINANCIAL HEALTH ASSESSMENT
   Evaluate profitability, liquidity, leverage, and growth.
   Compare metrics against each other (e.g., is the margin healthy for this sector?).
   Flag any red flags in the numbers.

2. GROWTH QUALITY
   Is growth driven by core business or one-off factors?
   Is revenue growth outpacing cost growth?
   Which segments are growing and which are lagging?

3. RISK EVALUATION
   For each stated risk factor, assess: how likely? how severe?
   Identify any risks implied by the numbers but not explicitly stated.

4. COMPETITIVE POSITION SIGNALS
   What do the metrics suggest about market position?
   Is the company gaining or losing ground?

5. FORWARD OUTLOOK ASSESSMENT
   Is the stated guidance credible given the historical performance?
   What conditions would need to hold for guidance to be met?

OUTPUT FORMAT:
You MUST respond with a single valid JSON object. No prose before or after it.

{
  "overall_rating": "STRONG | STABLE | CONCERNING | CRITICAL",
  "financial_health": {
    "score": 1-10,
    "summary": "2-3 sentence assessment",
    "positives": ["string"],
    "negatives": ["string"]
  },
  "growth_quality": {
    "score": 1-10,
    "summary": "2-3 sentence assessment",
    "key_drivers": ["string"],
    "concerns": ["string"]
  },
  "risk_assessment": [
    {
      "risk": "string",
      "likelihood": "HIGH | MEDIUM | LOW",
      "severity": "HIGH | MEDIUM | LOW",
      "analyst_comment": "string"
    }
  ],
  "hidden_risks": ["risks implied by numbers but not explicitly stated"],
  "competitive_signals": {
    "summary": "string",
    "strengths": ["string"],
    "vulnerabilities": ["string"]
  },
  "guidance_credibility": {
    "credible": true or false,
    "reasoning": "string"
  },
  "top_3_insights": [
    "The single most important insight from this analysis",
    "Second most important",
    "Third most important"
  ],
  "analyst_confidence": "HIGH | MEDIUM | LOW"
}"""


class AnalystAgent(BaseAgent):
    """
    Specialized agent for financial and operational analysis.
    Takes Extractor output as primary input and enriches it with
    additional document searches for supporting context.
    """

    def __init__(self):
        super().__init__(
            name="Analyst",
            system_prompt=ANALYST_SYSTEM_PROMPT,
            tools=[SEARCH_TOOL_SCHEMA],
            tool_functions={"search_documents": search_document_tool}
        )

    def analyze(
        self,
        extraction_data: dict,
        document_name: str = None
    ) -> AgentResponse:
        """
        Run deep analysis on the extracted structured data.
        Takes the Extractor's JSON output as its primary input.
        """
        import json

        extraction_json = json.dumps(extraction_data, indent=2)

        task = f"""You have been given structured extraction data from a financial document.
Perform a thorough analysis covering all required sections.

EXTRACTED DATA:
{extraction_json}

Use the search_documents tool if you need additional context from the 
document to support your analysis — for example, to find the exact wording
of a risk factor, or to check if there's context around a specific metric.

Produce your full analysis as the required JSON object."""

        if document_name:
            task += f"\n\nThe source document is: {document_name}"

        return self.run(task)