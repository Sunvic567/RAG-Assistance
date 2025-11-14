from typing import List, Dict
from langchain_text_splitters import RecursiveCharacterTextSplitter

def chunking_publication(paper_content: str, title: str) -> List[Dict[str, str]]:
    """
    Split a paper into overlapping chunks and return a list of dicts:
    { "content": str, "title": str, "chunk_id": str }.
    """
    if not paper_content or not paper_content.strip():
        return []

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ". "]
    )
    chunks = text_splitter.split_text(paper_content)
    chunk_data: List[Dict[str, str]] = []
    for i, chunk in enumerate(chunks):
        chunk_data.append({
            "content": chunk,
            "title": title,
            "chunk_id": f"{title}_{i}",
        })

    return chunk_data