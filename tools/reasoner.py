import requests
from config.settings import GROQ_API_KEY

url = "https://api.groq.com/openai/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

def analyze_ai(observation):

    data = {

        "model": "llama-3.1-8b-instant",

        "messages": [

            {
                "role": "system",

                "content": """
You are an AI analyst.

Analyze observations.

Give a short explanation.

Do not create workflows.
Do not return JSON.
Respond in plain English.
"""
            },

            {
                "role": "user",
                "content": str(observation)
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