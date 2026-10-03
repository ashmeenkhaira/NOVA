"""Every tool the agent can use lives here.

To add a tool:
  1. Write an ordinary Python function.
  2. Add an entry for it to the TOOLS dictionary at the bottom.
agent.py picks it up automatically - no changes needed there.
"""
import json
import ddgs

# --- The tools: ordinary Python functions ----------------------------------

def get_weather(city):
    """Fake tool: always returns the same made-up weather."""
    return f"It is 31 degrees Celsius and sunny in {city}."


def get_current_time():
    """Return the current date and time as text."""
    from datetime import datetime
    now = datetime.now()
    return now.strftime("%A, %d %B %Y, %I:%M %p")

def search_web(query):
    """Search the web for current events or facts you don't know. Returns the top 5 results."""
    results = ddgs.DDGS().text(query, max_results=5)
    if results:
        text=""
        for res in results:
            text+=f"Title: {res['title']}\nURL: {res['href']}\nSnippet: {res['body'][:300]}\n\n"
        return text
    else:
        return "No results found."
# --- The registry: tool name -> function + description for the model ------
# The model never sees the functions above. It only sees the "description"
# and "parameters", and decides from them when a tool is useful.
TOOLS = {
    "get_weather": {
        "function": get_weather,
        "description": "Get the current weather for a city.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name, e.g. Delhi"},
            },
            "required": ["city"],
        },
    },
        "get_current_time": {
        "function": get_current_time,
        "description": "Get the current date and time.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    "search_web": {
        "function": search_web,
        "description": "Search the web for current events or facts you don't know. Returns the top 5 results.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query, e.g. 'latest news'"},
            },
            "required": ["query"],
        },
    },

}


# --- Helpers used by agent.py -----------------------------------------------

def tool_menu():
    """Build the list of tools in the format the API expects."""
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": tool["description"],
                "parameters": tool["parameters"],
            },
        }
        for name, tool in TOOLS.items()
    ]


def run_tool(name, arguments):
    """Run the tool the model asked for and return its result as text.

    arguments is JSON text from the model, e.g. '{"city": "Delhi"}'.
    Errors are returned as text instead of crashing, so the model can
    read what went wrong and tell the user.
    """
    if name not in TOOLS:
        return f"Error: there is no tool called {name}"

    try:
        args = json.loads(arguments)
        # **args unpacks the dictionary into named arguments:
        # get_weather(**{"city": "Delhi"}) is the same as get_weather(city="Delhi")
        result = TOOLS[name]["function"](**args)
        return str(result)
    except Exception as error:
        return f"Error running {name}: {error}"
