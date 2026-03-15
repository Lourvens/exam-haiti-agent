"""Streamlit dashboard for Exam Haiti Agent."""

import streamlit as st
import time
from pathlib import Path
from typing import List, Dict, Any
import subprocess

from dotenv import load_dotenv
load_dotenv()

from services.ingestion_pipeline import IngestionPipeline
from langchain_openai import ChatOpenAI
import os


def get_pipeline():
    """Get or initialize the ingestion pipeline."""
    if "pipeline" not in st.session_state:
        llm = ChatOpenAI(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
        st.session_state.pipeline = IngestionPipeline(llm_client=llm)
    return st.session_state.pipeline


def reset_pipeline():
    """Reset the pipeline to force reload."""
    if "pipeline" in st.session_state:
        del st.session_state.pipeline


def get_collection_stats(pipeline: IngestionPipeline) -> Dict[str, Any]:
    """Get statistics from the Chroma collection."""
    vectorstore = pipeline._get_vectorstore()
    total_chunks = vectorstore._collection.count()

    if total_chunks > 0:
        all_docs = vectorstore.get(include=["metadatas"])
        metadatas = all_docs.get("metadatas", [])

        sources = {}
        subjects = {}
        chunk_types = {}
        years = {}

        for meta in metadatas:
            source = Path(meta.get("source", "unknown")).stem
            sources[source] = sources.get(source, 0) + 1

            subject = meta.get("subject", "unknown")
            subjects[subject] = subjects.get(subject, 0) + 1

            chunk_type = meta.get("chunk_type", "unknown")
            chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1

            year = meta.get("year", "unknown")
            years[year] = years.get(year, 0) + 1

        unique_docs = len(sources)

        return {
            "total_chunks": total_chunks,
            "unique_documents": unique_docs,
            "sources": sources,
            "subjects": subjects,
            "chunk_types": chunk_types,
            "years": years,
            "metadatas": metadatas
        }
    else:
        return {
            "total_documents": 0,
            "unique_documents": 0,
            "sources": {},
            "subjects": {},
            "chunk_types": {},
            "years": {},
            "metadatas": []
        }


def get_document_chunks(pipeline: IngestionPipeline, doc_name: str) -> List[Dict]:
    """Get all chunks for a specific document."""
    vectorstore = pipeline._get_vectorstore()
    results = vectorstore.get(include=["metadatas", "documents"])

    chunks = []
    for i, (doc, meta) in enumerate(zip(results.get("documents", []), results.get("metadatas", []))):
        source = Path(meta.get("source", "")).stem
        if source == doc_name:
            chunks.append({
                "index": meta.get("chunk_index", i),
                "content": doc,
                "chunk_type": meta.get("chunk_type", "unknown"),
                "subject": meta.get("subject", ""),
                "year": meta.get("year", ""),
                "serie": meta.get("serie", ""),
                "section": meta.get("section", ""),
                "question_number": meta.get("question_number", ""),
                "topic_hint": meta.get("topic_hint", "")
            })

    chunks.sort(key=lambda x: x["index"])
    return chunks


def delete_document_chunks(pipeline: IngestionPipeline, doc_name: str):
    """Delete all chunks for a specific document."""
    vectorstore = pipeline._get_vectorstore()

    # Find all IDs for this document
    all_docs = vectorstore.get(include=["metadatas"])
    ids_to_delete = []

    for i, meta in enumerate(all_docs.get("metadatas", [])):
        source = Path(meta.get("source", "")).stem
        if source == doc_name:
            ids_to_delete.append(all_docs["ids"][i])

    if ids_to_delete:
        vectorstore.delete(ids=ids_to_delete)
        return len(ids_to_delete)
    return 0


def get_pdf_files() -> List[str]:
    """Get list of PDF files from data/pdfs folder."""
    pdf_dir = Path("data/pdfs")
    if pdf_dir.exists():
        return sorted([str(f) for f in pdf_dir.glob("*.pdf")])
    return []


# Page config
st.set_page_config(
    page_title="Exam Haiti Agent",
    page_icon="📚",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    div[data-testid="stMetric"] {
        background-color: transparent;
        padding: 10px;
        border-radius: 8px;
    }
    @media (prefers-color-scheme: dark) {
        div[data-testid="stMetric"] {
            background-color: rgba(255, 255, 255, 0.05);
        }
    }
    .stButton > button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.title("📚 Exam Haiti Agent Dashboard")

# Main tabs
tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📥 Ingest", "🔍 Search"])

# ============ TAB 1: DASHBOARD ============
with tab1:
    # Initialize pipeline and get stats
    pipeline = get_pipeline()
    stats = get_collection_stats(pipeline)

    # Top metrics row
    st.subheader("Collection Statistics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Documents", stats["unique_documents"], border=True)
    with col2:
        st.metric("Total Chunks", stats["total_chunks"], border=True)
    with col3:
        top_subject = max(stats["subjects"].items(), key=lambda x: x[1]) if stats["subjects"] else ("N/A", 0)
        st.metric("Top Subject", top_subject[0], f"{top_subject[1]} chunks", border=True)
    with col4:
        top_year = max(stats["years"].items(), key=lambda x: x[1]) if stats["years"] else ("N/A", 0)
        st.metric("Top Year", top_year[0], f"{top_year[1]} chunks", border=True)

    st.markdown("---")

    # Two columns: Sidebar for document selection, Main area for content
    col_sidebar, col_main = st.columns([1, 3])

    with col_sidebar:
        st.subheader("📁 Documents")

        # Collection actions
        with st.expander("⚙️ Collection Actions", expanded=False):
            if st.button("🗑️ Clear All Chunks", use_container_width=True):
                with st.spinner("Clearing..."):
                    vectorstore = pipeline._get_vectorstore()
                    # Get all IDs and delete - Chroma requires explicit IDs
                    all_docs = vectorstore.get()
                    all_ids = all_docs.get("ids", [])
                    if all_ids:
                        vectorstore.delete(ids=all_ids)
                        st.success(f"Cleared {len(all_ids)} chunks!")
                    else:
                        st.success("Collection already empty!")
                    reset_pipeline()
                    st.rerun()

        # Document list
        if stats["sources"]:
            sorted_docs = sorted(stats["sources"].items(), key=lambda x: x[1], reverse=True)
            doc_options = [f"{name} ({count} chunks)" for name, count in sorted_docs]
            doc_options.insert(0, "— Select a document —")

            selected_doc = st.radio(
                "Select:",
                options=doc_options,
                index=0 if doc_options else None
            )

            if selected_doc and selected_doc != "— Select a document —":
                selected_doc_name = selected_doc.split(" (")[0]
            else:
                selected_doc_name = None
        else:
            st.info("No documents indexed yet.")
            selected_doc_name = None

        # Document actions
        if selected_doc_name:
            st.markdown("---")
            st.subheader("🔧 Document Actions")

            col_act1, col_act2 = st.columns(2)

            with col_act1:
                if st.button("🔄 Re-process", use_container_width=True, help="Delete and recreate chunks + embeddings"):
                    with st.spinner("Re-processing..."):
                        # Delete existing
                        deleted = delete_document_chunks(pipeline, selected_doc_name)
                        st.info(f"Deleted {deleted} existing chunks")

                        # Re-ingest
                        pdf_path = None
                        for src, _ in stats["sources"].items():
                            if src == selected_doc_name:
                                # Find actual file path
                                for f in get_pdf_files():
                                    if selected_doc_name in f:
                                        pdf_path = f
                                        break

                        if pdf_path:
                            result = pipeline.ingest_pdf(pdf_path)
                            reset_pipeline()
                            st.success(f"Re-processed: {result.get('chunks', 0)} chunks created!")
                            st.rerun()
                        else:
                            st.error("PDF file not found!")

            with col_act2:
                if st.button("🗑️ Delete", use_container_width=True, help="Delete all chunks for this document"):
                    with st.spinner("Deleting..."):
                        deleted = delete_document_chunks(pipeline, selected_doc_name)
                        reset_pipeline()
                        st.success(f"Deleted {deleted} chunks!")
                        st.rerun()

        # Subject breakdown
        st.markdown("---")
        st.markdown("### 📚 By Subject")
        if stats["subjects"]:
            for subject, count in sorted(stats["subjects"].items(), key=lambda x: x[1], reverse=True):
                st.write(f"- **{subject}**: {count}")
        else:
            st.write("No subjects found.")

        st.markdown("### 📅 By Year")
        if stats["years"]:
            for year, count in sorted(stats["years"].items(), key=lambda x: x[1], reverse=True):
                st.write(f"- **{year}**: {count}")
        else:
            st.write("No years found.")

    with col_main:
        if selected_doc_name:
            st.subheader(f"📄 {selected_doc_name}")

            chunks = get_document_chunks(pipeline, selected_doc_name)
            st.write(f"**{len(chunks)} chunks found**")

            # Filter
            col_filter1, col_filter2 = st.columns(2)
            with col_filter1:
                chunk_types = list(set(c["chunk_type"] for c in chunks))
                selected_types = st.multiselect("Filter by chunk type:", options=chunk_types, default=chunk_types)
            with col_filter2:
                show_preview = st.checkbox("Show full content", value=False)

            filtered_chunks = [c for c in chunks if c["chunk_type"] in selected_types]

            st.markdown("### 🔍 Chunks")
            for chunk in filtered_chunks:
                with st.expander(f"[{chunk['chunk_type']}] Q{chunk['question_number']} - {chunk['topic_hint'] or 'No topic'}", expanded=False):
                    meta_cols = st.columns(4)
                    with meta_cols[0]:
                        st.write(f"**Subject:** {chunk['subject']}")
                    with meta_cols[1]:
                        st.write(f"**Year:** {chunk['year']}")
                    with meta_cols[2]:
                        st.write(f"**Serie:** {chunk['serie']}")
                    with meta_cols[3]:
                        st.write(f"**Section:** {chunk['section']}")

                    st.markdown("---")
                    st.write("**Content:**")
                    if show_preview:
                        st.write(chunk["content"])
                    else:
                        st.write(chunk["content"][:500] + "..." if len(chunk["content"]) > 500 else chunk["content"])
        else:
            st.info("👈 Select a document from the sidebar to view its chunks.")

            # Chunk type distribution
            st.markdown("### 📊 Chunk Type Distribution")
            if stats["chunk_types"]:
                for chunk_type, count in sorted(stats["chunk_types"].items(), key=lambda x: x[1], reverse=True):
                    st.write(f"- **{chunk_type}**: {count}")
            else:
                st.write("No chunks found.")

# ============ TAB 2: INGEST ============
with tab2:
    st.subheader("📥 Ingest PDF")

    # Option 1: Select from existing PDFs
    st.markdown("### From data/pdfs folder")
    pdf_files = get_pdf_files()

    if pdf_files:
        pdf_options = [str(Path(f).name) for f in pdf_files]
        selected_pdf = st.selectbox("Select PDF:", options=pdf_options, index=0 if pdf_options else None)

        col_ingest1, col_ingest2 = st.columns([3, 1])
        with col_ingest1:
            if selected_pdf:
                pdf_path = next(f for f in pdf_files if selected_pdf in f)
                st.info(f"📄 {pdf_path}")

        with col_ingest2:
            if st.button("⚡ Ingest Selected", use_container_width=True):
                with st.spinner("Processing..."):
                    result = pipeline.ingest_pdf(pdf_path)
                    reset_pipeline()
                    st.success(f"✓ Ingested: {result.get('chunks', 0)} chunks!")
                    st.rerun()
    else:
        st.warning("No PDFs found in data/pdfs folder")

    st.markdown("---")

    # Option 2: Upload new PDF
    st.markdown("### Upload New PDF")
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

    if uploaded_file:
        # Save uploaded file
        save_dir = Path("data/pdfs")
        save_dir.mkdir(exist_ok=True)
        save_path = save_dir / uploaded_file.name

        with open(save_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        st.success(f"✓ Saved to: {save_path}")

        # Ingest button
        if st.button("⚡ Ingest Uploaded PDF", use_container_width=True):
            with st.spinner("Processing..."):
                result = pipeline.ingest_pdf(str(save_path))
                reset_pipeline()
                st.success(f"✓ Ingested: {result.get('chunks', 0)} chunks!")
                st.rerun()

# ============ TAB 3: SEARCH ============
with tab3:
    st.subheader("🔍 Search Documents")

    search_query = st.text_input("Enter search query:", placeholder="e.g., chemistry, biology, 2023...")

    col_search1, col_search2 = st.columns([3, 1])
    with col_search1:
        n_results = st.slider("Number of results:", min_value=1, max_value=20, value=5)
    with col_search2:
        search_btn = st.button("🔍 Search", use_container_width=True)

    if (search_btn or search_query) and search_query:
        with st.spinner("Searching..."):
            results = pipeline.search(search_query, n_results=n_results)

        st.markdown(f"### Found {len(results)} results")

        for i, result in enumerate(results):
            with st.expander(f"Result {i+1} (distance: {result.get('distance', 0):.3f})", expanded=True):
                meta = result.get("metadata", {})
                content = result.get("content", "")

                # Metadata
                meta_cols = st.columns(4)
                with meta_cols[0]:
                    st.write(f"**Subject:** {meta.get('subject', 'N/A')}")
                with meta_cols[1]:
                    st.write(f"**Year:** {meta.get('year', 'N/A')}")
                with meta_cols[2]:
                    st.write(f"**Type:** {meta.get('chunk_type', 'N/A')}")
                with meta_cols[3]:
                    st.write(f"**Serie:** {meta.get('serie', 'N/A')}")

                st.markdown("---")
                st.write("**Content:**")
                st.write(content[:1000] + "..." if len(content) > 1000 else content)
    elif not search_query:
        st.info("Enter a search query to find relevant chunks")
