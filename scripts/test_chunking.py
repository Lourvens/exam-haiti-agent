"""Test script for chunking system with LangGraph."""

import json
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from models.chunk import Chunk


def test_chunking(pdf_path: str, model: str = "gpt-4o-mini"):
    """Test chunking on a PDF file using LangGraph."""
    from langchain_openai import ChatOpenAI

    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    api_base = os.getenv("OPENAI_API_BASE")

    if not api_key:
        print("ERROR: OPENAI_API_KEY not found in environment")
        print("Please create a .env file with your API key:")
        print("  OPENAI_API_KEY=your_key_here")
        return

    # Create LLM client
    llm_kwargs = {"model": model, "api_key": api_key}
    if api_base:
        llm_kwargs["base_url"] = api_base

    llm = ChatOpenAI(**llm_kwargs)
    print(f"Using model: {model}")

    # Use LangGraph chunking engine
    from core.chunking_graph import LangGraphChunkingEngine
    engine = LangGraphChunkingEngine(llm_client=llm, verbose=True)

    print(f"\nChunking: {pdf_path}")
    print("-" * 50)

    chunks = engine.chunk_pdf(pdf_path)

    print(f"\n{'='*50}")
    print(f"Generated {len(chunks)} chunks")
    print("=" * 50)

    # Save to file
    output_file = Path("logs") / f"chunks_{Path(pdf_path).stem}.json"
    output_file.parent.mkdir(exist_ok=True)

    chunks_data = []
    for i, chunk in enumerate(chunks):
        chunks_data.append({
            "index": i + 1,
            "chunk_type": chunk.chunk_type,
            "subject": chunk.subject,
            "year": chunk.year,
            "serie": chunk.serie,
            "section": chunk.section,
            "question_number": chunk.question_number,
            "sub_question": chunk.sub_question,
            "has_formula": chunk.has_formula,
            "topic_hint": chunk.topic_hint,
            "page_num": chunk.page_num,
            "content": chunk.content,
            "content_preview": chunk.content[:200]
        })

    output = {
        "pdf_path": str(pdf_path),
        "model": model,
        "total_chunks": len(chunks),
        "chunks": chunks_data
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Saved to: {output_file}")

    # Display summary
    for i, chunk in enumerate(chunks[:10]):
        print(f"\n[{i+1}] {chunk.chunk_type}")
        print(f"    Subject: {chunk.subject}, Year: {chunk.year}, Serie: {chunk.serie}")
        print(f"    Topic: {chunk.topic_hint}")
        content_preview = chunk.content[:100].replace("\n", " ")
        print(f"    Content: {content_preview}...")

    if len(chunks) > 10:
        print(f"\n... and {len(chunks) - 10} more chunks")

    # Summary by chunk type
    from collections import Counter
    type_counts = Counter(c.chunk_type for c in chunks)
    print("\n" + "=" * 50)
    print("Summary by chunk type:")
    for chunk_type, count in type_counts.most_common():
        print(f"  {chunk_type}: {count}")


if __name__ == "__main__":
    # Default to a sample PDF
    pdf = "data/pdfs/Math-NS4-2025-LLA-Distance.pdf"

    if len(sys.argv) > 1:
        pdf = sys.argv[1]

    model = "gpt-4o-mini"
    if len(sys.argv) > 2:
        model = sys.argv[2]

    test_chunking(pdf, model)
