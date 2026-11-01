import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

import plotly.graph_objects as go
import requests
import streamlit as st

DEFAULT_API_URL = os.getenv("BIZSCOPE_API_URL", "http://127.0.0.1:8000")
REQUEST_TIMEOUT = 600
APP_DIR = Path(__file__).resolve().parent
HISTORY_DB = Path(os.getenv("BIZSCOPE_HISTORY_DB", str(APP_DIR / "bizscope_chat_history.sqlite3")))

st.set_page_config(
    page_title="BizScopeAI",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .block-container { max-width: 1200px; padding-top: 1.4rem; padding-bottom: 5rem; }
      .bs-subtitle { color: #8993a4; margin-top: -.55rem; }
      [data-testid="stChatMessage"] { border: 1px solid rgba(128,128,128,.14); }
      [data-testid="stSidebar"] { border-right: 1px solid rgba(128,128,128,.15); }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------
# Local conversation index:
# - Investigation messages/state remain persisted by the FastAPI backend.
# - This SQLite file stores the sidebar index, dataset metadata, and charts
#   returned per assistant turn (the current backend API doesn't persist charts
#   as message attachments).
# ---------------------------------------------------------------------
def db_connect():
    conn = sqlite3.connect(HISTORY_DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_history_db():
    with db_connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                investigation_id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                dataset_id INTEGER,
                dataset_filename TEXT,
                dataset_rows INTEGER,
                dataset_columns INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS turn_visualizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                investigation_id INTEGER NOT NULL,
                assistant_message_index INTEGER NOT NULL,
                visualizations_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(investigation_id, assistant_message_index)
            )
            """
        )


def upsert_conversation(investigation_id, title, dataset_info=None):
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    info = dataset_info or {}
    with db_connect() as conn:
        existing = conn.execute(
            "SELECT * FROM conversations WHERE investigation_id = ?",
            (investigation_id,),
        ).fetchone()
        conn.execute(
            """
            INSERT INTO conversations (
                investigation_id, title, dataset_id, dataset_filename,
                dataset_rows, dataset_columns, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(investigation_id) DO UPDATE SET
                title = CASE WHEN conversations.title = '' THEN excluded.title
                             ELSE conversations.title END,
                dataset_id = COALESCE(excluded.dataset_id, conversations.dataset_id),
                dataset_filename = COALESCE(excluded.dataset_filename, conversations.dataset_filename),
                dataset_rows = COALESCE(excluded.dataset_rows, conversations.dataset_rows),
                dataset_columns = COALESCE(excluded.dataset_columns, conversations.dataset_columns),
                updated_at = excluded.updated_at
            """,
            (
                investigation_id,
                title[:90] or "New conversation",
                info.get("dataset_id"),
                info.get("filename"),
                info.get("rows"),
                info.get("columns"),
                existing["created_at"] if existing else now,
                now,
            ),
        )


def update_conversation_title(investigation_id, title):
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    with db_connect() as conn:
        conn.execute(
            "UPDATE conversations SET title = ?, updated_at = ? WHERE investigation_id = ?",
            (title[:90] or "Business investigation", now, investigation_id),
        )


def save_turn_visualizations(investigation_id, assistant_message_index, visualizations):
    if not visualizations:
        return
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    with db_connect() as conn:
        conn.execute(
            """
            INSERT INTO turn_visualizations (
                investigation_id, assistant_message_index, visualizations_json, created_at
            ) VALUES (?, ?, ?, ?)
            ON CONFLICT(investigation_id, assistant_message_index)
            DO UPDATE SET visualizations_json = excluded.visualizations_json
            """,
            (
                investigation_id,
                assistant_message_index,
                json.dumps(visualizations, default=str),
                now,
            ),
        )


def load_turn_visualizations(investigation_id, assistant_message_index):
    with db_connect() as conn:
        row = conn.execute(
            """
            SELECT visualizations_json FROM turn_visualizations
            WHERE investigation_id = ? AND assistant_message_index = ?
            """,
            (investigation_id, assistant_message_index),
        ).fetchone()
    if not row:
        return []
    try:
        return json.loads(row["visualizations_json"])
    except (TypeError, ValueError):
        return []


def list_conversations():
    with db_connect() as conn:
        return conn.execute(
            """
            SELECT * FROM conversations
            ORDER BY updated_at DESC, investigation_id DESC
            """
        ).fetchall()


init_history_db()

for key, default in {
    "api_url": DEFAULT_API_URL,
    "dataset_id": None,
    "dataset_info": None,
    "investigation_id": None,
    "messages": [],
    "active_title": "New conversation",
    "loaded_investigation_id": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


def endpoint(path: str) -> str:
    return f"{st.session_state.api_url.rstrip('/')}{path}"


def response_error(response: requests.Response) -> str:
    try:
        payload = response.json()
        if isinstance(payload, dict):
            return str(payload.get("detail", payload))
        return str(payload)
    except (ValueError, requests.RequestException):
        return response.text or f"HTTP {response.status_code}"


def render_plotly_charts(visualizations, key_prefix):
    for index, chart_json in enumerate(visualizations or [], start=1):
        if not chart_json:
            continue
        try:
            figure = go.Figure(chart_json)
            figure.update_layout(
                autosize=True,
                margin=dict(l=24, r=24, t=55, b=24),
            )
            st.plotly_chart(
                figure,
                use_container_width=True,
                key=f"{key_prefix}-{index}",
            )
        except Exception:
            st.caption("A saved visualization could not be displayed.")


def fetch_investigation(investigation_id):
    response = requests.get(
        endpoint(f"/investigations/{investigation_id}"),
        timeout=30,
    )
    if not response.ok:
        raise RuntimeError(response_error(response))
    return response.json()


def set_active_conversation(investigation_id):
    details = fetch_investigation(investigation_id)
    st.session_state.investigation_id = details["investigation_id"]
    st.session_state.loaded_investigation_id = details["investigation_id"]
    st.session_state.dataset_id = details.get("dataset_id")
    st.session_state.active_title = details.get("problem") or "Business investigation"
    st.session_state.messages = details.get("messages") or []

    with db_connect() as conn:
        local = conn.execute(
            "SELECT * FROM conversations WHERE investigation_id = ?",
            (investigation_id,),
        ).fetchone()
    if local:
        st.session_state.dataset_info = {
            "dataset_id": local["dataset_id"],
            "filename": local["dataset_filename"],
            "rows": local["dataset_rows"],
            "columns": local["dataset_columns"],
        }
    else:
        st.session_state.dataset_info = None


# ------------------------------- Sidebar -------------------------------
with st.sidebar:
    st.title("BizScopeAI")
    st.caption("Business investigation assistant")

    if st.button("＋ New chat", type="primary", use_container_width=True):
        st.session_state.investigation_id = None
        st.session_state.loaded_investigation_id = None
        st.session_state.messages = []
        st.session_state.active_title = "New conversation"
        # Keep the selected dataset available for the next conversation.
        st.rerun()

    st.subheader("Your conversations")
    conversations = list_conversations()
    if not conversations:
        st.caption("Your conversations will appear here.")
    for conversation in conversations:
        conv_id = conversation["investigation_id"]
        title = conversation["title"] or "Business investigation"
        is_active = conv_id == st.session_state.investigation_id
        label = ("● " if is_active else "") + title
        if st.button(
            label,
            key=f"open-conversation-{conv_id}",
            use_container_width=True,
            help=f"Open conversation {conv_id}",
        ):
            try:
                set_active_conversation(conv_id)
                st.rerun()
            except (requests.RequestException, RuntimeError, KeyError, ValueError) as exc:
                st.error(f"Could not open this conversation: {exc}")

    st.divider()
    with st.expander("Dataset", expanded=not bool(st.session_state.dataset_info)):
        uploaded_file = st.file_uploader(
            "Upload a CSV file",
            type=["csv"],
            key="dataset_uploader",
        )
        if st.button("Upload dataset", use_container_width=True):
            if uploaded_file is None:
                st.warning("Choose a CSV file first.")
            else:
                try:
                    with st.spinner("Uploading dataset…"):
                        response = requests.post(
                            endpoint("/datasets/upload"),
                            files={"file": (uploaded_file.name, uploaded_file.getvalue(), "text/csv")},
                            timeout=REQUEST_TIMEOUT,
                        )
                    if not response.ok:
                        raise RuntimeError(response_error(response))
                    info = response.json()
                    st.session_state.dataset_id = info["dataset_id"]
                    st.session_state.dataset_info = info
                    st.success(f"Uploaded {info.get('filename', uploaded_file.name)}")
                except (requests.RequestException, RuntimeError, ValueError) as exc:
                    st.error(f"Dataset upload failed: {exc}")

        if st.session_state.dataset_info:
            info = st.session_state.dataset_info
            st.caption(
                f"**Active:** {info.get('filename', 'CSV')}  \n"
                f"{info.get('rows', '—')} rows · {info.get('columns', '—')} columns"
            )
        elif st.session_state.dataset_id:
            st.caption(f"Active dataset ID: {st.session_state.dataset_id}")
        else:
            st.caption("Upload a CSV to ask data-backed questions.")

    with st.expander("Connection settings", expanded=False):
        st.text_input("FastAPI URL", key="api_url")
        if st.button("Check backend", use_container_width=True):
            try:
                response = requests.get(endpoint("/openapi.json"), timeout=10)
                if response.ok:
                    st.success("Backend connected.")
                else:
                    st.error(f"Backend returned HTTP {response.status_code}.")
            except requests.RequestException:
                st.error("Could not reach FastAPI.")


# ------------------------------- Main chat -------------------------------
st.title("BizScopeAI")
st.markdown(
    '<p class="bs-subtitle">Investigate business questions through an ongoing conversation.</p>',
    unsafe_allow_html=True,
)

if st.session_state.dataset_info:
    info = st.session_state.dataset_info
    st.caption(f"Dataset: **{info.get('filename', 'CSV')}** · {info.get('rows', '—')} rows")
elif st.session_state.dataset_id:
    st.caption(f"Dataset ID: {st.session_state.dataset_id}")

# Render persisted backend messages. Each assistant response may have a chart
# attached in the local UI index for this message position.
messages = st.session_state.messages or []
assistant_index = 0
for index, message in enumerate(messages):
    role = message.get("role", "assistant")
    content = message.get("content", "")
    if role not in {"user", "assistant"}:
        continue
    with st.chat_message(role):
        st.markdown(content)
        if role == "assistant":
            assistant_index += 1
            charts = load_turn_visualizations(
                st.session_state.investigation_id,
                assistant_index,
            ) if st.session_state.investigation_id else []
            if charts:
                render_plotly_charts(
                    charts,
                    f"history-chart-{st.session_state.investigation_id}-{assistant_index}",
                )

prompt = st.chat_input(
    "Ask a business question or follow up on the findings…",
    disabled=False,
)

if prompt:
    if st.session_state.dataset_id is None and st.session_state.investigation_id is None:
        st.warning("Upload a CSV dataset in the sidebar to begin a data-backed investigation.")
    else:
        # Optimistically show the message while the backend investigates.
        with st.chat_message("user"):
            st.markdown(prompt)

        payload = {
            "message": prompt.strip(),
            "investigation_id": st.session_state.investigation_id,
            "dataset_id": st.session_state.dataset_id,
        }
        try:
            with st.chat_message("assistant"):
                with st.spinner("Investigating…"):
                    response = requests.post(
                        endpoint("/chat"),
                        json=payload,
                        timeout=REQUEST_TIMEOUT,
                    )
                if not response.ok:
                    raise RuntimeError(response_error(response))
                result = response.json()
                answer = result.get("response") or "I couldn't generate a response."
                charts = result.get("visualizations") or []
                st.markdown(answer)
                if charts:
                    render_plotly_charts(
                        charts,
                        f"new-chart-{result.get('investigation_id', 'new')}-{len(messages)}",
                    )
                elif st.session_state.dataset_id is not None:
                    st.caption("No chart was needed or returned for this response.")

            new_investigation_id = result.get("investigation_id")
            if new_investigation_id is not None:
                st.session_state.investigation_id = new_investigation_id
                st.session_state.loaded_investigation_id = new_investigation_id

                # Pull the backend's canonical persisted conversation messages.
                details = fetch_investigation(new_investigation_id)
                st.session_state.messages = details.get("messages") or []
                st.session_state.active_title = details.get("problem") or prompt[:70]
                if not st.session_state.active_title or st.session_state.active_title == "Business investigation":
                    st.session_state.active_title = prompt[:70]

                # Preserve local dataset metadata and create a sidebar entry.
                upsert_conversation(
                    new_investigation_id,
                    prompt[:70],
                    st.session_state.dataset_info,
                )
                # Charts are UI attachments keyed to the ordinal assistant reply.
                assistant_count = sum(
                    1 for item in st.session_state.messages
                    if item.get("role") == "assistant"
                )
                save_turn_visualizations(
                    new_investigation_id,
                    assistant_count,
                    charts,
                )
            st.rerun()
        except requests.Timeout:
            st.error("The investigation timed out. The backend may still be processing; reload the conversation before retrying.")
        except (requests.RequestException, RuntimeError, KeyError, ValueError) as exc:
            st.error(f"Message failed: {exc}")

if not st.session_state.messages:
    st.info("Start a conversation by asking a business question. Your messages will remain in the conversation history.")