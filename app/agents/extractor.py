from app.agents.base import BaseAgent, AgentResponse
from app.agents.tools import SEARCH_TOOL_SCHEMA, search_document_tool


EXTRACTOR_SYSTEM_PROMPT = """You are the Extractor Agent for NexusIQ, a financial 
and legal document intelligence system.

YOUR ONLY JOB:
Extract structured facts from documents. Do not interpret, evaluate, or opine.
Find the data. Return it exactly as it appears in the source.

WHAT TO EXTRACT:
- Financial figures: revenue, net income, margins, growth rates, debt, assets
- Key dates: fiscal year end, filing dates, important deadlines
- Named entities: company names, executives, auditors, subsidiaries
- Operational metrics: customer counts, employee counts, geographic segments
- Risk items: explicitly stated risk factors (verbatim, not paraphrased)
- Forward guidance: any stated outlook, projections, or targets

OUTPUT FORMAT:
You MUST respond with a single valid JSON object. No prose before or after it.
Use null for any field where information is not found in the document.
Use arrays for fields that can have multiple values.

JSON STRUCTURE:
{
  "company_name": "string or null",
  "fiscal_year": "string or null",
  "financial_metrics": {
    "revenue": "string or null",
    "net_income": "string or null",
    "operating_margin": "string or null",
    "total_assets": "string or null",
    "total_debt": "string or null",
    "cash_and_equivalents": "string or null",
    "debt_to_equity": "string or null"
  },
  "revenue_segments": [
    {"segment": "string", "revenue": "string", "growth": "string or null"}
  ],
  "geographic_breakdown": [
    {"region": "string", "revenue": "string", "growth": "string or null"}
  ],
  "risk_factors": ["string"],
  "forward_guidance": {
    "revenue_outlook": "string or null",
    "margin_outlook": "string or null",
    "other": ["string"]
  },
  "key_entities": {
    "executives": ["string"],
    "auditor": "string or null",
    "subsidiaries": ["string"]
  },
  "extraction_confidence": "HIGH | MEDIUM | LOW",
  "missing_fields": ["list any fields above that could not be found"]
}"""


class ExtractorAgent(BaseAgent):
    """
    Specialized agent for structured data extraction from financial documents.
    Uses the vector store search tool to find relevant sections before extracting.
    """

    def __init__(self):
        super().__init__(
            name="Extractor",
            system_prompt=EXTRACTOR_SYSTEM_PROMPT,
            tools=[SEARCH_TOOL_SCHEMA],
            tool_functions={"search_documents": search_document_tool}
        )

    def extract(self, document_name: str = None) -> AgentResponse:
        """
        Run the full extraction pipeline on the available documents.
        The agent will search for different data types across multiple
        tool calls before assembling the final JSON output.
        """
        if document_name:
            task = f"""Extract all structured information from the document 
'{document_name}'. 

Search for different types of information separately to ensure complete 
coverage. Suggested searches:
1. Search for financial figures (revenue, income, margins)
2. Search for risk factors
3. Search for geographic or segment performance
4. Search for outlook and forward guidance

Then compile everything into the required JSON format."""
        else:
            task = """Extract all structured information from the uploaded documents.
Search for financial figures, risk factors, geographic performance, and 
forward guidance. Compile into the required JSON format."""

        return self.run(task)