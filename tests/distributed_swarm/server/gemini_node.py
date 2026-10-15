import os
import sys
import time

SYS_DIR = os.path.dirname(os.path.abspath(__file__))
SWARM_DIR = os.path.dirname(SYS_DIR)
sys.path.append(SWARM_DIR)

from config import GEMINI_API_KEY, GEMINI_MODEL
from google import genai
from google.genai import types


class GeminiNode:

    def __init__(self):
        if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
            raise ValueError(
                "GEMINI_API_KEY is missing or not set in distributed_swarm/config.py!"
            )

        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.model = GEMINI_MODEL

    def generate_agent_response(
        self, system_instruction: str, user_task: str, context_summary: str
    ) -> str:
        prompt = (
            f"CONTEXT ATTACHMENT:\n{context_summary}\n\n"
            f"TASK:\n{user_task}\n\n"
            f"Please respond concisely as an enterprise sub-agent."
        )

        config = types.GenerateContentConfig(
            system_instruction=system_instruction
        )

        # Retry loop for 429 / 503 API rate limits
        for attempt in range(1, 4):
            try:
                response = self.client.models.generate_content(
                    model=self.model, contents=prompt, config=config
                )
                if response.text:
                    return response.text
            except Exception as e:
                err_msg = str(e)
                if (
                    "429" in err_msg or "503" in err_msg
                ) and attempt < 3:
                    time.sleep( attempt * 2.0 )  # Exponential backoff delay
                    continue
                return f"GEMINI_API_ERROR: {err_msg}"

        return "GEMINI_API_ERROR: Max retries exceeded."