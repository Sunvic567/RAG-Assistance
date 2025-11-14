from langchain_google_genai import GoogleGenerativeAI
from config.settings import GOOGLE_API_KEY, MODEL_NAME

llm = GoogleGenerativeAI(
    model=MODEL_NAME,
    api_key=GOOGLE_API_KEY,
    temperature=0.7,
    max_output_tokens=1024
)


