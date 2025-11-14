from LLM.llm import llm
from prompt.prompt_template import prompt_Tempalate
from embeddings.insert_and_embed_publication import embedding, insert_publication, publications
from retrival.search_db import search_research_db


# Set the prompt template
prompt_templates = prompt_Tempalate


# we combine retrieved knowledge with an LLM:
def answer_research_question(embedding, llm):
    while True:
        try:
            query = input("\n👤 You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n/AI🤖: Goodbye")
            break

        if query.lower() in {"quit", "exit"}:
            print("/AI🤖: Goodbye")
            break
        if not query:
            continue

        try:
            relevant_chunks = search_research_db(query, embedding, top_k=3)
            if not relevant_chunks:
                print("No relevant information found in the knowledge base.")
                continue  # skip to next prompt

            # Build context from research
            context = "\n\n".join([
                f"From {chunk.get('title', 'unknown')}:\n{chunk['content']}"
                for chunk in relevant_chunks
            ])
            prompt = prompt_templates.format(context=context, question=query)

            response = llm.invoke(prompt)
            answer = getattr(response, "content", str(response))
            print("/AI🤖:", answer)
        except Exception as e:
            print(f"LLM error: {e}")
            print("Sorry, I couldn't generate an answer at this time.")


if __name__ == "__main__":
    # Initialize knowledge base: insert publications into Supabase memories (if any)
    try:
        if publications:
            print("Inserting publications into the memory store...")
            insert_publication(publications)
        else:
            print("No publications found. Add files to your research directory (RESEARCH_PAPERS_PATH).")
    except Exception as e:
        print(f"Error initializing knowledge base: {e}")

    # run interactive loop; pass None for collection (kept for compatibility)
    answer_research_question(embedding, llm)