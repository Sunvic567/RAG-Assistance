from LLM.llm import llm
from prompt.prompt_template import prompt_template
from embeddings.insert_and_embed_publication import embedding, insert_publication
from retrival.search_db import search_research_db
from embeddings.load_publication import publications
from memory.memory import save_message, get_messages


# Set the prompt template
prompt_templates = prompt_template


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
            last_messages = get_messages(session_id="default_session", role="assistant")

            # check if there is any relevant information found both in memory and knowledge base
            if (not relevant_chunks) and (not last_messages):
                print("No relevant information found in memory or knowledge base.")
                continue

            # ---------- Memory Context ----------
            if last_messages:
                # Ensure ordering oldest → newest
                last_messages = last_messages[::-1]
                memory_text = "\n\n".join([msg["message"] for msg in last_messages])
                memory_context = f"Previous Conversation:\n{memory_text}\n\n"
            else:
                memory_context = ""

            # ---------- Research Context ----------
            if relevant_chunks:
                research_text = "\n\n".join([
                    f"From {chunk.get('title', 'unknown')}:\n{chunk['content']}"
                    for chunk in relevant_chunks
                ])
                research_context = f"Relevant Research:\n{research_text}\n\n"
            else:
                research_context = ""

            # ---------- Final Combined Context ----------
            context = memory_context + research_context
            prompt = prompt_templates.format(context=context, question=query)
            response = llm.invoke(prompt)
            answer = getattr(response, "content", str(response))
            # Save interaction to memory
            save_message(session_id="default_session", role="user", message=query)
            save_message(session_id="default_session", role="ai", message=answer)
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