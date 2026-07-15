"""Quick demo of Ziki Agent (Hermes-powered)."""

from ziki_agent.core import Agent
from ziki_agent import memory
import asyncio
import uuid


async def main():
    agent = Agent()
    session_id = str(uuid.uuid4())[:8]

    # Turn 1
    # result = await agent.run(session_id, "你好，我是小明")
    # print(f"[{session_id}] User: 你好，我是小明")
    # print(f"[{session_id}] Ziki: {result.response}\n")

    # Turn 2 — remembers context via SQLite
    text = "查询agentTest设备的绑定情况，输出采集员和作业详细信息"
    result = await agent.run(session_id, text)
    print(f"[{session_id}] User: {text}")
    print(f"[{session_id}] Ziki: {result.response}\n")

    # Cleanup
    memory.clear_session(session_id)
    agent.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
