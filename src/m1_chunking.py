"""Module 1: Document Loading and Hierarchical Chunking."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATA_DIR, HIERARCHICAL_PARENT_SIZE, HIERARCHICAL_CHILD_SIZE


@dataclass
class Chunk:
    text: str
    metadata: dict
    parent_id: str | int = 0


def load_documents() -> list[dict]:
    """Load all markdown documents from data/ directory."""
    data_path = Path(DATA_DIR)
    docs = []
    for file_path in sorted(data_path.glob("*.md")):
        text = file_path.read_text(encoding="utf-8").strip()
        if text:
            docs.append({
                "text": text,
                "metadata": {
                    "source": file_path.name,
                    "title": file_path.stem.replace("_", " ").title(),
                }
            })
    return docs


def chunk_hierarchical(text: str, metadata: dict | None = None) -> tuple[list[Chunk], list[Chunk]]:
    """Split document into hierarchical parent and child chunks.
    
    Returns:
        tuple (parents, children), where each child has .text, .metadata, .parent_id
    """
    metadata = dict(metadata or {})
    # Split text by sections/headers or double newlines
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [text]

    parents: list[Chunk] = []
    children: list[Chunk] = []

    current_parent_text = []
    current_parent_len = 0
    parent_idx = 0

    parent_groups: list[list[str]] = []

    for para in paragraphs:
        if current_parent_len + len(para) > HIERARCHICAL_PARENT_SIZE and current_parent_text:
            parent_groups.append(current_parent_text)
            current_parent_text = [para]
            current_parent_len = len(para)
        else:
            current_parent_text.append(para)
            current_parent_len += len(para)

    if current_parent_text:
        parent_groups.append(current_parent_text)

    for p_id, p_paras in enumerate(parent_groups):
        p_text = "\n\n".join(p_paras)
        parent_chunk = Chunk(
            text=p_text,
            metadata={**metadata, "chunk_type": "parent", "parent_id": p_id},
            parent_id=p_id,
        )
        parents.append(parent_chunk)

        # Create child chunks from the parent's paragraphs / sentences
        child_buf = []
        child_buf_len = 0
        child_sub_id = 0

        for para in p_paras:
            # If paragraph is longer than child size, split further by sentences
            if len(para) > HIERARCHICAL_CHILD_SIZE:
                sentences = [s.strip() + "." for s in para.replace(".\n", ". ").split(". ") if s.strip()]
                for sentence in sentences:
                    if child_buf_len + len(sentence) > HIERARCHICAL_CHILD_SIZE and child_buf:
                        c_text = " ".join(child_buf)
                        children.append(Chunk(
                            text=c_text,
                            metadata={**metadata, "chunk_type": "child", "child_id": f"{p_id}_{child_sub_id}"},
                            parent_id=p_id,
                        ))
                        child_sub_id += 1
                        child_buf = [sentence]
                        child_buf_len = len(sentence)
                    else:
                        child_buf.append(sentence)
                        child_buf_len += len(sentence)
            else:
                if child_buf_len + len(para) > HIERARCHICAL_CHILD_SIZE and child_buf:
                    c_text = "\n".join(child_buf)
                    children.append(Chunk(
                        text=c_text,
                        metadata={**metadata, "chunk_type": "child", "child_id": f"{p_id}_{child_sub_id}"},
                        parent_id=p_id,
                    ))
                    child_sub_id += 1
                    child_buf = [para]
                    child_buf_len = len(para)
                else:
                    child_buf.append(para)
                    child_buf_len += len(para)

        if child_buf:
            c_text = "\n".join(child_buf)
            children.append(Chunk(
                text=c_text,
                metadata={**metadata, "chunk_type": "child", "child_id": f"{p_id}_{child_sub_id}"},
                parent_id=p_id,
            ))

    return parents, children
