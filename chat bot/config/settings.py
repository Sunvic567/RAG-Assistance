import os
from dotenv import load_dotenv

load_dotenv()

PINECONE_DB_PATH = os.getenv("PINECONE_DB_PATH", "./researchdb")
RESEARCH_DIR = os.getenv("RESEARCH_PAPERS_PATH", "./research_papers")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL_NAME = "gemini-2.5-flash"
PINECONE_API_KEY=os.getenv("PINECONE_API_KEY")
PINECONE_ENV = os.getenv("PINECONE_ENV")
PINECONE_INDEX = os.getenv("PINECONE_INDEX", "research-memory")
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
