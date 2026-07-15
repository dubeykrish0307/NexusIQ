import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import requests
import json
import time
from datetime import datetime

API_BASE = "http://localhost:8000"

st.set_page_config(
    page_title="NexusIQ",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1a1a2e;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: #f8f9fa;
        border-radius: 12px;
        padding: 1.2rem;
        border-left: 4px solid #4361ee;
        margin-bottom: 1rem;
    }
    .agent-step {
        background: #eef2ff;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        margin: 0.4rem 0;
        border-left: 3px solid #4361ee;
        font-size: 0.9rem;
    }
    .risk-high { border-left: 4px solid #e63946; }
    .risk-medium { border-left: 4px solid #f4a261; }
    .risk-low { border-left: 4px solid #2a9d8f; }
    .verified { color: #2a9d8f; font-weight: 500; }
    .unverified { color: #e63946; font-weight: 500; }
    .assessment-STRONG { color: #2a9d8f; font-weight: 700; }
    .assessment-STABLE { color: #4361ee; font-weight: 700; }
    .assessment-CONCERNING { color: #f4a261; font-weight: 700; }
    .assessment-CRITICAL { color: #e63946; font-weight: 700; }
</style>
""", unsafe_allow_html=True)


def api_get(endpoint: str) -> dict | None:
    """Make a GET request to the API. Returns None on failure."""
    try:
        response = requests.get(f"{API_BASE}{endpoint}", timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to NexusIQ API. "
                 "Make sure the server is running on port 8000.")
        return None


def api_post(endpoint: str, data: dict = None,
             files: dict = None) -> dict | None:
    """Make a POST request to the API."""
    try:
        if files:
            response = requests.post(
                f"{API_BASE}{endpoint}", files=files, timeout=30
            )
        else:
            response = requests.post(
                f"{API_BASE}{endpoint}",
                json=data,
                timeout=120
            )
        if response.status_code == 200:
            return response.json()
        st.error(f"API error {response.status_code}: "
                 f"{response.json().get('detail', 'Unknown error')}")
        return None
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to NexusIQ API.")
        return None
    except requests.exceptions.Timeout:
        st.error("Request timed out. The analysis pipeline "
                 "can take 60-90 seconds — please try again.")
        return None
    
def render_sidebar():
    """Sidebar: navigation, document list, quick stats."""
    with st.sidebar:
        st.markdown("## 🧠 NexusIQ")
        st.markdown("*Multi-agent document intelligence*")
        st.divider()

        page = st.radio(
            "Navigate",
            ["📤 Upload & Ingest",
             "💬 Ask Questions",
             "🔬 Deep Analysis",
             "📊 Dashboard"],
            label_visibility="collapsed"
        )

        st.divider()
        st.markdown("**Stored Documents**")

        doc_data = api_get("/documents/list")
        if doc_data and doc_data["total_documents"] > 0:
            for doc in doc_data["documents"]:
                st.markdown(f"📄 `{doc}`")
            st.caption(
                f"{doc_data['total_documents']} documents · "
                f"{doc_data['total_chunks']} chunks"
            )
        else:
            st.caption("No documents uploaded yet.")

        st.divider()
        stats = api_get("/analysis/stats")
        if stats:
            col1, col2 = st.columns(2)
            col1.metric("Questions", stats["total_questions"])
            col2.metric("Analyses", stats["total_analyses"])

    return page.split(" ", 1)[1]

def render_upload_page():
    """Page 1: Upload documents and ingest them."""
    st.markdown(
        '<div class="main-header">📤 Upload Document</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="sub-header">Upload PDF, DOCX, or TXT files '
        'to add them to the NexusIQ knowledge base.</div>',
        unsafe_allow_html=True
    )

    uploaded_file = st.file_uploader(
        "Drop a document here",
        type=["pdf", "docx", "txt", "md"],
        help="Maximum file size: 50MB"
    )

    if uploaded_file is not None:
        col1, col2, col3 = st.columns([2, 1, 1])
        col1.info(f"**{uploaded_file.name}** "
                  f"({uploaded_file.size / 1024:.1f} KB)")

        if col2.button("⚡ Ingest Document", type="primary"):
            with st.spinner("Parsing, chunking, and embedding..."):
                files = {"file": (
                    uploaded_file.name,
                    uploaded_file.getvalue(),
                    uploaded_file.type
                )}
                result = api_post("/documents/upload", files=files)

            if result:
                st.success(f"✅ {result['message']}")
                col_a, col_b, col_c, col_d = st.columns(4)
                col_a.metric(
                    "Category", result["document_category"]
                )
                col_b.metric(
                    "Chunks created", result["chunks_created"]
                )
                col_c.metric(
                    "Detected title",
                    result.get("detected_title", "N/A")[:20]
                    if result.get("detected_title") else "N/A"
                )
                col_d.metric(
                    "Detected date",
                    result.get("detected_date", "N/A")
                )
                st.rerun()


def render_ask_page():
    """Page 2: Ask questions via RAG."""
    st.markdown(
        '<div class="main-header">💬 Ask Questions</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="sub-header">Ask anything about your uploaded '
        'documents. Answers are grounded in source text with '
        'citations.</div>',
        unsafe_allow_html=True
    )

    doc_data = api_get("/documents/list")
    doc_filter = None

    if doc_data and doc_data["total_documents"] > 0:
        filter_options = ["All documents"] + doc_data["documents"]
        selected = st.selectbox(
            "Search within", filter_options
        )
        if selected != "All documents":
            doc_filter = selected
    else:
        st.warning("No documents uploaded yet. "
                   "Go to Upload & Ingest first.")
        return

    question = st.text_input(
        "Your question",
        placeholder="What was the total revenue in fiscal 2023?",
        key="question_input"
    )

    if st.button("🔍 Ask", type="primary") and question:
        with st.spinner("Searching and generating answer..."):
            result = api_post("/analysis/ask", {
                "question": question,
                "document_filter": doc_filter,
                "n_results": 5
            })

        if result:
            if result.get("had_sufficient_context"):
                st.success("**Answer**")
                st.write(result["answer"])
            else:
                st.warning("⚠️ Insufficient context")
                st.write(result["answer"])

            with st.expander("📚 Sources used"):
                for i, source in enumerate(
                    result.get("sources", []), 1
                ):
                    st.markdown(
                        f"**[Source {i}]** {source['document']} "
                        f"· Page {source['page']} "
                        f"· Relevance: {source['relevance_score']}"
                    )
                    st.caption(source.get("preview", "")[:200])
                    st.divider()

    st.divider()
    st.markdown("**Recent Questions**")
    history = api_get("/analysis/questions")
    if history and history["questions"]:
        for q in history["questions"][:5]:
            with st.expander(f"🕐 {q['question'][:80]}"):
                st.write(q["answer"])
                st.caption(
                    f"Asked: {q['created_at'][:19].replace('T', ' ')}"
                )


def render_analysis_page():
    """Page 3: Full four-agent deep analysis."""
    st.markdown(
        '<div class="main-header">🔬 Deep Analysis</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="sub-header">Run the full four-agent pipeline: '
        'Extractor → Analyst → Validator → Synthesizer. '
        'Takes 60-90 seconds.</div>',
        unsafe_allow_html=True
    )

    doc_data = api_get("/documents/list")
    if not doc_data or doc_data["total_documents"] == 0:
        st.warning("No documents uploaded yet.")
        return

    selected_doc = st.selectbox(
        "Select document to analyze",
        doc_data["documents"]
    )

    col1, col2 = st.columns([1, 3])
    run_button = col1.button(
        "🚀 Run Analysis", type="primary"
    )
    col2.caption(
        "This triggers 4 AI agents making 12-16 tool calls. "
        "Watch the terminal for live progress."
    )

    if run_button:
        progress_placeholder = st.empty()
        status_placeholder = st.empty()

        agents = [
            ("🔍", "Extractor", "Pulling structured facts..."),
            ("📊", "Analyst", "Interpreting the data..."),
            ("✅", "Validator", "Cross-checking claims..."),
            ("📝", "Synthesizer", "Writing final report...")
        ]

        with progress_placeholder.container():
            st.markdown("**Agent pipeline running...**")
            for emoji, name, desc in agents:
                st.markdown(
                    f'<div class="agent-step">'
                    f'{emoji} <strong>{name}</strong> — {desc}'
                    f'</div>',
                    unsafe_allow_html=True
                )

        with st.spinner(
            "Running 4 agents... check terminal for live logs"
        ):
            result = api_post("/analysis/analyze", {
                "document_name": selected_doc
            })

        progress_placeholder.empty()

        if result:
            st.session_state["last_report"] = result
            st.session_state["last_doc"] = selected_doc
            st.rerun()

    if "last_report" in st.session_state:
        render_report(
            st.session_state["last_report"],
            st.session_state.get("last_doc", "")
        )


def render_report(report: dict, doc_name: str):
    """Render a complete analysis report."""
    st.divider()
    st.markdown(f"### Intelligence Report — `{doc_name}`")

    assessment = report.get("overall_assessment", "N/A")
    confidence = report.get("report_confidence", "N/A")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Overall Assessment", assessment)
    col2.metric("Report Confidence", confidence)
    stats = report.get("pipeline_stats", {})
    col3.metric("Agents Run", stats.get("agents_run", 4))
    col4.metric(
        "Tool Calls", stats.get("total_tool_calls", 0)
    )

    st.markdown("#### Executive Summary")
    summary = report.get("executive_summary", "")
    if summary:
        st.info(summary)

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("#### Financial Snapshot")
        snapshot = report.get("financial_snapshot", {})
        if snapshot:
            metrics = snapshot.get("key_metrics", [])
            for m in metrics:
                verified = m.get("verified", True)
                icon = "✓" if verified else "?"
                color = "verified" if verified else "unverified"
                st.markdown(
                    f'<span class="{color}">{icon}</span> '
                    f'**{m.get("metric", "")}**: '
                    f'{m.get("value", "")}',
                    unsafe_allow_html=True
                )

    with col_right:
        st.markdown("#### Risk Landscape")
        risks = report.get("risk_landscape", [])
        if risks:
            for risk in risks[:5]:
                likelihood = risk.get("likelihood", "MEDIUM")
                severity = risk.get("severity", "MEDIUM")
                risk_class = f"risk-{severity.lower()}"
                st.markdown(
                    f'<div class="metric-card {risk_class}">'
                    f'<strong>{risk.get("risk", "")[:60]}</strong>'
                    f'<br><small>Likelihood: {likelihood} · '
                    f'Severity: {severity}</small>'
                    f'</div>',
                    unsafe_allow_html=True
                )

    st.markdown("#### Business Analysis")
    analysis = report.get("business_analysis", "")
    if analysis:
        st.write(analysis)

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("#### Validation Notes")
        notes = report.get("validation_notes", "")
        if notes:
            verified_count = stats.get("verified_claims", 0)
            st.success(
                f"✅ {verified_count} claims verified"
            )
            st.write(notes)

    with col_b:
        st.markdown("#### Outlook")
        outlook = report.get("outlook", "")
        if outlook:
            st.write(outlook)

    if st.button("💾 Export Report as JSON"):
        st.download_button(
            label="⬇️ Download JSON",
            data=json.dumps(report, indent=2),
            file_name=f"nexusiq_report_{doc_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )


def render_dashboard_page():
    """Page 4: Usage statistics and history."""
    st.markdown(
        '<div class="main-header">📊 Dashboard</div>',
        unsafe_allow_html=True
    )

    stats = api_get("/analysis/stats")
    if not stats:
        st.error("Could not load stats.")
        return

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Questions", stats["total_questions"])
    col2.metric("Total Analyses", stats["total_analyses"])
    col3.metric("Documents Stored", stats["total_documents"])
    col4.metric(
        "Context Success Rate",
        f"{stats['context_success_rate']}%"
    )

    st.divider()

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("**Recent Analysis Runs**")
        recent = stats.get("recent_analyses", [])
        if recent:
            for run in recent:
                with st.expander(
                    f"📄 {run['document']} — {run['assessment']}"
                ):
                    st.markdown(
                        f"Confidence: **{run['confidence']}**"
                    )
                    st.caption(
                        run['timestamp'][:19].replace('T', ' ')
                    )
        else:
            st.caption(
                "No analyses run yet. "
                "Go to Deep Analysis to run one."
            )

    with col_right:
        st.markdown("**Question History**")
        history = api_get("/analysis/questions")
        if history and history["questions"]:
            for q in history["questions"][:8]:
                context_icon = (
                    "✅" if q["had_sufficient_context"] else "⚠️"
                )
                st.markdown(
                    f"{context_icon} {q['question'][:70]}"
                )
                st.caption(
                    q['created_at'][:19].replace('T', ' ')
                )
        else:
            st.caption("No questions asked yet.")


def main():
    """Main app entry point."""
    page = render_sidebar()

    if page == "Upload & Ingest":
        render_upload_page()
    elif page == "Ask Questions":
        render_ask_page()
    elif page == "Deep Analysis":
        render_analysis_page()
    elif page == "Dashboard":
        render_dashboard_page()


if __name__ == "__main__":
    main()