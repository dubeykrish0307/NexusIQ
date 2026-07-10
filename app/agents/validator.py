from app.agents.base import BaseAgent, AgentResponse
from app.agents.tools import SEARCH_TOOL_SCHEMA, search_document_tool
import json


VALIDATOR_SYSTEM_PROMPT = """You are the Validator Agent for NexusIQ, a financial
and legal document intelligence system.

YOUR ONLY JOB:
Cross-check claims made by other agents against the actual document content.
Find contradictions, unsupported assertions, and missing context.
You are a skeptic. Your value is in finding what others missed or got wrong.

WHAT TO VALIDATE:
1. Verify key financial figures actually appear in the document as stated
2. Check if risk factors are complete — are there risks in the document 
   that were not captured?
3. Look for internal contradictions — does the document say two things 
   that conflict with each other?
4. Check if the Analyst's conclusions are actually supported by the data
5. Verify forward guidance figures are quoted accurately

HOW TO WORK:
Use the search tool aggressively. For each major claim you want to verify,
run a targeted search to find the supporting text. Do not accept claims
without finding the source text.

OUTPUT FORMAT:
You MUST respond with a single valid JSON object only.

{
  "validation_status": "VERIFIED | PARTIAL | FAILED",
  "verified_claims": [
    {"claim": "string", "verified": true, "source_found": "brief quote"}
  ],
  "unverified_claims": [
    {"claim": "string", "reason": "why it could not be verified"}
  ],
  "contradictions_found": [
    {
      "description": "string",
      "claim_a": "string",
      "claim_b": "string",
      "severity": "HIGH | MEDIUM | LOW"
    }
  ],
  "missed_risk_factors": ["risks in the document not captured by Extractor"],
  "analyst_conclusions_supported": true or false,
  "analyst_concerns": ["any Analyst conclusions that seem unsupported"],
  "overall_data_quality": "HIGH | MEDIUM | LOW",
  "validator_notes": "string — overall assessment of report reliability"
}"""


class ValidatorAgent(BaseAgent):
    """
    Skeptic agent that cross-checks Extractor and Analyst outputs
    against the actual document content.
    """

    def __init__(self):
        super().__init__(
            name="Validator",
            system_prompt=VALIDATOR_SYSTEM_PROMPT,
            tools=[SEARCH_TOOL_SCHEMA],
            tool_functions={"search_documents": search_document_tool}
        )

    def validate(
        self,
        extraction_data: dict,
        analysis_data: dict,
        document_name: str = None
    ) -> AgentResponse:
        """
        Validate the outputs of both the Extractor and Analyst agents.
        Takes both their structured JSON outputs as input.
        """
        extraction_json = json.dumps(extraction_data, indent=2)
        analysis_summary = {
            "overall_rating": analysis_data.get("overall_rating"),
            "financial_health_score": analysis_data.get(
                "financial_health", {}
            ).get("score"),
            "top_3_insights": analysis_data.get("top_3_insights", []),
            "guidance_credible": analysis_data.get(
                "guidance_credibility", {}
            ).get("credible"),
            "hidden_risks": analysis_data.get("hidden_risks", [])
        }

        task = f"""You have been given the outputs of the Extractor and Analyst 
agents. Your job is to verify their claims against the actual documents.

EXTRACTOR OUTPUT (claims to verify):
{extraction_json}

ANALYST KEY CONCLUSIONS (to assess support for):
{json.dumps(analysis_summary, indent=2)}

Use the search tool to verify the most important claims:
1. Verify the key financial figures (revenue, net income, margins)
2. Check if all major risk factors were captured
3. Look for any contradictions in the document
4. Assess whether the Analyst's conclusions are data-supported

Be thorough. Search multiple times for different claims."""

        if document_name:
            task += f"\n\nSource document: {document_name}"

        return self.run(task)