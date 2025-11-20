from langchain_community.document_loaders import TextLoader
import os
from config.settings import RESEARCH_DIR
from dotenv import load_dotenv
from typing import List

load_dotenv()

# Loading knowledge base path (use RESEARCH_DIR or fallback)
document_path = RESEARCH_DIR or os.getenv("RESEARCH_DIR") or "./research_papers"


def load_research_publications(document_path: str) -> List[str]:
    documents = []
    if not document_path or not os.path.isdir(document_path):
        print(f"Document path not found or invalid: {document_path}")
        return []

    for file in os.listdir(document_path):
        if file.endswith('.md') or file.endswith('.txt'):
            file_path = os.path.join(document_path, file)
            try:
                loader = TextLoader(file_path)
                loaded_doc = loader.load()
                documents.extend(loaded_doc)
                print(f"successfully loaded: {file}")
            except Exception as e:
                print(f"Error loading {file}: {e}")

    print(f"\nTotal documents loaded: {len(documents)}")
    publications = [doc.page_content for doc in documents]
    return publications


# Load publications safely at import time (empty list if path invalid)
try:
    publications = load_research_publications(document_path)
except Exception as e:
    print(f"Unexpected error loading publications: {e}")
    publications = []