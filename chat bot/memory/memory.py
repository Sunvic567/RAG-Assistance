from supabase import create_client
from config.settings import SUPABASE_DB_URL, SUPABASE_KEY
import os

SUPABASE_DB_URL = SUPABASE_DB_URL
SUPABASE_KEY = SUPABASE_KEY

supabase = create_client(SUPABASE_DB_URL, SUPABASE_KEY)

def save_message(session_id: str, role: str, message: str, embedding=None, pinecone_id=None):
    data = {
        "session_id": session_id,
        "role": role,
        "message": message,
        "pinecone_id": pinecone_id
    }

    if embedding is not None:
        data["embedding"] = embedding

    supabase.table("agent_memory").insert(data).execute()


def get_messages(session_id: str, role: str):
    response = supabase.table("agent_memory").select("message").eq("session_id", session_id).eq("role", role).order("created_at", desc=False).limit(3).execute()
    last_messages = list(reversed(response.data))
    return last_messages


