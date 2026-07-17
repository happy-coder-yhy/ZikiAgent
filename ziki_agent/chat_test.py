from ziki_agent.core import Agent
import asyncio
import uuid

# Test user IDs decoded from JWT access_tokens in .env
ADMIN_USER_ID = "5d062691-50f5-4369-b10c-b810271919f1"
COLLECTOR_USER_ID = "27b5f00f-cc82-4eaa-889b-d34ad839098a"


async def main():
    # Switch between ADMIN_USER_ID / COLLECTOR_USER_ID to test different roles
    test_user_id = COLLECTOR_USER_ID
    test_role = "collector"  # must match the user's actual role

    agent = Agent(role=test_role)
    # session_id = str(uuid.uuid4())[:8]
    # session_id = '8f58d9fc'
    session_id = '6f40d1e8'

    # Turn 1
    # result = await agent.run(session_id, "你好，我是小明", user_id=test_user_id)
    # print(f"[{session_id}] User: 你好，我是小明")
    # print(f"[{session_id}] Ziki: {result.response}\n")

    # Turn 2 — remembers context via SQLite (scoped to user_id)
    # text = "你好，今天星期几"
    # result = await agent.run(session_id, text, user_id=test_user_id)
    # print(f"[{session_id}] User: {text}")
    # print(f"[{session_id}] Ziki: {result.response}\n")

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

    text = "我是北京大学毕业的"
    full_response = ""
    async for chunk in agent.run_stream(session_id, text, user_id=test_user_id):
        if chunk.get("type") == "token":
            content = chunk.get("text", "")
            print(content, end="", flush=True)
            full_response += content
        elif chunk.get("type") == "done":
            # 也可以直接用最终的 answer，与累积的一致
            final_answer = chunk.get("answer", "")
            # 可选：覆盖 full_response = final_answer
    print()  # 换行

    text = "我喜欢周杰伦"
    full_response = ""
    async for chunk in agent.run_stream(session_id, text, user_id=test_user_id):
        if chunk.get("type") == "token":
            content = chunk.get("text", "")
            print(content, end="", flush=True)
            full_response += content
        elif chunk.get("type") == "done":
            # 也可以直接用最终的 answer，与累积的一致
            final_answer = chunk.get("answer", "")
            # 可选：覆盖 full_response = final_answer
    print()  # 换行


if __name__ == "__main__":
    asyncio.run(main())
