"""Query Open-Meteo weather, then let an OpenAI agent explain it in English."""

import asyncio
import sys
from typing import Annotated

import requests
from pydantic import BaseModel, Field

from agents import Agent, Runner
from agents.decorators import tool


class Weather(BaseModel):
    city: str
    temperature_c: float = Field(allow_inf_nan=False)
    wind_speed_kmh: float = Field(ge=0, allow_inf_nan=False)
    weather_code: int = Field(description="WMO weather interpretation code")
    data_time: str
    timezone: str
    source: str = "Open-Meteo (https://open-meteo.com/), model-based current conditions"


def fetch_weather(city: str) -> Weather | str:
    """Fetch current model-based conditions; never substitute invented weather."""
    try:
        response = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "en", "format": "json"},
            timeout=15,
        )
        response.raise_for_status()
        locations = response.json().get("results", [])
        if not locations:
            return "未找到该城市。请提供城市英文名；不要编造天气。"
        location = locations[0]
        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "current": "temperature_2m,weather_code,wind_speed_10m",
                "temperature_unit": "celsius",
                "wind_speed_unit": "kmh",
                "timezone": "auto",
            },
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        current = data["current"]
        return Weather(
            city=", ".join(
                str(location[key]) for key in ("name", "admin1", "country") if location.get(key)
            ),
            temperature_c=current["temperature_2m"],
            wind_speed_kmh=current["wind_speed_10m"],
            weather_code=current["weather_code"],
            data_time=current["time"],
            timezone=data["timezone"],
        )
    except (requests.RequestException, ValueError, KeyError, TypeError, AttributeError):
        return "天气查询失败：网络不可用、服务异常或数据不完整。请稍后重试；不要编造天气。"


@tool
async def get_weather(city: Annotated[str, "City name, preferably in English"]) -> Weather | str:
    """Get current weather from Open-Meteo, including the matched location and data time."""
    print("[天气工具] 正在查询 Open-Meteo…")
    return await asyncio.to_thread(fetch_weather, city)


agent = Agent(
    name="Weather assistant",
    instructions=(
        "你是天气助手。回答天气问题前必须调用 get_weather，使用英文城市名查询。"
        "仅根据工具返回的数据用英文回答（包括查询失败时的回复），列出匹配的城市、国家、摄氏温度、风速、"
        "数据时间和时区，并注明来源 Open-Meteo（数值天气模型数据，不是现场实测）。"
        "天气代码是 WMO 代码；不确定含义时保留代码，不猜测。"
        "城市搜索返回最匹配的地点；请用户核对地点，尤其是同名城市。"
        "工具失败就明确告知无法获取，不要用记忆补充天气，不要将当前温度说成全天温度范围。"
    ),
    tools=[get_weather],
)


async def main():
    city = " ".join(sys.argv[1:]).strip() or "Tokyo"
    result = await Runner.run(agent, input=f"请查询这个城市的当前天气：{city}")
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
