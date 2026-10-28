from dataclasses import dataclass, field

from app.agents.analyst import AnalystAgent
from app.agents.base import AgentResponse
from app.agents.extractor import ExtractorAgent
from app.agents.synthesizer import SynthesizerAgent
from app.agents.validator import ValidatorAgent

RULE = "-" * 40


@dataclass
class OrchestrationResult:
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
        """Plain-text version of the final report for the terminal."""
        if not self.final_report:
            return "No report generated."

        r = self.final_report
        lines = [
            "=" * 70,
            "NEXUSIQ INTELLIGENCE REPORT",
            str(r.get("report_title", "")),
            "=" * 70,
            f"\nOVERALL ASSESSMENT: {r.get('overall_assessment', 'N/A')}",
            "\nEXECUTIVE SUMMARY", RULE, r.get("executive_summary", ""),
            "\nFINANCIAL SNAPSHOT", RULE,
        ]

        for metric in r.get("financial_snapshot", {}).get("key_metrics", []):
            mark = "✓" if metric.get("verified") else "?"
            lines.append(f"  {mark} {metric.get('metric', '')}: {metric.get('value', '')}")

        lines += ["\nBUSINESS ANALYSIS", RULE, r.get("business_analysis", ""), "\nRISK LANDSCAPE", RULE]

        for risk in r.get("risk_landscape", []):
            lines.append(
                f"  [{risk.get('likelihood', '?')} likelihood / {risk.get('severity', '?')} severity] "
                f"{risk.get('risk', '')}"
            )
            if risk.get("comment"):
                lines.append(f"    → {risk['comment']}")

        lines += [
            "\nVALIDATION NOTES", RULE, r.get("validation_notes", ""),
            "\nOUTLOOK", RULE, r.get("outlook", ""),
            f"\nREPORT CONFIDENCE: {r.get('report_confidence', 'N/A')}",
            r.get("confidence_reasoning", ""),
            "=" * 70,
        ]
        return "\n".join(lines)


class Orchestrator:
    """Runs the agents in a fixed order: Extractor -> Analyst -> Validator -> Synthesizer."""

    def __init__(self):
        print("Initializing NexusIQ agent pipeline...")
        self.extractor = ExtractorAgent()
        self.analyst = AnalystAgent()
        self.validator = ValidatorAgent()
        self.synthesizer = SynthesizerAgent()
        print("All agents ready.")

    def analyze_document(self, document_name: str) -> OrchestrationResult:
        result = OrchestrationResult(task="full_document_analysis", document_name=document_name)

        print("\n[1/4] Extractor running...")
        extraction = self.extractor.extract(document_name=document_name)
        result.agent_responses.append(extraction)
        if not extraction.success:
            result.success = False
            result.error = "Extraction failed"
            return result
        result.extraction = extraction.structured_data or {}
        print(f"      extracted {len(result.extraction)} fields, tool calls: {extraction.tool_calls_made}")

        print("\n[2/4] Analyst running...")
        analysis = self.analyst.analyze(extraction_data=result.extraction, document_name=document_name)
        result.agent_responses.append(analysis)
        result.analysis = analysis.structured_data or {}
        print(f"      rating: {result.analysis.get('overall_rating', 'N/A')}, tool calls: {analysis.tool_calls_made}")

        print("\n[3/4] Validator running...")
        validation = self.validator.validate(
            extraction_data=result.extraction,
            analysis_data=result.analysis,
            document_name=document_name,
        )
        result.agent_responses.append(validation)
        result.validation = validation.structured_data or {}
        print(f"      status: {result.validation.get('validation_status', 'N/A')}, "
              f"tool calls: {validation.tool_calls_made}")

        print("\n[4/4] Synthesizer running...")
        synthesis = self.synthesizer.synthesize(
            extraction_data=result.extraction,
            analysis_data=result.analysis,
            validation_data=result.validation,
            document_name=document_name,
        )
        result.agent_responses.append(synthesis)
        result.final_report = synthesis.structured_data or {}
        print(f"      confidence: {result.final_report.get('report_confidence', 'N/A')}")

        return result
