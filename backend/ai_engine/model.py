import ollama
from database.db import get_all_memories

MODEL_NAME = "qwen2.5:3b"

SYSTEM_PROMPT = """
You are NOVA, an intelligent personal AI assistant.

Your personality:
- Friendly, intelligent and professional.
- Calm and conversational.
- Soft female assistant personality.

Your responsibilities:
- Answer questions.
- Help manage daily tasks.
- Organize schedules.
- Remember useful information about the user.
- Provide helpful suggestions.

Important instructions:
- Use the conversation history to maintain context.
- Use saved memories when relevant.
- Never invent personal information.
- Do not claim to remember something that is not available.
- Communicate naturally and clearly.
"""


def ask_nova(message, history):
    memories = get_all_memories()

    memory_context = ""

    if memories:
        memory_context = "\n\nImportant information remembered about the user:\n"
        memory_context += "\n".join(f"- {memory}" for memory in memories)

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT + memory_context
        }
    ]

    messages.extend(history)

    messages.append({
        "role": "user",
        "content": message
    })

    response = ollama.chat(
        model=MODEL_NAME,
        messages=messages
    )

    return response["message"]["content"]