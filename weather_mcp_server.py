import sys
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from weather_agent import agent

mcp = FastMCP("weather-agent")


@mcp.tool()
def query_weather(location: str, date: Optional[str] = None) -> str:
    """查詢指定地點的當天或指定日期天氣。"""
    prompt = f"幫我查 {location} 的天氣"
    if date:
        prompt = f"幫我查 {location} 在 {date} 的天氣"

    response = agent.invoke({"messages": [("user", prompt)]})
    return response["messages"][-1].content


if __name__ == "__main__":
    mcp.run(transport="stdio")
