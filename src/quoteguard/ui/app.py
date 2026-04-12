"""Streamlit UI entrypoint with a dependency-free debug snapshot helper."""

from __future__ import annotations

from quoteguard.orchestration.state import ConversationState


def build_debug_snapshot(state: ConversationState, retrieval_results: list[dict] | None = None) -> dict:
    return {
        "phase": state.phase,
        "slots": dict(state.slots),
        "turn_count": state.turn_count,
        "retrieval_results": retrieval_results or [],
    }


def run_streamlit_app() -> None:
    try:
        import streamlit as st
    except ImportError as exc:
        raise RuntimeError("Streamlit is not installed. Install dependencies to run the demo UI.") from exc

    st.set_page_config(page_title="QuoteGuard", layout="wide")
    st.title("QuoteGuard")
    left, right = st.columns([2, 1])
    with left:
        st.write("Chat UI placeholder. Wire this to the orchestrator once dependencies are installed.")
    with right:
        st.write("Debug panel placeholder.")


if __name__ == "__main__":
    run_streamlit_app()
