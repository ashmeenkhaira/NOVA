"""The agent loop: send a conversation, run any tools the model asks for, return the answer.

Tools live in tools.py - this file does not change when you add one.
Run this file directly to chat in the terminal; bot.py will import run_agent.
"""
from openai import OpenAI

import config
import tools

# Groq accepts the same request format as OpenAI, so the openai library works
# as long as we point it at Groq's address instead of OpenAI's.
client = OpenAI(
    api_key=config.GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)

# Groq rotates its models. If this name stops working, pick a new one from
# console.groq.com/docs/models
MODEL = "openai/gpt-oss-120b"

# Safety limit: stop a model that keeps asking for tools from looping forever
# and using up the whole daily quota.
MAX_ROUND_TRIPS = 5

# The menu of tools, built from the registry in tools.py.
TOOL_MENU = tools.tool_menu()

SYSTEM_PROMPT = "You are OmniAgent, Always answer like a helpful assistant. Keep answers short."


def run_agent(history):
    """Answer the last message in history, running any tools the model asks for.

    history is the conversation so far: user and assistant messages only,
    with the new user message last. It is not changed - the caller decides
    what to keep. Returns the answer as text.
    """
    # The system prompt is added fresh on every call, so trimming the history
    # can never cut it off.
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

    # --- Round trip 1: conversation + menu go out --------------------------
    response = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOL_MENU)
    reply = response.choices[0].message
    round_trip = 1
    print(f"[debug] round trip 1 done, tokens used: {response.usage.total_tokens}")

    # The agent loop: as long as the model asks for tools, run them and ask again.
    # It may need several rounds, e.g. Delhi's weather first, then London's.
    while reply.tool_calls and round_trip < MAX_ROUND_TRIPS:
        # The model's request must go into the messages, so that in the next
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
            print(f"[debug] model asked to run {call.function.name}({call.function.arguments})")
            result = tools.run_tool(call.function.name, call.function.arguments)
            print(f"[debug] tool returned: {result}")

            # tool_call_id links this result to the request it answers.
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})

        # --- Next round trip: everything so far, now including the results --
        response = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOL_MENU)
        reply = response.choices[0].message
        round_trip += 1
        print(f"[debug] round trip {round_trip} done, tokens used: {response.usage.total_tokens}")

    if reply.tool_calls:
        return "Sorry, I gave up after too many tool calls."
    return reply.content


# This block runs only when you start this file directly (python agent.py),
# not when another file imports it (import agent).
if __name__ == "__main__":
    history = []
    print("Chat with OmniAgent. Type 'quit' to stop.")

    while True:
        question = input("You: ")
        if question.strip().lower() == "quit":
            break

        history.append({"role": "user", "content": question})
        answer = run_agent(history)
        history.append({"role": "assistant", "content": answer})

        print("OmniAgent:", answer)
