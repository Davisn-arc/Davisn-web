import os
import logging
from pathlib import Path

from dotenv import load_dotenv
from google import genai

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger("Davisn.AI")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

SYSTEM_INSTRUCTION = """
You are Davisn, a helpful and intelligent AI assistant.

Your personality:
- Friendly, clear, and respectful.
- Explain difficult topics step by step.
- Be concise when a short answer is enough.
- Be honest when you do not know something.
- Do not pretend to access the user's computer or files.
- Help users with learning, creativity, technology, and everyday tasks.
"""


def chat(message, history=None, memory_context=None):
    """Generate a cloud AI response using Gemini."""

    if not GEMINI_API_KEY:
        return {
            "success": False,
            "message": "Gemini API key is missing. Please configure GEMINI_API_KEY."
        }

    message = str(message or "").strip()

    if not message:
        return {
            "success": False,
            "message": "Please enter a message."
        }

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)

        prompt_parts = [SYSTEM_INSTRUCTION]

        if memory_context:
            prompt_parts.append(
                "Relevant saved context:\n" + str(memory_context)
            )

        if history:
            prompt_parts.append("Previous conversation:")

            for item in history[-20:]:
                role = str(item.get("role", "user")).lower()
                content = item.get("message", item.get("content", ""))

                if content:
                    speaker = "Davisn" if role == "assistant" else "User"
                    prompt_parts.append(f"{speaker}: {content}")

        prompt_parts.append(f"User: {message}")
        prompt_parts.append("Davisn:")

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents="\n\n".join(prompt_parts)
        )

        reply = getattr(response, "text", None)

        if not reply:
            return {
                "success": False,
                "message": "Gemini returned an empty response. Please try again."
            }

        return {
            "success": True,
            "message": reply.strip(),
            "mode": "cloud"
        }

    except Exception:
        logger.exception("Gemini request failed")

        return {
            "success": False,
            "message": "Davisn couldn't reach Gemini. Please try again later."
        }
