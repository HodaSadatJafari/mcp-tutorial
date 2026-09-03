import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server_params = StdioServerParameters(
    command="python",
    args=["server.py"],
)


async def main():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:

            await session.initialize()

            tools = await session.list_tools()

            print("Available tools:")

            for tool in tools.tools:
                print(f"- {tool.name}: {tool.description}")

            tools_result = await session.call_tool(
                "multiply",
                arguments={
                    "a": 25,
                    "b": 40,
                },
            )
            print(f"Result is: {tools_result.structured_content["result"]}")


if __name__ == "__main__":
    asyncio.run(main())
