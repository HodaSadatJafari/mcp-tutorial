import asyncio
import os
import json

from dotenv import load_dotenv
from openai import AsyncOpenAI

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()

openai = AsyncOpenAI(
    base_url=os.environ["BASE_URL"],
    api_key=os.environ["API_KEY"],
)


server_params = StdioServerParameters(
    command="python",
    args=["server.py"],
)


def mcp_tools_to_openai_tools(mcp_tools):

    tools = []

    for tool in mcp_tools:

        tools.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.input_schema,
                },
            }
        )

    return tools


async def call_llm(messages, tools):
    response = await openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=tools,
    )
    return response


async def main():

    async with stdio_client(server_params) as (read, write):

        async with ClientSession(read, write) as session:

            await session.initialize()

            tools_result = await session.list_tools()

            for tool in tools_result.tools:
                print(tool.name)

            tools = mcp_tools_to_openai_tools(tools_result.tools)

            user_message = "What is 15 percent of 240?"

            messages = [
                {
                    "role": "user",
                    "content": user_message,
                }
            ]
            while True:

                response = await call_llm(messages, tools)

                message = response.choices[0].message

                if not message.tool_calls:
                    print(message.content)
                    break

                messages.append(message)

                for tool_call in message.tool_calls:

                    result = await session.call_tool(
                        tool_call.function.name,
                        arguments=json.loads(tool_call.function.arguments),
                    )

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": str(result),
                        }
                    )


if __name__ == "__main__":
    asyncio.run(main())
