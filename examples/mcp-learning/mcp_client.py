"""MCP 学习示例 —— 客户端（SSE 传输）

依次演示如何通过 MCP 客户端：
- 列出 / 调用 tools
- 列出 / 读取 prompts
- 列出 resources 与 resource templates，并读取资源

运行前请先启动服务端（默认 SSE，监听 8002）：
    python mcp_server.py

然后运行本客户端：
    python mcp_client.py
"""

import asyncio
import logging
from contextlib import AsyncExitStack
from typing import Any, Optional

import mcp.types as types
from mcp import ClientSession
from mcp.client.sse import sse_client
from pydantic import AnyUrl

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class MCPClient:
    def __init__(self):
        self._session_context = None
        self._streams_context = None
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

    async def connect_to_sse_server(self, server_url: str):
        """通过 SSE 传输方式连接到 MCP 服务端

        - 用 sse_client 创建与指定 URL 的 SSE 连接，拿到通信流
        - 用这些流创建 ClientSession
        - 初始化会话，完成与服务端的能力协商
        """
        self._streams_context = sse_client(url=server_url)
        streams = await self._streams_context.__aenter__()

        self._session_context = ClientSession(*streams)
        self.session = await self._session_context.__aenter__()

        # 初始化
        await self.session.initialize()

    async def cleanup(self):
        """关闭会话上下文与连接流，正确释放资源"""
        if self._session_context:
            await self._session_context.__aexit__(None, None, None)
        if self._streams_context:
            await self._streams_context.__aexit__(None, None, None)

    async def list_tools(self):
        """列出全部工具"""
        try:
            response = await self.session.list_tools()
            return response.tools
        except Exception as e:
            error_msg = f"Error listing tools: {str(e)}"
            logging.error(error_msg)
            return error_msg

    async def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """调用工具"""
        try:
            return await self.session.call_tool(tool_name, arguments)
        except Exception as e:
            error_msg = f"Error executing tool: {str(e)}"
            logging.error(error_msg)
            return error_msg

    async def list_prompts(self):
        """列出全部提示模板"""
        try:
            return await self.session.list_prompts()
        except Exception as e:
            error_msg = f"Error listing prompts: {str(e)}"
            logging.error(error_msg)
            return error_msg

    async def get_prompt(self, name: str, arguments: dict[str, str] | None = None):
        """读取提示模板内容"""
        try:
            return await self.session.get_prompt(name=name, arguments=arguments)
        except Exception as e:
            error_msg = f"Error getting prompt: {str(e)}"
            logging.error(error_msg)
            return error_msg

    async def list_resources(self) -> types.ListResourcesResult:
        """列出全部资源"""
        try:
            return await self.session.list_resources()
        except Exception as e:
            error_msg = f"Error listing resources: {str(e)}"
            logging.error(error_msg)
            return error_msg

    async def list_resource_templates(self) -> types.ListResourceTemplatesResult:
        """列出全部带参数的资源模板"""
        try:
            return await self.session.list_resource_templates()
        except Exception as e:
            error_msg = f"Error listing resource templates: {str(e)}"
            logging.error(error_msg)
            return error_msg

    async def read_resource(self, uri: AnyUrl) -> types.ReadResourceResult:
        """读取资源"""
        try:
            return await self.session.read_resource(uri=uri)
        except Exception as e:
            error_msg = f"Error reading resource: {str(e)}"
            logging.error(error_msg)
            return error_msg


async def main():
    client = MCPClient()
    try:
        server_url = "http://localhost:8002/sse"
        await client.connect_to_sse_server(server_url=server_url)

        # 列出全部 tools
        tools = await client.list_tools()
        print("------------列出全部 tools")
        for tool in tools:
            print(f"---- 工具名称：{tool.name}, 描述：{tool.description}")
            print(f"输入参数: {tool.inputSchema}")

        # 调用 add 工具
        result = await client.execute_tool("add", {"a": 2, "b": 3})
        print(f"工具执行结果（add 2+3）：{result}")

        # 列出全部 prompts
        prompts_list = await client.list_prompts()
        print("------------列出全部 prompts")
        for prompt in prompts_list.prompts:
            print(
                f"---- prompt 名称: {prompt.name}, 描述：{prompt.description}, "
                f"参数：{prompt.arguments}"
            )

        # 获取 "介绍中国省份" prompt 内容
        province_name = "广东省"
        prompt_result = await client.get_prompt(
            name="introduce_china_province", arguments={"province": province_name}
        )
        prompt_content = prompt_result.messages[0].content.text
        print(f"-------介绍{province_name}的 prompt：{prompt_content}")

        # 列出全部 resources
        resources_list = await client.list_resources()
        print("---- 列出全部 resources")
        print(resources_list.resources)

        # 列出全部 resource templates
        resource_templates_list = await client.list_resource_templates()
        print("---- 列出全部 resource templates")
        print(resource_templates_list.resourceTemplates)

        # 获取全部数据表的表名
        uri = AnyUrl("db://tables")
        table_names = await client.read_resource(uri)
        print("---- 全部数据表：")
        print(table_names.contents[0].text)

        # 读取某个数据表的数据
        uri = AnyUrl("db://tables/chinese_movie_ratings/data/20")
        resource_datas = await client.read_resource(uri)
        print("chinese_movie_ratings 表数据：")
        print(resource_datas.contents[0].text)
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
