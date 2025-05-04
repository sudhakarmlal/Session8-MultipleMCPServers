from typing import List, Optional
from pydantic import BaseModel
import os
import re
import json
from dotenv import load_dotenv
from modules.model_manager import ModelManager
from modules.tools import summarize_tools

model = ModelManager()
tool_context = summarize_tools(model.get_all_tools()) if hasattr(model, "get_all_tools") else ""


class PerceptionResult(BaseModel):
    user_input: str
    intent: Optional[str]
    entities: List[str] = []
    tool_hint: Optional[str] = None


async def extract_perception(user_input: str) -> PerceptionResult:
    """
    Uses LLMs to extract structured info:
    - intent: user's high-level goal
    - entities: keywords or values
    - tool_hint: likely MCP tool name (optional)
    """

    prompt = f"""
You are an AI that extracts structured facts from user input.

Available tools: {tool_context}

Input: "{user_input}"

Return the response as a Python dictionary with keys:
- intent: (brief phrase about what the user wants)
- entities: a list of strings representing keywords or values (e.g., ["INDIA", "ASCII"])
- tool_hint: (name of the MCP tool that might be useful, if any)
- user_input: same as above

Output only the dictionary on a single line. Do NOT wrap it in ```json or other formatting. Ensure `entities` is a list of strings, not a dictionary.
"""

    try:
        response = await model.generate_text(prompt)

        # Clean up raw if wrapped in markdown-style ```json
        raw = response.strip()
        print("RAW RESPONSE FROM PERCEPTION IS", raw)
        if not raw or raw.lower() in ["none", "null", "undefined"]:
            raise ValueError("Empty or null model output")

        # Clean and parse
        clean = re.sub(r"^```json|```$", "", raw, flags=re.MULTILINE).strip()
        print("PERCEPTION CLEAN IS", clean)

        # Handle potential JSON parsing issues
        try:
            # Replace Python's None with null for JSON parsing
            clean = clean.replace("None", "null")
            # Ensure tool_hint is properly formatted
            if '"tool_hint": null' not in clean and '"tool_hint":' in clean:
                clean = clean.replace('"tool_hint":', '"tool_hint": null')
            
            parsed = json.loads(clean)
        except json.JSONDecodeError as json_error:
            print(f"[perception] JSON parsing failed: {json_error}")
            # Create a basic parsed structure with defaults
            parsed = {
                "user_input": user_input,
                "intent": None,
                "entities": [],
                "tool_hint": None
            }

        # Ensure Keys and proper types
        if not isinstance(parsed, dict):
            parsed = {
                "user_input": user_input,
                "intent": None,
                "entities": [],
                "tool_hint": None
            }
        
        # Ensure required fields exist
        parsed.setdefault("user_input", user_input)
        parsed.setdefault("intent", None)
        parsed.setdefault("entities", [])
        parsed.setdefault("tool_hint", None)

        # Fix common issues
        if isinstance(parsed.get("entities"), dict):
            parsed["entities"] = list(parsed["entities"].values())
        elif not isinstance(parsed.get("entities"), list):
            parsed["entities"] = []

        # Ensure tool_hint is either a string or None
        if parsed.get("tool_hint") is not None and not isinstance(parsed["tool_hint"], str):
            parsed["tool_hint"] = None

        return PerceptionResult(**parsed)

    except Exception as e:
        print(f"[perception] ⚠️ LLM perception failed: {e}")
        return PerceptionResult(user_input=user_input)
