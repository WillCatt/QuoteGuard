"""Streamlit UI entrypoint with a dependency-free debug snapshot helper."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[3]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from quoteguard.config.settings import settings
from quoteguard.observability.benchmarking import load_benchmark_report
from quoteguard.orchestration.state import ConversationState


def build_debug_snapshot(state: ConversationState, retrieval_results: list[dict] | None = None) -> dict:
    return {
        "phase": state.phase,
        "slots": dict(state.slots),
        "turn_count": state.turn_count,
        "retrieval_results": retrieval_results or [],
    }


def _run_label(run: dict) -> str:
    parser_requested = run.get("parser_backend_requested", "unknown")
    embedder = run.get("embedder_backend", "unknown")
    vector_store = run.get("vector_store_backend", "unknown")
    used = ", ".join(run.get("parser_backend_used", []))
    parser_label = parser_requested if not used or used == parser_requested else f"{parser_requested} ({used})"
    return f"{parser_label} | {embedder} | {vector_store}"


def _run_config(run: dict) -> tuple[str, str, str]:
    return (
        run.get("parser_backend_requested", "unknown"),
        run.get("embedder_backend", "unknown"),
        run.get("vector_store_backend", "unknown"),
    )


def _available_values(runs: list[dict], index: int) -> list[str]:
    return sorted({_run_config(run)[index] for run in runs})


def _find_run(runs: list[dict], parser_backend: str, embedder_backend: str, vector_store_backend: str) -> dict | None:
    for run in runs:
        if _run_config(run) == (parser_backend, embedder_backend, vector_store_backend):
            return run
    return None


def _render_run_selector(
    st: object,
    runs: list[dict],
    *,
    key_prefix: str,
    title: str,
    defaults: tuple[str, str, str] | None = None,
    exclude_config: tuple[str, str, str] | None = None,
) -> dict | None:
    st.markdown(f"**{title}**")
    parser_options = _available_values(runs, 0)
    embedder_options = _available_values(runs, 1)
    vector_store_options = _available_values(runs, 2)
    parser_default, embedder_default, vector_default = defaults or (
        parser_options[0],
        embedder_options[0],
        vector_store_options[0],
    )

    parser_backend = st.radio(
        "Parser Type",
        parser_options,
        index=parser_options.index(parser_default) if parser_default in parser_options else 0,
        key=f"{key_prefix}_parser",
        horizontal=True,
    )
    embedder_backend = st.radio(
        "Embedder Backend",
        embedder_options,
        index=embedder_options.index(embedder_default) if embedder_default in embedder_options else 0,
        key=f"{key_prefix}_embedder",
        horizontal=True,
    )
    vector_store_backend = st.radio(
        "Vector Store Backend",
        vector_store_options,
        index=vector_store_options.index(vector_default) if vector_default in vector_store_options else 0,
        key=f"{key_prefix}_vector_store",
        horizontal=True,
    )

    selected_config = (parser_backend, embedder_backend, vector_store_backend)
    if exclude_config and selected_config == exclude_config:
        st.caption("Comparison run is currently identical to the primary selection.")
    run = _find_run(runs, parser_backend, embedder_backend, vector_store_backend)
    if not run:
        st.warning("That configuration is not present in the current benchmark report.")
        return None
    st.caption(_run_label(run))
    return run


def _format_delta(primary: float, secondary: float, *, lower_is_better: bool = True) -> str:
    delta = primary - secondary
    if delta == 0:
        return "0.00"
    sign = "-" if lower_is_better and delta < 0 else "+" if lower_is_better else "+" if delta > 0 else "-"
    return f"{sign}{abs(delta):.2f}"


def _stage_rows(runs: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for run in runs:
        summary = run.get("summary", {})
        label = _run_label(run)
        rows.extend(
            [
                {"backend": label, "stage": "parse", "ms": summary.get("parse_ms_total", 0.0)},
                {"backend": label, "stage": "chunk", "ms": summary.get("chunk_ms_total", 0.0)},
                {"backend": label, "stage": "index", "ms": summary.get("index_ms_total", 0.0)},
                {"backend": label, "stage": "retrieval", "ms": summary.get("avg_retrieval_ms", 0.0)},
            ]
        )
    return rows


def _document_union(runs: list[dict]) -> list[str]:
    names = {
        document["source_pdf"]
        for run in runs
        for document in run.get("documents", [])
    }
    return sorted(names)


def _document_lookup(run: dict) -> dict[str, dict]:
    return {document["source_pdf"]: document for document in run.get("documents", [])}


def _query_lookup(run: dict) -> dict[str, dict]:
    return {query["question"]: query for query in run.get("queries", [])}


def _render_stage_chart(st: object, runs: list[dict]) -> None:
    rows = _stage_rows(runs)
    if not rows:
        return
    st.vega_lite_chart(
        {
            "data": {"values": rows},
            "mark": {"type": "bar", "cornerRadiusTopLeft": 4, "cornerRadiusTopRight": 4},
            "encoding": {
                "x": {"field": "stage", "type": "nominal", "title": "Pipeline stage"},
                "xOffset": {"field": "backend"},
                "y": {"field": "ms", "type": "quantitative", "title": "Time (ms)"},
                "color": {"field": "backend", "type": "nominal", "title": "Backend"},
                "tooltip": [
                    {"field": "backend", "type": "nominal"},
                    {"field": "stage", "type": "nominal"},
                    {"field": "ms", "type": "quantitative", "format": ".2f"},
                ],
            },
        },
        use_container_width=True,
    )


def _render_latency_chart(st: object, runs: list[dict]) -> None:
    rows = [
        {
            "backend": _run_label(run),
            "question": query["question"],
            "latency_ms": query["latency_ms"],
        }
        for run in runs
        for query in run.get("queries", [])
    ]
    if not rows:
        return
    st.vega_lite_chart(
        {
            "data": {"values": rows},
            "mark": {"type": "circle", "size": 120},
            "encoding": {
                "x": {"field": "question", "type": "nominal", "title": "Question"},
                "y": {"field": "latency_ms", "type": "quantitative", "title": "Latency (ms)"},
                "color": {"field": "backend", "type": "nominal", "title": "Backend"},
                "tooltip": [
                    {"field": "backend", "type": "nominal"},
                    {"field": "question", "type": "nominal"},
                    {"field": "latency_ms", "type": "quantitative", "format": ".2f"},
                ],
            },
        },
        use_container_width=True,
    )


def _render_document_chart(st: object, runs: list[dict], metric: str, title: str) -> None:
    rows = [
        {
            "backend": _run_label(run),
            "document": document["source_pdf"],
            metric: document.get(metric, 0),
        }
        for run in runs
        for document in run.get("documents", [])
        if document.get("status") == "ok"
    ]
    if not rows:
        return
    st.caption(title)
    st.vega_lite_chart(
        {
            "data": {"values": rows},
            "mark": {"type": "bar", "cornerRadiusTopLeft": 4, "cornerRadiusTopRight": 4},
            "encoding": {
                "x": {"field": "document", "type": "nominal", "title": "Document"},
                "xOffset": {"field": "backend"},
                "y": {"field": metric, "type": "quantitative", "title": metric.replace("_", " ").title()},
                "color": {"field": "backend", "type": "nominal", "title": "Backend"},
                "tooltip": [
                    {"field": "backend", "type": "nominal"},
                    {"field": "document", "type": "nominal"},
                    {"field": metric, "type": "quantitative"},
                ],
            },
        },
        use_container_width=True,
    )


def _render_query_results(st: object, run: dict, question: str) -> None:
    query = _query_lookup(run).get(question)
    if not query:
        st.info("No query results recorded for this question.")
        return
    st.metric("Latency (ms)", f"{query['latency_ms']:.2f}")
    st.write(f"Top hit: `{query.get('top_hit_source_pdf') or 'n/a'}`")
    for result in query.get("results", []):
        st.markdown(
            "\n".join(
                [
                    f"**#{result['rank']} {result['source_pdf']} p.{result['page_number']}**",
                    f"Score: `{result['score']}`",
                    f"Section: `{' > '.join(result['section_path'])}`",
                    result["preview"],
                ]
            )
        )


def _render_document_panel(st: object, run: dict, document_name: str) -> None:
    document = _document_lookup(run).get(document_name)
    if not document:
        st.info("This backend did not produce output for the selected document.")
        return
    if document.get("status") != "ok":
        st.error(document.get("error", "Document parse failed."))
        return
    st.metric("Parse time (ms)", f"{document['parse_ms']:.2f}")
    st.metric("Sections", str(document["sections"]))
    st.metric("Chunks", str(document["chunks"]))
    st.metric("Avg chunk tokens", f"{document['avg_chunk_tokens']:.2f}")
    st.table(document.get("sample_sections", []))


def _render_retrieval_lab(st: object) -> None:
    report = load_benchmark_report()
    st.subheader("Retrieval Lab")
    st.caption(
        "Explore precomputed parser, embedder, and vector-store combinations without rerunning the corpus pipeline on every click."
    )
    if not report:
        st.info(
            "No benchmark report found yet. Run `python3 scripts/build_benchmark_report.py` "
            "from the repo root, then refresh this page."
        )
        return

    runs = report.get("runs", [])
    if not runs:
        st.warning("Benchmark report is present but contains no runs.")
        return

    default_primary = _run_config(runs[0])
    selector_columns = st.columns(2)
    with selector_columns[0]:
        primary = _render_run_selector(
            st,
            runs,
            key_prefix="primary",
            title="Primary Configuration",
            defaults=default_primary,
        )
    compare_enabled = len(runs) > 1 and selector_columns[1].checkbox("Compare a second configuration", value=True)
    comparison = None
    if compare_enabled:
        comparison_defaults = _run_config(runs[1]) if len(runs) > 1 else default_primary
        with selector_columns[1]:
            comparison = _render_run_selector(
                st,
                runs,
                key_prefix="comparison",
                title="Comparison Configuration",
                defaults=comparison_defaults,
                exclude_config=_run_config(primary) if primary else None,
            )

    if not primary:
        return

    selected_runs = [primary]
    if comparison:
        selected_runs.append(comparison)

    st.write(
        {
            "generated_at": report.get("generated_at"),
            "product_type": report.get("product_type"),
            "questions": len(report.get("questions", [])),
            "parser_backends": report.get("parser_backends"),
            "embedder_backends": report.get("embedder_backends"),
            "vector_store_backends": report.get("vector_store_backends"),
            "benchmark_report": str(settings.benchmark_report_path),
        }
    )

    summary = primary.get("summary", {})
    comparison_summary = selected_runs[1].get("summary", {}) if len(selected_runs) > 1 else None

    metric_columns = st.columns(4)
    metric_columns[0].metric(
        "Parse total (ms)",
        f"{summary.get('parse_ms_total', 0.0):.2f}",
        _format_delta(summary.get("parse_ms_total", 0.0), comparison_summary.get("parse_ms_total", 0.0))
        if comparison_summary
        else None,
    )
    metric_columns[1].metric(
        "Sections",
        str(summary.get("sections_total", 0)),
        _format_delta(summary.get("sections_total", 0), comparison_summary.get("sections_total", 0), lower_is_better=False)
        if comparison_summary
        else None,
    )
    metric_columns[2].metric(
        "Chunks",
        str(summary.get("chunks_total", 0)),
        _format_delta(summary.get("chunks_total", 0), comparison_summary.get("chunks_total", 0), lower_is_better=False)
        if comparison_summary
        else None,
    )
    metric_columns[3].metric(
        "Avg retrieval (ms)",
        f"{summary.get('avg_retrieval_ms', 0.0):.2f}",
        _format_delta(
            summary.get("avg_retrieval_ms", 0.0),
            comparison_summary.get("avg_retrieval_ms", 0.0),
        )
        if comparison_summary
        else None,
    )

    st.markdown("#### Stage Timings")
    _render_stage_chart(st, selected_runs)

    st.markdown("#### Document Shape")
    _render_document_chart(st, selected_runs, "sections", "Sections extracted per document")
    _render_document_chart(st, selected_runs, "chunks", "Chunks generated per document")

    st.markdown("#### Query Latency")
    _render_latency_chart(st, selected_runs)

    st.markdown("#### Document Drill-down")
    documents = _document_union(selected_runs)
    if documents:
        selected_document = st.selectbox("Document", documents)
        doc_columns = st.columns(len(selected_runs))
        for column, run in zip(doc_columns, selected_runs, strict=True):
            with column:
                st.markdown(f"**{_run_label(run)}**")
                _render_document_panel(st, run, selected_document)

    st.markdown("#### Retrieval Explorer")
    questions = report.get("questions", [])
    if questions:
        selected_question = st.selectbox("Question", questions)
        query_columns = st.columns(len(selected_runs))
        for column, run in zip(query_columns, selected_runs, strict=True):
            with column:
                st.markdown(f"**{_run_label(run)}**")
                _render_query_results(st, run, selected_question)

    error_runs = [run for run in runs if run.get("status") != "ok"]
    if error_runs:
        with st.expander("Failed runs"):
            for run in error_runs:
                st.error(f"{_run_label(run)}: {run.get('error', 'Unknown error')}")


def run_streamlit_app() -> None:
    try:
        import streamlit as st
    except ImportError as exc:
        raise RuntimeError("Streamlit is not installed. Install dependencies to run the demo UI.") from exc

    st.set_page_config(page_title="QuoteGuard", layout="wide")
    st.title("QuoteGuard")
    lab_tab, chat_tab = st.tabs(["Retrieval Lab", "Chat Demo"])
    with lab_tab:
        _render_retrieval_lab(st)
    with chat_tab:
        left, right = st.columns([2, 1])
        with left:
            st.write("Chat UI placeholder. Wire this to the orchestrator once dependencies are installed.")
        with right:
            st.write("Debug panel placeholder.")


if __name__ == "__main__":
    run_streamlit_app()
