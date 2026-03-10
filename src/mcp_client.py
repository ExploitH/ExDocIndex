from fastmcp import Client
import asyncio,os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

MCP_PATH = r"mcp_server.py"


async def _gettools():
    async with Client(MCP_PATH) as client:
        tools = await client.list_tools()
        # print("Available tools:", tools)
        tools = [tool.model_dump(mode="json") for tool in tools]
        return tools

async def _call_tool(tool_name, arguments):
    async with Client(MCP_PATH) as client:
        result = await client.call_tool(tool_name, arguments)
        # print("Tool result:", result)
        if result.content and len(result.content) > 0:
            content_item = result.content[0]
            if hasattr(content_item, 'text') and content_item.text:
                return content_item.text
            elif hasattr(content_item, 'data'):
                return str(content_item.data)
            else:
                return str(content_item)
        return str(result)

def _convert_tools_to_openai_format(tools):
    """
    将自定义工具格式转换为 OpenAI 兼容的工具格式。
    """
    openai_tools = []
    for tool in tools:
        # 提取必要字段
        name = tool.get('name')
        description = tool.get('description', '')
        input_schema = tool.get('inputSchema') or {}

        # 确保 parameters 是合法的 JSON Schema（至少包含 type）
        if 'type' not in input_schema:
            input_schema['type'] = 'object'
        if 'properties' not in input_schema:
            input_schema['properties'] = {}

        openai_tool = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": input_schema
            }
        }
        openai_tools.append(openai_tool)
    return openai_tools
#==========SYNCLYSE FUNC==========
def get_tools():
    tools = asyncio.run(_gettools())
    return _convert_tools_to_openai_format(tools)

def call_tool(tool_name:str, arguments:dict):
    result = asyncio.run(_call_tool(tool_name, arguments))
    return result

if __name__ == "__main__":
    tools = get_tools()
    print(tools)
    result = call_tool(tools[0]["function"]["name"], {})
    print(result)