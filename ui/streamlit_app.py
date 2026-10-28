import sys, os, json, uuid, requests
from datetime import datetime, date
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st

API_BASE = "http://localhost:8000"

st.set_page_config(
    page_title="NexusIQ", page_icon="⬡",
    layout="wide", initial_sidebar_state="collapsed"
)

# ── STATE ──────────────────────────────────────────────────────────────────
def _init():
    defaults = {
        "sidebar_open": True,
        "sessions": {},      # {id: {name, meta, history, ts}}
        "active": None,      # active session id
        "uploading": False,  # new-chat upload screen
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init()

# ── STYLES ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,300;0,14..32,400;0,14..32,500;0,14..32,600;1,14..32,300&display=swap');

/* ── RESET ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body,
[data-testid="stAppViewContainer"],
[data-testid="stApp"] {
    background: #0d0d0f !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    color: #e8e8e8 !important;
}

/* ── KILL STREAMLIT CHROME ── */
#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
[data-testid="manage-app-button"],
.stDeployButton { display: none !important; }

/* ── MAIN PADDING ── */
.block-container {
    padding: 0 !important;
    max-width: 100% !important;
}

[data-testid="stMain"] { padding: 0 !important; }
[data-testid="stVerticalBlock"] { gap: 0 !important; }

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width: 3px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 3px; }

