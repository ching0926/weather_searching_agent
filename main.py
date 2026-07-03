from datetime import date
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field
from weather_agent import get_weather, agent

#建立instance of FastAPI
app = FastAPI()

#定義傳送的資料格式
class WeatherRequest(BaseModel):
    location: str
    date: Optional[str] = Field(
        default_factory=lambda: date.today().strftime("%Y-%m-%d"),
        description="指定未來某一天日期，格式為 YYYY-MM-DD"
    )
    
#建立API路由，接收使用者查詢請求
@app.post("/search-weather")
async def get_weather(request: WeatherRequest):
    location = request.location
    weather_date = request.date
    #weather_info = get_current_weather(location)
    response = agent.invoke({"messages": [("user", f"幫我查 {location} 在 {weather_date} 的天氣")]})
    weather_info = response["messages"][-1].content
    return {"location": location, "date": weather_date, "weather_info": weather_info}