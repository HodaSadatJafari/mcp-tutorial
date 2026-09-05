import asyncio
import json
import os

from dotenv import load_dotenv
from openai import OpenAI

from mcp import (
    ClientSession,
    StdioServerParameters,
)

from mcp.client.stdio import stdio_client

from mcp.types import TextResourceContents

load_dotenv()

# =========================================================
# OPENAI CLIENT
# =========================================================
openai_client = OpenAI(
    base_url=os.environ["BASE_URL"],
    api_key=os.environ["API_KEY"],
)
# =========================================================
# MCP SERVER CONFIGURATION
# =========================================================

server_params = StdioServerParameters(
    command="python",
    args=["part_4/server.py"],
)


# =========================================================
# MCP → OPENAI TOOL CONVERSION
# =========================================================
def mcp_tools_to_openai_tools(
    mcp_tools,
) -> list[dict]:
    """
    Convert MCP tool definitions into
    OpenAI function tool definitions.
    """

    tools = []

    for tool in mcp_tools:

        tools.append(
            {
                "type": "function",
                "name": tool.name,
                "description": (tool.description or ""),
                "parameters": tool.input_schema,
            }
        )

    return tools


# =========================================================
# READ MCP RESOURCE
# =========================================================
async def read_document(
    session: ClientSession,
    filename: str,
) -> str:
    """
    Read a document through MCP.
    """

    uri = f"document://{filename}"

    result = await session.read_resource(uri)

    texts = []

    for content in result.contents:

        if isinstance(
            content,
            TextResourceContents,
        ):
            texts.append(content.text)

    return "\n".join(texts)


# =========================================================
# CALL MCP TOOL
# =========================================================
async def call_mcp_tool(
    session: ClientSession,
    tool_name: str,
    arguments: dict,
):
    """
    Execute an MCP tool and return its result.
    """

    result = await session.call_tool(
        tool_name,
        arguments=arguments,
    )

    return result


# =========================================================
# EXTRACT TEXT FROM MCP RESULT
# =========================================================
def extract_mcp_text(result) -> str:
    """
    Extract text content from an MCP tool result.
    """

    texts = []

    for content in result.content:
        if hasattr(content, "text"):
            texts.append(content.text)

    return "\n".join(texts)


# =========================================================
# SEARCH DOCUMENTS
# =========================================================
async def search_documents(
    session: ClientSession,
    query: str,
) -> list[str]:
    """
    Call the MCP search_documents tool.
    """

    result = await call_mcp_tool(
        session=session,
        tool_name="search_documents",
        arguments={"query": query},
    )

    # Prefer structured content when available
    if result.structured_content:

        data = result.structured_content

        if isinstance(data, list):
            return data

        if isinstance(data, dict):

            # Possible shape:
            # {"result": ["mcp.txt"]}

            for value in data.values():

                if isinstance(value, list):
                    return value

    # Fallback to text content
    text = extract_mcp_text(result)

    if not text:
        return []

    try:

        data = json.loads(text)

        if isinstance(data, list):
            return data

    except json.JSONDecodeError:
        pass

    return []


# =========================================================
# BUILD DOCUMENT CONTEXT
# =========================================================
async def build_document_context(
    session: ClientSession,
    filenames: list[str],
) -> str:
    """
    Read all matching documents through MCP resources
    and combine them into context for the LLM.
    """

    if not filenames:
        return "No documents were found."

    documents = []

    for filename in filenames:

        try:

            content = await read_document(
                session,
                filename,
            )

            documents.append(f"""
                --- DOCUMENT: {filename} ---
                {content}
                --- END DOCUMENT ---
                """)

        except Exception as exc:
            documents.append(f"""
                --- DOCUMENT: {filename} ---
                Could not read document:
                {exc}
                --- END DOCUMENT ---
                """)

    return "\n".join(documents)


