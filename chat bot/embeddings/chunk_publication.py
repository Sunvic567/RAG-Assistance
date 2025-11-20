from typing import List, Dict
from langchain_text_splitters import RecursiveCharacterTextSplitter

def chunking_publication(publications, title) -> List[Dict[str, str]]:
    
    if not publications.strip():
        return []

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ". "]
    )
    chunks = text_splitter.split_text(publications)
    chunk_data: List[Dict[str, str]] = []
    for i, chunk in enumerate(chunks):
        id = f"chunk_id{i}"
        chunk_data.append({
            "content": chunk,
            "chunk_id": id,
            "title": title
        })

    return chunk_data