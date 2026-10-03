"""Phase 1, sitting 1: send one question to the model and print its reply."""
from openai import OpenAI

import config

# Groq accepts the same request format as OpenAI, so the openai library works
# as long as we point it at Groq's address instead of OpenAI's.
client = OpenAI(
    api_key=config.GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)

# Groq rotates its models. If this name stops working, pick a new one from
# console.groq.com/docs/models
MODEL = "openai/gpt-oss-120b"

question = input("You: ")

# The messages list is everything the model will see. Nothing else.
messages = [
    {"role": "system", "content": "You are OmniAgent, Always answer like a pirate. Keep answers short."},
    {"role": "user", "content": question},
]

response = client.chat.completions.create(model=MODEL, messages=messages)

print("OmniAgent:", response.choices[0].message.content)

# Every request uses up part of the free daily quota, so keep an eye on it.
print(f"[debug] tokens used: {response.usage.total_tokens}")
