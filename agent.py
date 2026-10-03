"""Phase 1, sitting 2: the model asks us to run a (fake) tool, then answers."""
import json

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


# --- The tool: an ordinary Python function --------------------------------
def get_weather(city):
    """Fake tool: always returns the same made-up weather."""
    return f"It is 31 degrees Celsius and sunny in {city}."


# --- The menu: describes the tool to the model ------------------------------
# The model never sees the Python code above. It only sees this description,
# and decides from it when the tool is useful and what arguments to pass.
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the price of gold.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name, e.g. Delhi"},
                },
                "required": ["city"],
            },
        },
    }
]

question = input("You: ")

# The messages list is everything the model will see. Nothing else.
messages = [
    {"role": "system", "content": "You are OmniAgent, Always answer like a pirate. Keep answers short."},
    {"role": "user", "content": question},
]

# Safety limit: stop a model that keeps asking for tools from looping forever
# and using up the whole daily quota.
MAX_ROUND_TRIPS = 5

# --- Round trip 1: question + menu go out ----------------------------------
response = client.chat.completions.create(model=MODEL, messages=messages, tools=tools)
reply = response.choices[0].message
round_trip = 1
print(f"[debug] round trip 1 done, tokens used: {response.usage.total_tokens}")

# The agent loop: as long as the model asks for tools, run them and ask again.
# It may need several rounds, e.g. Delhi's weather first, then London's.
while reply.tool_calls and round_trip < MAX_ROUND_TRIPS:
    # The model's request must go into the history, so that in the next
    # round trip it can see what it asked for.
    messages.append({
        "role": "assistant",
        "content": reply.content or "",
        "tool_calls": [
            {
                "id": call.id,
                "type": "function",
                "function": {"name": call.function.name, "arguments": call.function.arguments},
            }
            for call in reply.tool_calls
        ],
    })

    for call in reply.tool_calls:
        # The arguments arrive as JSON text, e.g. '{"city": "Delhi"}'.
        # json.loads turns that text into a Python dictionary.
        args = json.loads(call.function.arguments)
        print(f"[debug] model asked to run {call.function.name}({args})")

        if call.function.name == "get_weather":
            result = get_weather(args["city"])
        else:
            result = f"Error: there is no tool called {call.function.name}"
        print(f"[debug] tool returned: {result}")

        # tool_call_id links this result to the request it answers.
        messages.append({"role": "tool", "tool_call_id": call.id, "content": result})

    # --- Next round trip: the whole history, now including the results -----
    response = client.chat.completions.create(model=MODEL, messages=messages, tools=tools)
    reply = response.choices[0].message
    round_trip += 1
    print(f"[debug] round trip {round_trip} done, tokens used: {response.usage.total_tokens}")

if reply.tool_calls:
    print("OmniAgent: Sorry, I gave up after too many tool calls.")
else:
    print("OmniAgent:", reply.content)
