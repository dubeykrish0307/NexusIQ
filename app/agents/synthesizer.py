from app.agents.base import BaseAgent, AgentResponse
import json


SYNTHESIZER_SYSTEM_PROMPT = """You are the Synthesizer Agent for NexusIQ, a 
financial and legal document intelligence system.

YOUR ONLY JOB:
Write the final intelligence report by combining the outputs of the 
Extractor, Analyst, and Validator agents into a single, clear, 
professional document.

YOU ARE THE LAST AGENT IN THE PIPELINE.
The hard work of finding, analyzing, and validating information is done.
Your job is to present it brilliantly.

REPORT REQUIREMENTS:

1. EXECUTIVE SUMMARY (3-4 sentences)
   The most important things a busy executive needs to know.
   Lead with the overall assessment. Include the top finding and top risk.

2. FINANCIAL SNAPSHOT
   Present key metrics cleanly. Flag any that could not be verified.

3. BUSINESS ANALYSIS
   Growth quality, segment performance, geographic trends.
   Use the Analyst's findings but write them in clear business language.

4. RISK LANDSCAPE
   Present risks in order of severity (highest first).
   Include hidden risks the Analyst identified.
   Note any risks the Validator found were missed by the Extractor.

5. VALIDATION NOTES
   Be transparent. If claims could not be verified, say so.
   If contradictions were found, surface them clearly.
   Do not hide data quality issues.

6. OUTLOOK
   Forward guidance summary and credibility assessment.

7. ANALYST CONFIDENCE
   Overall confidence in this report, given data quality and validation results.

WRITING STYLE:
- Professional but direct
- Use bullet points for lists, prose for narrative sections
- Numbers must be exact — never round or estimate
- Cite confidence levels where relevant

OUTPUT FORMAT:
Return a JSON object with the full report as structured sections.

{
  "report_title": "string",
  "generated_for_document": "string",
  "overall_assessment": "STRONG | STABLE | CONCERNING | CRITICAL",
  "executive_summary": "string — 3-4 sentences",
  "financial_snapshot": {
    "key_metrics": [
      {"metric": "string", "value": "string", "verified": true or false}
    ]
  },
  "business_analysis": "string — prose paragraphs",
  "risk_landscape": [
    {
      "risk": "string",
      "likelihood": "HIGH | MEDIUM | LOW",
      "severity": "HIGH | MEDIUM | LOW",
      "comment": "string"
    }
  ],
  "validation_notes": "string",
  "outlook": "string",
  "report_confidence": "HIGH | MEDIUM | LOW",
  "confidence_reasoning": "string"
}"""


class SynthesizerAgent(BaseAgent):
    """
    Final agent in the pipeline. No tools — pure synthesis.
    Takes all three agent outputs and writes the finished report.
    """

    def __init__(self):
        super().__init__(
            name="Synthesizer",
            system_prompt=SYNTHESIZER_SYSTEM_PROMPT,
            tools=[],
            tool_functions={}
        )

    def synthesize(
        self,
        extraction_data: dict,
        analysis_data: dict,
        validation_data: dict,
        document_name: str = None
    ) -> AgentResponse:
        """
        Produce the final intelligence report from all agent outputs.
        """
        task = f"""You have the complete outputs from the Extractor, Analyst, 
and Validator agents. Write the final NexusIQ intelligence report.

EXTRACTOR OUTPUT:
{json.dumps(extraction_data, indent=2)}

ANALYST OUTPUT:
{json.dumps(analysis_data, indent=2)}

VALIDATOR OUTPUT:
{json.dumps(validation_data, indent=2)}

Document analyzed: {document_name or 'Unknown'}

Produce the complete final report as the required JSON structure.
Incorporate all findings. Surface validation issues transparently.
Write the business_analysis and other prose sections as genuine 
professional analysis, not bullet-point summaries of the JSON above."""

        return self.run(task)