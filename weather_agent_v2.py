#langGraph version
import os
from typing import Annotated, Optional
import requests
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from dotenv import load_dotenv
load_dotenv()



# 建立 tool
@tool
def get_weather(location: str, date: Optional[str] = None) -> str:
    """查詢指定城市或地區的當天或指定日期的天氣預報。"""
    api_key = os.getenv("WEATHER_API_KEY")
    if not api_key:
        return "Weather API 金鑰未設定。"

    if date:
        url = "http://api.weatherapi.com/v1/forecast.json"
        params = {
            "key": api_key,
            "q": location,
            "days": 10,
            "lang": "zh_tw",
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code != 200:
                return f"找不到關於 '{location}' 的天氣預報資訊，請確認地名是否正確。"

            data = response.json()
            forecast_days = data.get("forecast", {}).get("forecastday", [])
            target_day = None

            for item in forecast_days:
                if item.get("date") == date:
                    target_day = item
                    break

            if not target_day:
                return f"找不到 {location} 在 {date} 的天氣預報資料。"

            day_data = target_day.get("day", {})
            maxtemp_c = day_data.get("maxtemp_c")
            mintemp_c = day_data.get("mintemp_c")
            avgtemp_c = day_data.get("avgtemp_c")

            return (
                f"{location} 在 {date} 的天氣預報：\n"
                f"最高溫：{maxtemp_c}°C\n"
                f"最低溫：{mintemp_c}°C\n"
                f"平均溫：{avgtemp_c}°C"
            )
        except Exception as e:
            return f"與天氣服務連線時發生錯誤：{str(e)}"

    url = "http://api.weatherapi.com/v1/current.json"
    params = {
        "key": api_key,
        "q": location,
        "aqi": "yes",
        "lang": "zh_tw",
    }

    try:
        response = requests.get(url, params=params, timeout=10)

        if response.status_code != 200:
            return f"找不到關於 '{location}' 的天氣資訊，請確認地名是否正確。"

        data = response.json()
        city = data["location"]["name"]
        region = data["location"]["region"]
        temp_c = data["current"]["temp_c"]
        condition = data["current"]["condition"]["text"]
        humidity = data["current"]["humidity"]
        pm25 = data["current"]["air_quality"]["pm2_5"]

        result = (
            f"{region}{city}目前的天氣狀況為：{condition}。\n"
            f"現在氣溫 {temp_c}°C，相對濕度 {humidity}%。\n"
            f"當地 PM2.5 空氣品質指數為：{pm25:.1f}。"
        )
        return result

    except Exception as e:
        return f"與天氣服務連線時發生錯誤：{str(e)}"
    
# LangGraph structure

# 定義state
class AgentState(dict):
    # messages 以新舊訊息串接
    messages: Annotated[list[BaseMessage], add_messages]
    
    
    
    
# 初始化 LLM 並綁定工具 
tools = [get_weather]
llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
llm_with_tools = llm.bind_tools(tools)

# 定義節點
def call_model(state: AgentState):
    """LLM 節點：負責思考、接收訊息，並決定下一步"""
    system_prompt = SystemMessage(
        content=(
            "你是一個貼心的生活助手。"
            "如果使用者詢問天氣，請先判斷是否有指定日期。"
            "若有指定日期，請使用工具查詢該日期的天氣預報；"
            "若沒有指定日期，請查詢當天的天氣。"
            "請用繁體中文回覆，並整理成易讀的報告。"
        )
    )
    # 將 System Prompt 插入到對話最前面
    messages = [system_prompt] + state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

# 建立工具節點 (LangGraph 內建的 ToolNode 會自動處理工具執行與異常)
tool_node = ToolNode(tools)

# 定義 Conditional Edge 決定流向
def should_continue(state: AgentState):
    """判斷 LLM 的最新回覆是否包含工具呼叫(Tool Calls)"""
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"  # 執行工具節點
    return END          # 沒有要用工具了，直接結束對話

# 組裝圖 (Workflow)
workflow = StateGraph(AgentState)

# 1. 註冊節點
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)

# 2. 設定起點
workflow.add_edge(START, "agent")

# 3. 設定條件邊
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "tools": "tools",  # 如果函數判斷需要執行工具，走去 tools 節點
        END: END           # 如果結束，走去 END
    }
)

# 4. 工具執行完後，把結果重新交給 agent 看結果並進行下一輪思考
workflow.add_edge("tools", "agent")

# 5. 編譯圖
app = workflow.compile()

#  測試執行 
if __name__ == "__main__":
    user_input_location = input("請輸入地點（例如：台中）：")
    user_input_date = input("請輸入日期（YYYY-MM-DD，留空則查詢今天）：")
    
    # 定義初始狀態(使用者輸入的訊息)
    initial_state = {
        "messages": [("user", f"幫我查 {user_input_location} 在 {user_input_date if user_input_date else '今天'} 的天氣")]
    }
    
    # 執行圖
    final_state = app.invoke(initial_state)
    
    # 印出最後一條訊息
    print("\n--- Agent 最終回覆 ---")
    print(final_state["messages"][-1].content)