# =========================================================
# PROCESS ONE USER QUESTION
# =========================================================
async def process_question(
    session: ClientSession,
    openai_tools: list[dict],
    question: str,
    conversation: list,
):
    """
    Process one user question.

    For this demo, every question is required to use
    the MCP document search tool first.
    """

    conversation.append(
        {
            "role": "user",
            "content": question,
        }
    )

    response = openai_client.responses.create(
        model="gpt-4o-mini",
        instructions="""
            You are a document question-answering assistant.

            IMPORTANT RULE:

            For EVERY user question, you MUST first use the
            search_documents MCP tool.

            Do not answer from your own knowledge before searching
            the documents.

            After the search:

            1. Look at the returned filenames.
            2. The application will provide the contents of the
            matching documents.
            3. Answer using those documents.
            4. If no documents match the question, clearly say that
            the provided document collection does not contain
            enough information to answer the question.
            5. Do not invent information that is not present in
            the documents.

            Examples:

            User:
            "What is MCP?"

            You should search:
            search_documents(query="MCP")

            User:
            "What is .NET?"

            You should search:
            search_documents(query=".NET")

            If the search returns no documents, do NOT answer from
            your general knowledge.
            """,
        input=conversation,
        tools=openai_tools,
        # Important for this learning example:
        # force the model to make a tool call.
        tool_choice="required",
    )

    # -----------------------------------------------------
    # TOOL CALL LOOP
    # -----------------------------------------------------
    while True:

        tool_calls = [item for item in response.output if item.type == "function_call"]

        # -------------------------------------------------
        # No more tool calls → final answer
        # -------------------------------------------------
        if not tool_calls:
            answer = response.output_text
            conversation.extend(response.output)
            return answer

        # -------------------------------------------------
        # Execute MCP tools
        # -------------------------------------------------
        tool_outputs = []

        for tool_call in tool_calls:

            print(f"\n[MCP] Calling tool: " f"{tool_call.name}")

            try:

                arguments = json.loads(tool_call.arguments)

                result = await call_mcp_tool(
                    session=session,
                    tool_name=tool_call.name,
                    arguments=arguments,
                )

                # -----------------------------------------
                # SEARCH DOCUMENTS
                # -----------------------------------------
                if tool_call.name == "search_documents":

                    filenames = []

                    # Structured result
                    if result.structured_content:

                        data = result.structured_content

                        if isinstance(
                            data,
                            list,
                        ):
                            filenames = data

                        elif isinstance(
                            data,
                            dict,
                        ):

                            for value in data.values():

                                if isinstance(
                                    value,
                                    list,
                                ):
                                    filenames.extend(value)

                    # Text fallback
                    if not filenames:

                        text = extract_mcp_text(result)

                        try:

                            data = json.loads(text)

                            if isinstance(
                                data,
                                list,
                            ):
                                filenames = data

                        except json.JSONDecodeError:
                            pass

                    print(
                        "[MCP] Matching documents:",
                        filenames,
                    )

                    # -------------------------------------
                    # READ MATCHING RESOURCES
                    # -------------------------------------
                    document_context = await build_document_context(
                        session,
                        filenames,
                    )

                    tool_output = document_context

                else:

                    tool_output = extract_mcp_text(result)

            except Exception as exc:

                tool_output = f"MCP tool error: {exc}"

            # ---------------------------------------------
            # Return MCP result to LLM
            # ---------------------------------------------
            tool_outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": tool_call.call_id,
                    "output": tool_output,
                }
            )

        # -------------------------------------------------
        # Ask LLM to answer using the MCP results
        # -------------------------------------------------

        response = openai_client.responses.create(
            model="gpt-4o-mini",
            instructions="""
                Answer the user's question using the MCP document
                content returned by the previous tool call.

                Do not use outside knowledge.

                If the MCP search found no documents, explain that
                the provided document collection does not contain
                enough information to answer the question.
                """,
            previous_response_id=response.id,
            input=tool_outputs,
            tools=openai_tools,
        )


# =========================================================
# MAIN APPLICATION
# =========================================================
async def main():

    print("=" * 60)
    print("MCP DOCUMENT ASSISTANT")
    print("=" * 60)

    print("\nConnecting to MCP server...")

    # -----------------------------------------------------
    # Start MCP server
    # -----------------------------------------------------
    async with stdio_client(server_params) as (read, write):

        async with ClientSession(
            read,
            write,
        ) as session:

            # ---------------------------------------------
            # MCP initialization
            # ---------------------------------------------
            await session.initialize()

            print("MCP connection established.")

            # ---------------------------------------------
            # Get available tools
            # ---------------------------------------------
            tools_result = await session.list_tools()

            openai_tools = mcp_tools_to_openai_tools(tools_result.tools)

            print("\nAvailable MCP tools:")

            for tool in tools_result.tools:

                print(f"  - {tool.name}")

            # ---------------------------------------------
            # Show resource templates
            # ---------------------------------------------

            templates_result = await session.list_resource_templates()

            print("\nAvailable MCP resource templates:")

            for template in templates_result.resource_templates:

                print(f"  - {template.uri_template}")

            # ---------------------------------------------
            # Conversation history
            # ---------------------------------------------
            conversation = []

            print("\nType 'exit' or 'quit' to stop.")

            # =============================================
            # CHAT LOOP
            # =============================================
            while True:

                try:

                    question = input("\nYou: ").strip()

                except (
                    KeyboardInterrupt,
                    EOFError,
                ):

                    print("\nGoodbye!")
                    break

                # -----------------------------------------
                # Exit
                # -----------------------------------------
                if question.lower() in {
                    "exit",
                    "quit",
                }:

                    print("Goodbye!")
                    break

                if not question:
                    continue

                # -----------------------------------------
                # Process question
                # -----------------------------------------
                try:

                    answer = await process_question(
                        session=session,
                        openai_tools=openai_tools,
                        question=question,
                        conversation=conversation,
                    )

                    print(f"\nAssistant: {answer}")

                except Exception as exc:

                    print(f"\nError: {exc}")


# =========================================================
# ENTRY POINT
# =========================================================
if __name__ == "__main__":
    asyncio.run(main())
