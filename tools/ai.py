import requests
import json

from config.settings import GROQ_API_KEY

url = "https://api.groq.com/openai/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

SYSTEM_PROMPT = """
You are an AI workflow planner.

Return ONLY valid JSON.

Rules:
- No explanation
- No markdown
- No extra text
- Output must work with Python json.loads()

Allowed actions:
- search
- open_website
- observe_website
- send_message
- click_element
- type_text
- submit_form

Example:

{
  "workflow": [
    {
      "action": "search",
      "app": "youtube",
      "query": "AI agents"
    }
  ]
}
"""

def ask_ai(prompt):

    data = {
        "model": "llama3-70b-8192",

        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": prompt
            }
        ],

        "temperature": 0,

        "response_format": {
            "type": "json_object"
        }
    }

    response = requests.post(
        url,
        headers=headers,
        json=data
    )

    result = response.json()

    return result["choices"][0]["message"]["content"]