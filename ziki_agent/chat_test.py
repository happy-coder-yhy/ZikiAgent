"""Quick demo of Ziki Agent (Hermes-powered)."""

from ziki_agent.core import Agent
from ziki_agent import memory
import asyncio
import uuid

# Test user IDs decoded from JWT access_tokens in .env
ADMIN_USER_ID = "5d062691-50f5-4369-b10c-b810271919f1"
COLLECTOR_USER_ID = "27b5f00f-cc82-4eaa-889b-d34ad839098a"


async def main():
    agent = Agent()
    # session_id = str(uuid.uuid4())[:8]
    session_id = '8f58d9fc'

    # Switch between ADMIN_USER_ID / COLLECTOR_USER_ID to test different roles
    test_user_id = ADMIN_USER_ID

    # Turn 1
    # result = await agent.run(session_id, "你好，我是小明", user_id=test_user_id)
    # print(f"[{session_id}] User: 你好，我是小明")
    # print(f"[{session_id}] Ziki: {result.response}\n")

    # Turn 2 — remembers context via SQLite (scoped to user_id)
    text = "我最近干了什么"
    result = await agent.run(session_id, text, user_id=test_user_id)
    print(f"[{session_id}] User: {text}")
    print(f"[{session_id}] Ziki: {result.response}\n")

    # text = "计划采集条数为5，作业描述为memory测试2"
    # result2 = await agent.run(session_id, text, user_id=test_user_id)
    # print(f"[{session_id}] User: {text}")
    # print(f"[{session_id}] Ziki: {result2.response}\n")

    # text = "我是北京人"
    # result2 = await agent.run(session_id, text, user_id=test_user_id)
    # print(f"[{session_id}] User: {text}")
    # print(f"[{session_id}] Ziki: {result2.response}\n")

    # Cleanup
    # memory.clear_session(session_id, user_id=test_user_id)
    # agent.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
