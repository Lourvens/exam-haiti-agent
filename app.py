"""Streamlit dashboard for Exam Haiti Agent."""

import streamlit as st
from pathlib import Path
from typing import List, Dict, Any

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


def get_collection_stats(pipeline: IngestionPipeline) -> Dict[str, Any]:
    """Get statistics from the Chroma collection."""
    vectorstore = pipeline._get_vectorstore()
    total_chunks = vectorstore._collection.count()

    # Get all documents to analyze
    if total_chunks > 0:
        all_docs = vectorstore.get(include=["metadatas"])
        metadatas = all_docs.get("metadatas", [])

        # Count by source
        sources = {}
        subjects = {}
        chunk_types = {}
        years = {}

        for meta in metadatas:
            # Source (document)
            source = Path(meta.get("source", "unknown")).stem
            sources[source] = sources.get(source, 0) + 1

            # Subject
            subject = meta.get("subject", "unknown")
            subjects[subject] = subjects.get(subject, 0) + 1

            # Chunk type
            chunk_type = meta.get("chunk_type", "unknown")
            chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1

            # Year
            year = meta.get("year", "unknown")
            years[year] = years.get(year, 0) + 1

        # Get unique documents
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
            "total_chunks": 0,
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

    # Search with a broad query to get all docs, then filter
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

    # Sort by index
    chunks.sort(key=lambda x: x["index"])
    return chunks


# Page config
st.set_page_config(
    page_title="Exam Haiti Agent",
    page_icon="📚",
    layout="wide"
)

# Custom CSS for better styling (works in both light and dark mode)
st.markdown("""
<style>
    /* Metric cards - use transparent background to inherit theme */
    div[data-testid="stMetric"] {
        background-color: transparent;
        padding: 10px;
        border-radius: 8px;
    }

    /* Container styling */
    .chunk-card {
        padding: 15px;
        border-radius: 8px;
        border: 1px solid rgba(128, 128, 128, 0.3);
        margin-bottom: 10px;
    }

    /* Adjust text colors for dark mode */
    @media (prefers-color-scheme: dark) {
        div[data-testid="stMetric"] {
            background-color: rgba(255, 255, 255, 0.05);
        }
    }

    /* Sidebar styling */
    [data-testid="stRadio"] > div {
        gap: 8px;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.title("📚 Exam Haiti Agent Dashboard")
st.markdown("---")

# Initialize pipeline and get stats
pipeline = get_pipeline()
stats = get_collection_stats(pipeline)

# Top metrics row
st.subheader("📊 Collection Statistics")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Total Documents",
        stats["unique_documents"],
        border=True
    )

with col2:
    st.metric(
        "Total Chunks",
        stats["total_chunks"],
        border=True
    )

with col3:
    # Count by subject
    top_subject = max(stats["subjects"].items(), key=lambda x: x[1]) if stats["subjects"] else ("N/A", 0)
    st.metric(
        "Top Subject",
        top_subject[0],
        f"{top_subject[1]} chunks",
        border=True
    )

with col4:
    # Count by year
    top_year = max(stats["years"].items(), key=lambda x: x[1]) if stats["years"] else ("N/A", 0)
    st.metric(
        "Top Year",
        top_year[0],
        f"{top_year[1]} chunks",
        border=True
    )

st.markdown("---")

# Two columns: Sidebar for document selection, Main area for content
col_sidebar, col_main = st.columns([1, 3])

with col_sidebar:
    st.subheader("📁 Documents")

    # Document list
    if stats["sources"]:
        # Sort by chunk count
        sorted_docs = sorted(stats["sources"].items(), key=lambda x: x[1], reverse=True)

        # Create radio options
        doc_options = [f"{name} ({count} chunks)" for name, count in sorted_docs]

        selected_doc = st.radio(
            "Select a document:",
            options=doc_options,
            index=0 if doc_options else None
        )

        # Extract document name
        if selected_doc:
            selected_doc_name = selected_doc.split(" (")[0]
        else:
            selected_doc_name = None
    else:
        st.info("No documents indexed yet.")
        selected_doc_name = None

    # Subject breakdown
    st.markdown("### 📚 By Subject")
    if stats["subjects"]:
        for subject, count in sorted(stats["subjects"].items(), key=lambda x: x[1], reverse=True):
            st.write(f"- **{subject}**: {count} chunks")
    else:
        st.write("No subjects found.")

    # Year breakdown
    st.markdown("### 📅 By Year")
    if stats["years"]:
        for year, count in sorted(stats["years"].items(), key=lambda x: x[1], reverse=True):
            st.write(f"- **{year}**: {count} chunks")
    else:
        st.write("No years found.")

with col_main:
    if selected_doc_name:
        st.subheader(f"📄 {selected_doc_name}")

        # Get chunks for this document
        chunks = get_document_chunks(pipeline, selected_doc_name)

        st.write(f"**{len(chunks)} chunks found**")

        # Filter options
        col_filter1, col_filter2 = st.columns(2)

        with col_filter1:
            chunk_types = list(set(c["chunk_type"] for c in chunks))
            selected_types = st.multiselect(
                "Filter by chunk type:",
                options=chunk_types,
                default=chunk_types
            )

        with col_filter2:
            show_preview = st.checkbox("Show full content", value=False)

        # Filter chunks
        filtered_chunks = [c for c in chunks if c["chunk_type"] in selected_types]

        st.markdown("### 🔍 Chunks")

        # Display chunks
        for chunk in filtered_chunks:
            with st.expander(f"[{chunk['chunk_type']}] Q{chunk['question_number']} - {chunk['topic_hint'] or 'No topic'}", expanded=False):
                # Metadata row
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

                # Content
                st.write("**Content:**")
                if show_preview:
                    st.write(chunk["content"])
                else:
                    st.write(chunk["content"][:500] + "..." if len(chunk["content"]) > 500 else chunk["content"])
    else:
        st.info("👈 Select a document from the sidebar to view its chunks.")

        # Show chunk type distribution
        st.markdown("### 📊 Chunk Type Distribution")
        if stats["chunk_types"]:
            for chunk_type, count in sorted(stats["chunk_types"].items(), key=lambda x: x[1], reverse=True):
                st.write(f"- **{chunk_type}**: {count}")
        else:
            st.write("No chunks found.")
