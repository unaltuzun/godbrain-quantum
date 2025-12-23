import asyncio
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from seraph.seraph_jarvis import SeraphJarvis
# Forcing import from tools.py rather than tools/ package
import importlib.util
spec = importlib.util.spec_from_file_location("seraph_tools", os.path.join(os.path.dirname(__file__), "..", "seraph", "tools.py"))
tools_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tools_mod)
get_seraph_tools = tools_mod.get_seraph_tools

async def test_seraph_time():
    print("Initializing Seraph...")
    seraph = SeraphJarvis(use_router=False) # Use direct Anthropic for testing if possible, or mock
    
    print("\nChecking System Prompt...")
    system_prompt = seraph._build_system_prompt()
    print("-" * 20)
    # Print the temporal part of the system prompt
    for line in system_prompt.split("\n"):
        if "ZAMAN" in line or "tarih" in line or "saat" in line:
            print(line)
    print("-" * 20)

    print("\nChecking Tools...")
    tools = get_seraph_tools()
    tool_defs = tools.get_tool_definitions()
    time_tool = next((t for t in tool_defs if t['name'] == 'get_current_time'), None)
    if time_tool:
        print(f"Found tool: {time_tool['name']} - {time_tool['description']}")
        result = tools.execute("get_current_time", {})
        print(f"Tool execution result: {result.output}")
    else:
        print("Error: get_current_time tool not found!")

if __name__ == "__main__":
    asyncio.run(test_seraph_time())
