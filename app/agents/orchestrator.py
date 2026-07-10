import json
from dataclasses import dataclass, field
from app.agents.base import AgentResponse
from app.agents.extractor import ExtractorAgent
from app.agents.analyst import AnalystAgent
from app.agents.validator import ValidatorAgent
from app.agents.synthesizer import SynthesizerAgent


@dataclass
class OrchestrationResult:
    """
    The complete output of a full multi-agent analysis run.
    Contains every agent's individual output plus the final report.
    """
    task: str
    document_name: str
    extraction: dict = field(default_factory=dict)
    analysis: dict = field(default_factory=dict)
    validation: dict = field(default_factory=dict)
    final_report: dict = field(default_factory=dict)
    agent_responses: list[AgentResponse] = field(default_factory=list)
    success: bool = True
    error: str = None

    def get_report_as_text(self) -> str:
        """
        Convert the structured final report into a human-readable
        text format for display in terminal or simple text contexts.
        """
        if not self.final_report:
            return "No report generated."

        r = self.final_report
        lines = []

        lines.append("=" * 70)
        lines.append(f"NEXUSIQ INTELLIGENCE REPORT")
        lines.append(f"{r.get('report_title', '')}")
        lines.append("=" * 70)

        lines.append(f"\nOVERALL ASSESSMENT: {r.get('overall_assessment', 'N/A')}")
        lines.append(f"\nEXECUTIVE SUMMARY")
        lines.append("-" * 40)
        lines.append(r.get('executive_summary', ''))

        lines.append(f"\nFINANCIAL SNAPSHOT")
        lines.append("-" * 40)
        snapshot = r.get('financial_snapshot', {})
        for metric in snapshot.get('key_metrics', []):
            verified = "✓" if metric.get('verified') else "?"
            lines.append(
                f"  {verified} {metric.get('metric', '')}: "
                f"{metric.get('value', '')}"
            )

        lines.append(f"\nBUSINESS ANALYSIS")
        lines.append("-" * 40)
        lines.append(r.get('business_analysis', ''))

        lines.append(f"\nRISK LANDSCAPE")
        lines.append("-" * 40)
        for risk in r.get('risk_landscape', []):
            lines.append(
                f"  [{risk.get('likelihood','?')} likelihood / "
                f"{risk.get('severity','?')} severity] "
                f"{risk.get('risk', '')}"
            )
            if risk.get('comment'):
                lines.append(f"    → {risk.get('comment', '')}")

        lines.append(f"\nVALIDATION NOTES")
        lines.append("-" * 40)
        lines.append(r.get('validation_notes', ''))

        lines.append(f"\nOUTLOOK")
        lines.append("-" * 40)
        lines.append(r.get('outlook', ''))

        lines.append(f"\nREPORT CONFIDENCE: {r.get('report_confidence', 'N/A')}")
        lines.append(r.get('confidence_reasoning', ''))
        lines.append("=" * 70)

        return "\n".join(lines)


class Orchestrator:
    """
    Coordinates all four NexusIQ agents in a fixed pipeline:
    Extractor → Analyst → Validator → Synthesizer

    Each agent's output feeds the next. The final result is a
    structured intelligence report with full audit trail.
    """

    def __init__(self):
        print("Initializing NexusIQ agent pipeline...")
        self.extractor = ExtractorAgent()
        self.analyst = AnalystAgent()
        self.validator = ValidatorAgent()
        self.synthesizer = SynthesizerAgent()
        print("All agents ready.")

    def analyze_document(self, document_name: str) -> OrchestrationResult:
        """
        Run the full four-agent pipeline on a document.
        Returns a complete OrchestrationResult with every agent's
        output and the final synthesized report.
        """
        result = OrchestrationResult(
            task="full_document_analysis",
            document_name=document_name
        )

        print(f"\n[1/4] Extractor Agent running...")
        extraction_response = self.extractor.extract(
            document_name=document_name
        )
        result.agent_responses.append(extraction_response)

        if not extraction_response.success:
            result.success = False
            result.error = "Extraction failed"
            return result

        extraction_data = extraction_response.structured_data or {}
        result.extraction = extraction_data
        print(f"      ✓ Extracted {len(extraction_data)} top-level fields. "
              f"Tool calls: {extraction_response.tool_calls_made}")

        print(f"\n[2/4] Analyst Agent running...")
        analysis_response = self.analyst.analyze(
            extraction_data=extraction_data,
            document_name=document_name
        )
        result.agent_responses.append(analysis_response)

        analysis_data = analysis_response.structured_data or {}
        result.analysis = analysis_data
        print(f"      ✓ Analysis complete. "
              f"Rating: {analysis_data.get('overall_rating', 'N/A')}. "
              f"Tool calls: {analysis_response.tool_calls_made}")

        print(f"\n[3/4] Validator Agent running...")
        validation_response = self.validator.validate(
            extraction_data=extraction_data,
            analysis_data=analysis_data,
            document_name=document_name
        )
        result.agent_responses.append(validation_response)

        validation_data = validation_response.structured_data or {}
        result.validation = validation_data
        print(f"      ✓ Validation complete. "
              f"Status: {validation_data.get('validation_status', 'N/A')}. "
              f"Tool calls: {validation_response.tool_calls_made}")

        print(f"\n[4/4] Synthesizer Agent running...")
        synthesis_response = self.synthesizer.synthesize(
            extraction_data=extraction_data,
            analysis_data=analysis_data,
            validation_data=validation_data,
            document_name=document_name
        )
        result.agent_responses.append(synthesis_response)

        final_report = synthesis_response.structured_data or {}
        result.final_report = final_report
        print(f"      ✓ Report generated. "
              f"Confidence: {final_report.get('report_confidence', 'N/A')}.")

        return result