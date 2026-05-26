import requests
from config.settings import GROQ_API_KEY
from tools.tool_definitions import TOOLS


url = "https://api.groq.com/openai/v1/chat/completions"


headers = {
    "Authorization":
        f"Bearer {GROQ_API_KEY}",

    "Content-Type":
        "application/json"
}


def ask_ai(prompt):

    data = {

        "model": "llama-3.1-8b-instant",

        "messages": [

            {

                "role": "system",

                "content": f"""

You are an AI workflow planner.

Convert user requests into VALID workflow JSON.

AVAILABLE TOOLS:

{TOOLS}

STRICT RULES:

- Return ONLY valid JSON
- Never explain anything
- Never invent extra tasks
- Never assume user intentions
- Only generate tasks explicitly requested
- Always return workflow object
- Use ONLY available tools

SUPPORTED ACTIONS:

1. send_message
Required:
- app
- target
- message

2. search
Required:
- app
- query

3. observe_website
Required:
- app
- url

4. open_website
Required:
- app
- url

5. click_element
Required:
- app
- element

6. type_text
Required:
- app
- text

7. submit_form
Required:
- app

GOOD EXAMPLE:

{{
    "workflow": [

        {{
            "action": "search",
            "app": "youtube",
            "query": "AI agents"
        }},

        {{
            "action": "send_message",
            "app": "whatsapp",
            "target": "aman",
            "message": "Search completed"
        }}

    ]
}}

OBSERVE WEBSITE EXAMPLE:

{{
    "workflow": [

        {{
            "action": "observe_website",
            "app": "browser",
            "url": "https://openai.com"
        }}

    ]
}}

INTERACTION EXAMPLE:

{{
    "workflow": [

        {{
            "action": "open_website",
            "app": "browser",
            "url": "https://youtube.com"
        }},

        {{
            "action": "type_text",
            "app": "browser",
            "text": "AI agents"
        }},

        {{
            "action": "submit_form",
            "app": "browser"
        }}

    ]
}}
"""
            },

            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    response = requests.post(
        url,
        headers=headers,
        json=data
    )

    result = response.json()

    return result["choices"][0]["message"]["content"]