/* ── SIDEBAR COLUMN ── */
.sidebar-panel {
    background: #111114;
    height: 100vh;
    position: sticky;
    top: 0;
    border-right: 0.5px solid rgba(255,255,255,0.07);
    padding: 0;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

.sidebar-top {
    padding: 18px 16px 12px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 0.5px solid rgba(255,255,255,0.05);
}

.wordmark {
    font-size: 15px;
    font-weight: 600;
    color: #e8e8e8;
    letter-spacing: -0.03em;
}

.hamburger-btn {
    width: 30px; height: 30px;
    display: flex; align-items: center; justify-content: center;
    border-radius: 7px;
    cursor: pointer;
    color: rgba(255,255,255,0.4);
    font-size: 14px;
    transition: background 0.12s, color 0.12s;
    border: none; background: transparent;
    flex-shrink: 0;
}
.hamburger-btn:hover { background: rgba(255,255,255,0.06); color: rgba(255,255,255,0.8); }

.new-chat-btn {
    margin: 10px 12px 6px;
    padding: 9px 14px;
    background: rgba(255,255,255,0.05);
    border: 0.5px solid rgba(255,255,255,0.1);
    border-radius: 10px;
    font-size: 13px;
    font-weight: 500;
    color: rgba(255,255,255,0.75);
    cursor: pointer;
    display: flex; align-items: center; gap: 8px;
    transition: background 0.12s, border-color 0.12s;
    width: calc(100% - 24px);
}
.new-chat-btn:hover {
    background: rgba(255,255,255,0.09);
    border-color: rgba(255,255,255,0.18);
    color: #e8e8e8;
}

.session-group-label {
    padding: 14px 16px 5px;
    font-size: 11px;
    font-weight: 500;
    color: rgba(255,255,255,0.2);
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

.session-item {
    margin: 1px 8px;
    padding: 8px 10px;
    border-radius: 8px;
    font-size: 13px;
    color: rgba(255,255,255,0.55);
    cursor: pointer;
    display: flex; align-items: center; gap: 9px;
    transition: background 0.1s, color 0.1s;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    line-height: 1.35;
}
.session-item:hover { background: rgba(255,255,255,0.06); color: rgba(255,255,255,0.85); }
.session-item.active { background: rgba(255,255,255,0.08); color: #e8e8e8; }
.session-icon { opacity: 0.45; flex-shrink: 0; font-size: 12px; }
.session-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.sidebar-sessions {
    flex: 1;
    overflow-y: auto;
    padding-bottom: 16px;
}

/* ── MAIN PANEL ── */
.main-panel {
    height: 100vh;
    display: flex;
    flex-direction: column;
    background: #0d0d0f;
    position: relative;
}

/* ── TOP BAR ── */
.top-bar {
    padding: 14px 20px;
    display: flex;
    align-items: center;
    gap: 12px;
    border-bottom: 0.5px solid rgba(255,255,255,0.06);
    background: rgba(13,13,15,0.95);
    backdrop-filter: blur(12px);
    position: sticky; top: 0; z-index: 10;
    min-height: 52px;
}

.top-bar-doc {
    font-size: 13px;
    font-weight: 500;
    color: rgba(255,255,255,0.5);
    letter-spacing: -0.01em;
}

.top-bar-badge {
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 6px;
    background: rgba(109,110,254,0.12);
    color: rgba(109,110,254,0.9);
    border: 0.5px solid rgba(109,110,254,0.2);
    font-weight: 500;
    letter-spacing: 0.02em;
}

/* ── BUTTONS (override Streamlit) ── */
.stButton > button {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    color: rgba(255,255,255,0.45) !important;
    font-size: 18px !important;
    line-height: 1 !important;
    width: 32px !important;
    height: 32px !important;
    border-radius: 8px !important;
    transition: background 0.12s, color 0.12s !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}
.stButton > button:hover {
    background: rgba(255,255,255,0.07) !important;
    color: rgba(255,255,255,0.85) !important;
}

/* Primary button override */
.stButton > button[kind="primary"] {
    background: rgba(109,110,254,0.85) !important;
    border: none !important;
    color: #fff !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 0.55rem 1.4rem !important;
    border-radius: 10px !important;
    width: auto !important;
    height: auto !important;
    letter-spacing: -0.01em !important;
}
.stButton > button[kind="primary"]:hover {
    background: rgba(109,110,254,1) !important;
    transform: translateY(-1px) !important;
}

/* ── CHAT MESSAGES ── */
[data-testid="stChatMessage"] {
    background: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
    max-width: 100% !important;
}

[data-testid="stChatMessageContent"] {
    font-size: 15px !important;
    line-height: 1.65 !important;
    color: #e0e0e0 !important;
    font-weight: 400 !important;
}

/* User message: right-leaning minimal */
[data-testid="stChatMessage"][data-testid*="user"] [data-testid="stChatMessageContent"] {
    background: rgba(255,255,255,0.05) !important;
    border: 0.5px solid rgba(255,255,255,0.09) !important;
    border-radius: 16px 16px 4px 16px !important;
    padding: 11px 16px !important;
    display: inline-block !important;
    max-width: 78% !important;
    float: right !important;
    clear: both !important;
    color: rgba(255,255,255,0.85) !important;
}

/* ── CHAT INPUT ── */
[data-testid="stChatInput"] {
    background: rgba(255,255,255,0.05) !important;
    border: 0.5px solid rgba(255,255,255,0.1) !important;
    border-radius: 14px !important;
    backdrop-filter: blur(10px) !important;
    margin: 0 !important;
}

[data-testid="stChatInput"] textarea {
    background: transparent !important;
    color: #e8e8e8 !important;
    font-size: 15px !important;
    font-family: inherit !important;
    caret-color: #6d6efe !important;
    border: none !important;
    padding: 12px 14px !important;
    line-height: 1.5 !important;
}

[data-testid="stChatInput"] textarea::placeholder { color: rgba(255,255,255,0.2) !important; }
[data-testid="stChatInput"] textarea:focus { box-shadow: none !important; outline: none !important; }

[data-testid="stChatInput"] button {
    background: rgba(109,110,254,0.75) !important;
    border-radius: 9px !important;
    color: #fff !important;
    width: 32px !important;
    height: 32px !important;
    font-size: 13px !important;
}

/* ── CHAT BOTTOM AREA ── */
[data-testid="stBottom"] {
    background: linear-gradient(to top,
        rgba(13,13,15,1) 60%,
        rgba(13,13,15,0) 100%) !important;
    padding: 16px 20px 20px !important;
}

/* ── FILE UPLOADER ── */
[data-testid="stFileUploader"] {
    background: rgba(255,255,255,0.02) !important;
    border: 1.5px dashed rgba(255,255,255,0.1) !important;
    border-radius: 18px !important;
    transition: border-color 0.2s, background 0.2s !important;
}
[data-testid="stFileUploader"]:hover {
    border-color: rgba(109,110,254,0.4) !important;
    background: rgba(109,110,254,0.03) !important;
}
[data-testid="stFileUploaderDropzoneInstructions"] {
    color: rgba(255,255,255,0.3) !important;
}
[data-testid="stFileUploaderDropzoneInstructions"] small {
    color: rgba(255,255,255,0.2) !important;
}

/* ── EXPANDER ── */
[data-testid="stExpander"] {
    background: rgba(255,255,255,0.02) !important;
    border: 0.5px solid rgba(255,255,255,0.07) !important;
    border-radius: 10px !important;
    overflow: hidden !important;
}
[data-testid="stExpander"] summary {
    color: rgba(255,255,255,0.35) !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    padding: 8px 12px !important;
}
[data-testid="stExpander"] summary:hover { color: rgba(255,255,255,0.6) !important; }

/* ── GENERAL TEXT ── */
p, li, td { color: rgba(255,255,255,0.72) !important; font-size: 14px !important; }
h1, h2, h3, h4, h5 { color: #f0f0f0 !important; letter-spacing: -0.04em !important; }
strong { color: rgba(255,255,255,0.88) !important; }
small, .stCaption p { color: rgba(255,255,255,0.25) !important; font-size: 12px !important; }

/* ── SPINNER ── */
[data-testid="stSpinner"] > div > div {
    border-top-color: #6d6efe !important;
}

/* ── COLUMNS GAP FIX ── */
[data-testid="stHorizontalBlock"] { gap: 0 !important; align-items: stretch !important; }

/* ── DIVIDER ── */
hr { border-color: rgba(255,255,255,0.06) !important; margin: 0.8rem 0 !important; }
</style>
""", unsafe_allow_html=True)


# ── API ────────────────────────────────────────────────────────────────────
def api_get(path, timeout=10):
    try:
        r = requests.get(f"{API_BASE}{path}", timeout=timeout)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None

def api_post(path, data=None, files=None, timeout=120):
    try:
        if files:
            r = requests.post(f"{API_BASE}{path}", files=files, timeout=30)
        else:
            r = requests.post(f"{API_BASE}{path}", json=data, timeout=timeout)
        if r.status_code == 200:
            return r.json()
        detail = r.json().get("detail", "Unknown error")
        st.error(f"API {r.status_code}: {detail}")
        return None
    except requests.exceptions.Timeout:
        st.error("Request timed out.")
        return None
    except Exception as e:
        st.error(f"Connection error — is the API server running? ({e})")
        return None

def stream_question(question, doc_filter=None, n_results=5):
    """Generator that yields tokens from the streaming endpoint."""
    try:
        with requests.post(
            f"{API_BASE}/analysis/ask/stream",
            json={"question": question,
                  "document_filter": doc_filter,
                  "n_results": n_results},
            stream=True, timeout=60
        ) as r:
            for chunk in r.iter_content(chunk_size=None):
                if chunk:
                    yield chunk.decode("utf-8")
    except Exception as e:
        yield f"\n\n_Error: {e}_"

def get_sources(question, doc_filter=None):
    result = api_post("/analysis/ask", {
        "question": question,
        "document_filter": doc_filter,
        "n_results": 5
    })
    return result.get("sources", []) if result else []


# ── SESSION HELPERS ────────────────────────────────────────────────────────
def new_session(doc_name, meta):
    sid = str(uuid.uuid4())
    st.session_state.sessions[sid] = {
        "name": doc_name,
        "meta": meta,
        "history": [],
        "ts": datetime.now().isoformat()
    }
    return sid

def get_session():
    sid = st.session_state.active
    if sid and sid in st.session_state.sessions:
        return st.session_state.sessions[sid]
    return None

def session_display_name(name):
    stem = os.path.splitext(name)[0].replace("_", " ").replace("-", " ")
    return stem[:32] + ("…" if len(stem) > 32 else "")

def group_sessions_by_date():
    today = date.today()
    groups = {"Today": [], "Yesterday": [], "Earlier": []}
    for sid, s in st.session_state.sessions.items():
        d = datetime.fromisoformat(s["ts"]).date()
        delta = (today - d).days
        if delta == 0:
            groups["Today"].append((sid, s))
        elif delta == 1:
            groups["Yesterday"].append((sid, s))
        else:
            groups["Earlier"].append((sid, s))
    return {k: v for k, v in groups.items() if v}


# ── SIDEBAR ────────────────────────────────────────────────────────────────
def render_sidebar_content():
    """Renders the content inside the sidebar column."""
    st.markdown("""
<div class="sidebar-panel">
    <div class="sidebar-top">
        <span class="wordmark">⬡ NexusIQ</span>
    </div>
""", unsafe_allow_html=True)

    # Hamburger close button
    if st.button("✕", key="close_sidebar"):
        st.session_state.sidebar_open = False
        st.rerun()

    # New chat
    st.markdown("""
<button class="new-chat-btn" onclick="return false">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
         stroke="currentColor" stroke-width="2" stroke-linecap="round">
        <line x1="12" y1="5" x2="12" y2="19"/>
        <line x1="5" y1="12" x2="19" y2="12"/>
    </svg>
    New Chat
</button>
""", unsafe_allow_html=True)

    if st.button("＋  New Chat", key="new_chat_btn"):
        st.session_state.uploading = True
        st.session_state.active = None
        st.rerun()

    # Session list
    groups = group_sessions_by_date()
    if groups:
        st.markdown('<div class="sidebar-sessions">', unsafe_allow_html=True)
        for group_name, sessions in groups.items():
            st.markdown(
                f'<div class="session-group-label">{group_name}</div>',
                unsafe_allow_html=True
            )
            for sid, s in reversed(sessions):
                is_active = st.session_state.active == sid
                active_class = "active" if is_active else ""
                display = session_display_name(s["name"])
                st.markdown(
                    f'<div class="session-item {active_class}">'
                    f'<span class="session-icon">📄</span>'
                    f'<span class="session-name">{display}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                if st.button(display, key=f"sess_{sid}"):
                    st.session_state.active = sid
                    st.session_state.uploading = False
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown(
            '<div style="padding:20px 16px;font-size:12px;'
            'color:rgba(255,255,255,0.2)">No chats yet.</div>',
            unsafe_allow_html=True
        )

    st.markdown('</div>', unsafe_allow_html=True)


# ── LANDING ────────────────────────────────────────────────────────────────
def render_landing():
    st.markdown("""
<div style="display:flex;flex-direction:column;align-items:center;
            justify-content:center;height:calc(100vh - 52px);
            text-align:center;padding:0 2rem">
    <div style="font-size:3rem;margin-bottom:1.2rem;opacity:0.15">⬡</div>
    <h1 style="font-size:2.2rem;font-weight:700;letter-spacing:-0.05em;
               color:#e8e8e8;margin-bottom:0.6rem;line-height:1.1">
        What do you want<br>to know?
    </h1>
    <p style="font-size:0.95rem;color:rgba(255,255,255,0.3);
              max-width:360px;line-height:1.6;margin-bottom:2.5rem">
        Upload a financial or legal document and ask anything.
        Four AI agents extract, analyse, validate, and report.
    </p>
</div>
""", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 0.6, 1])
    with col2:
        if st.button("Start a new chat", type="primary",
                     key="landing_new"):
            st.session_state.uploading = True
            st.rerun()


# ── UPLOAD SCREEN ──────────────────────────────────────────────────────────
def render_upload_screen():
    st.markdown("""
<div style="display:flex;flex-direction:column;align-items:center;
            padding:4rem 2rem 2rem;text-align:center">
    <p style="font-size:11px;font-weight:600;letter-spacing:0.1em;
              text-transform:uppercase;color:rgba(255,255,255,0.2);
              margin-bottom:0.8rem">New Chat</p>
    <h2 style="font-size:1.7rem;font-weight:600;letter-spacing:-0.04em;
               color:#e8e8e8;margin-bottom:0.5rem">Drop your document</h2>
    <p style="font-size:0.88rem;color:rgba(255,255,255,0.3);
              margin-bottom:2.5rem;max-width:320px">
        PDF, DOCX, TXT, or MD · up to 50 MB
    </p>
</div>
""", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        f = st.file_uploader(
            " ",
            type=["pdf", "docx", "txt", "md"],
            key="upload_input",
            label_visibility="collapsed"
        )

        if f:
            with st.spinner("Parsing · Chunking · Embedding…"):
                result = api_post("/documents/upload", files={
                    "file": (
                        f.name, f.getvalue(),
                        f.type or "application/octet-stream"
                    )
                })
            if result:
                sid = new_session(f.name, result)
                st.session_state.active = sid
                st.session_state.uploading = False
                st.rerun()

    st.markdown("""
<div style="text-align:center;margin-top:1.5rem">
    <p style="font-size:12px;color:rgba(255,255,255,0.15)">
        Or pick a document already in your knowledge base
    </p>
</div>
""", unsafe_allow_html=True)

    docs = api_get("/documents/list")
    if docs and docs["total_documents"] > 0:
        col_a, col_b, col_c = st.columns([1, 2, 1])
        with col_b:
            for doc in docs["documents"]:
                display = session_display_name(doc)
                if st.button(f"📄  {display}", key=f"pick_{doc}"):
                    meta = {
                        "document_name": doc,
                        "document_category": "",
                        "chunks_created": 0,
                        "detected_title": doc,
                        "detected_date": ""
                    }
                    sid = new_session(doc, meta)
                    st.session_state.active = sid
                    st.session_state.uploading = False
                    st.rerun()


# ── CHAT VIEW ──────────────────────────────────────────────────────────────
def render_chat():
    sess = get_session()
    if not sess:
        render_landing()
        return

    doc_name = sess["name"]
    meta = sess["meta"]
    history = sess["history"]

    # ── Top bar ──────────────────────────────────────────────────────────
    cat = meta.get("document_category", "")
    st.markdown(f"""
<div class="top-bar">
    <span class="top-bar-doc">{session_display_name(doc_name)}</span>
    {'<span class="top-bar-badge">' + cat + '</span>' if cat else ''}
</div>
""", unsafe_allow_html=True)

    # ── Messages ─────────────────────────────────────────────────────────
    msg_container = st.container()

    with msg_container:
        if not history:
            detected_title = meta.get("detected_title") or doc_name
            chunks = meta.get("chunks_created", 0)
            st.markdown(f"""
<div style="text-align:center;padding:3rem 2rem 1.5rem">
    <div style="font-size:2rem;margin-bottom:1rem;opacity:0.12">⬡</div>
    <p style="font-size:0.88rem;color:rgba(255,255,255,0.35);
              max-width:400px;margin:0 auto;line-height:1.6">
        <strong style="color:rgba(255,255,255,0.6)">
            {detected_title[:50]}
        </strong><br>
        {chunks} chunks indexed · Ask me anything about this document.
    </p>
</div>

<div style="display:grid;grid-template-columns:1fr 1fr;
            gap:8px;padding:0 4rem 2rem;max-width:700px;margin:0 auto">
    <div style="background:rgba(255,255,255,0.03);border:0.5px solid
                rgba(255,255,255,0.08);border-radius:12px;padding:14px 16px;
                cursor:pointer;font-size:13px;color:rgba(255,255,255,0.5);
                line-height:1.4">
        📊 What are the key financial highlights?
    </div>
    <div style="background:rgba(255,255,255,0.03);border:0.5px solid
                rgba(255,255,255,0.08);border-radius:12px;padding:14px 16px;
                cursor:pointer;font-size:13px;color:rgba(255,255,255,0.5);
                line-height:1.4">
        ⚠️ What are the main risk factors?
    </div>
    <div style="background:rgba(255,255,255,0.03);border:0.5px solid
                rgba(255,255,255,0.08);border-radius:12px;padding:14px 16px;
                cursor:pointer;font-size:13px;color:rgba(255,255,255,0.5);
                line-height:1.4">
        📋 Summarise the executive overview
    </div>
    <div style="background:rgba(255,255,255,0.03);border:0.5px solid
                rgba(255,255,255,0.08);border-radius:12px;padding:14px 16px;
                cursor:pointer;font-size:13px;color:rgba(255,255,255,0.5);
                line-height:1.4">
        🔭 What is the company's outlook?
    </div>
</div>
""", unsafe_allow_html=True)

        # Render existing messages
        for msg in history:
            if msg["role"] == "user":
                with st.chat_message("user", avatar="🧑"):
                    st.markdown(msg["content"])
            else:
                with st.chat_message("assistant", avatar="✦"):
                    st.markdown(msg["content"])
                    if msg.get("sources"):
                        with st.expander(
                            f"  {len(msg['sources'])} sources",
                            expanded=False
                        ):
                            for i, src in enumerate(msg["sources"], 1):
                                score = src.get("relevance_score", 0)
                                color = (
                                    "#4ade80" if score > 0.6 else
                                    "#fbbf24" if score > 0.35 else
                                    "#888"
                                )
                                st.markdown(
                                    f"**[{i}]** `{src['document']}` "
                                    f"· Page {src.get('page','N/A')} · "
                                    f"<span style='color:{color}'>"
                                    f"{score:.3f}</span>",
                                    unsafe_allow_html=True
                                )
                                if src.get("preview"):
                                    st.caption(src["preview"][:160])

    # ── Input + streaming ────────────────────────────────────────────────
    question = st.chat_input(
        "Ask anything about this document…",
        key=f"chat_{st.session_state.active}"
    )

    if question:
        # Append user message
        sess["history"].append({"role": "user", "content": question})

        with msg_container:
            with st.chat_message("user", avatar="○"):
                st.markdown(question)

            with st.chat_message("assistant", avatar="✦"):
                # Stream the response token by token
                answer = st.write_stream(
                    stream_question(question, doc_name)
                )

        # Fetch sources (non-blocking, separate call)
        sources = get_sources(question, doc_name)

        sess["history"].append({
            "role": "assistant",
            "content": answer,
            "sources": sources
        })
        st.rerun()


# ── MAIN ───────────────────────────────────────────────────────────────────
def main():
    # ── Hamburger (collapsed state, no sidebar column) ──
    if not st.session_state.sidebar_open:
        col_ham, col_spacer = st.columns([0.04, 0.96])
        with col_ham:
            if st.button("☰", key="open_sidebar"):
                st.session_state.sidebar_open = True
                st.rerun()

    # ── Layout ──────────────────────────────────────────────────────────
    if st.session_state.sidebar_open:
        col_sb, col_main = st.columns([0.22, 0.78])
        with col_sb:
            render_sidebar_content()
        with col_main:
            _render_main_area()
    else:
        _render_main_area()


def _render_main_area():
    if st.session_state.uploading:
        render_upload_screen()
    elif st.session_state.active:
        render_chat()
    else:
        render_landing()


if __name__ == "__main__":
    main()