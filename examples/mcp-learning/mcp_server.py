"""MCP 学习示例 —— 服务端

演示 FastMCP 的三大能力：
- tools     ：可被客户端调用的函数（hello / add / subtract / multiply / divide）
- prompts   ：可复用的提示模板（introduce_china_province / debug_code）
- resources ：可被读取的数据源，含静态资源与带参数的资源模板（db:// 系列）

依赖安装：
    pip install -r requirements.txt

数据库（db:// 资源使用 MySQL）：
    需要一个本地 MySQL，库名 db_mcp，账号见下方 DB_CONFIG。
    若未配置 MySQL，server 仍可正常启动，tools / prompts 不受影响，
    仅 db:// 资源会返回友好的错误信息。

启动：
    python mcp_server.py          # 默认 SSE 传输，监听 0.0.0.0:8002
    python mcp_server.py stdio    # 改用 stdio 传输
"""

import json
import os
import sys

import pymysql.cursors
from dbutils.pooled_db import PooledDB

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base

# 创建 MCP 服务器
mcp = FastMCP(
    "MCP First Server",  # 服务器名称
    debug=True,          # 启用调试模式，输出详细日志
    host="0.0.0.0",      # 监听所有网络接口，允许远程连接
    port=8002,           # 服务器监听的端口号
)

# 数据库配置（注意：MySQL 默认端口是 3306）
DB_CONFIG = {
    "database": "db_mcp",  # PyMySQL 用 'database' 而不是 'dbname'
    "user": "root",
    "password": "root",
    "host": "localhost",
    "port": 3306,  # port 是 int 类型（不是字符串）
    "cursorclass": pymysql.cursors.DictCursor,  # 自动返回字典
    "autocommit": True,
}

# 连接池采用惰性初始化：只有第一次真正用到数据库时才创建，
# 这样即使本机没有 MySQL，server 也能正常启动，tools / prompts 照常工作。
_pool = None


def get_db_connection():
    """从连接池获取连接（首次调用时才创建连接池）"""
    global _pool
    if _pool is None:
        _pool = PooledDB(
            creator=pymysql,
            mincached=1,
            maxcached=5,
            maxconnections=10,
            blocking=True,
            **DB_CONFIG,
        )
    return _pool.connection()


@mcp.resource("hello://world")
def hello_resource() -> str:
    """简单的测试资源"""
    return "Hello, World!"


# 定义资源：获取所有表名
@mcp.resource("db://tables")
def list_tables() -> str:
    """获取所有表名列表"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT table_name AS table_name
                    FROM information_schema.tables
                    WHERE table_schema = %s
                    """,
                    (DB_CONFIG["database"],),
                )
                tables = [row["table_name"] for row in cur.fetchall()]
                return json.dumps(tables, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


# 定义资源：获取表数据（带参数的资源模板）
@mcp.resource("db://tables/{table_name}/data/{limit}")
def get_table_data(table_name: str, limit: int = 100) -> str:
    """读取某张表的数据
    参数:
        table_name: 表名
        limit: 返回的最大行数
    """
    # 安全校验：防止 SQL 注入（只允许字母、数字、下划线、连字符）
    if not table_name.replace("_", "").replace("-", "").isalnum():
        return json.dumps({"error": "Invalid table name"}, ensure_ascii=False)

    # 资源模板的 URI 参数以字符串传入，这里安全地转成 int 并限制上限
    try:
        limit = min(int(limit), 1000)
    except (TypeError, ValueError):
        limit = 100

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # 表名已校验，可安全拼接；数据部分用参数占位符
                query = f"SELECT * FROM `{table_name}` LIMIT %s"
                cur.execute(query, (limit,))
                rows = cur.fetchall()
                return json.dumps(rows, default=str, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


# 定义资源：获取表结构（带参数的资源模板）
@mcp.resource("db://tables/{table_name}/schema")
def get_table_schema(table_name: str) -> str:
    """获取表结构信息
    参数:
        table_name: 表名
    """
    # 安全校验：防止 SQL 注入（只允许字母、数字、下划线、连字符）
    if not table_name.replace("_", "").replace("-", "").isalnum():
        return json.dumps({"error": "Invalid table name"}, ensure_ascii=False)

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        COLUMN_NAME AS column_name,
                        DATA_TYPE AS data_type,
                        CHARACTER_MAXIMUM_LENGTH AS character_maximum_length,
                        COLUMN_COMMENT AS column_comment
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = %s
                      AND TABLE_NAME = %s
                    ORDER BY ORDINAL_POSITION
                    """,
                    (DB_CONFIG["database"], table_name),
                )

                columns = [
                    {
                        "name": row["column_name"],
                        "type": row["data_type"],
                        "max_length": row["character_maximum_length"],
                        "comment": row["column_comment"] or "",  # 防止 None
                    }
                    for row in cur.fetchall()
                ]
                return json.dumps(columns, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


# 中国省份介绍（字符串型 prompt）
@mcp.prompt()
def introduce_china_province(province: str) -> str:
    """介绍中国省份
    参数:
        province: 省份名称
    """
    return f"""
    请介绍这个省份：{province}
    要求介绍以下内容：
    1. 历史沿革
    2. 人文地理、风俗习惯
    3. 经济发展状况
    4. 旅游建议
    """


# 调试代码提示（对话式 prompt）
@mcp.prompt()
def debug_code(code: str, error_message: str) -> list[base.Message]:
    """调试代码的对话式提示模板
    参数:
        code: 需要调试的代码
        error_message: 错误信息
    """
    return [
        base.SystemMessage("你是一位专业的代码调试助手。请仔细分析用户提供的代码和错误信息，找出问题所在并提供修复方案。"),
        base.UserMessage("我的代码有问题，请帮我修复："),
        base.UserMessage(f"```\n{code}\n```"),
        base.UserMessage(f"错误信息：\n{error_message}"),
        base.AssistantMessage("我会帮你分析这段代码和错误信息。首先让我理解问题所在..."),
    ]


@mcp.tool()
def hello(name: str) -> str:
    """向指定名称的用户发送问候

    参数:
        name: 字符串，要问候的用户名称

    返回:
        字符串，包含问候语的响应
    """
    return f"Hello {name}, Welcome to Changchun!"


@mcp.tool()
def add(a: float, b: float) -> float:
    """加法运算
    参数:
        a: 第一个数字
        b: 第二个数字
    返回:
        两数之和
    """
    return a + b


@mcp.tool()
def subtract(a: float, b: float) -> float:
    """减法运算
    参数:
        a: 第一个数字
        b: 第二个数字
    返回:
        两数之差 (a - b)
    """
    return a - b


@mcp.tool()
def multiply(a: float, b: float) -> float:
    """乘法运算
    参数:
        a: 第一个数字
        b: 第二个数字
    返回:
        两数之积
    """
    return a * b


@mcp.tool()
def divide(a: float, b: float) -> float:
    """除法运算
    参数:
        a: 被除数
        b: 除数
    返回:
        两数之商 (a / b)
    异常:
        ValueError: 当除数为零时
    """
    if b == 0:
        raise ValueError("除数不能为零")
    return a / b


if __name__ == "__main__":
    # 传输方式：默认 SSE（与 mcp_client.py 对应）；也可传入 stdio。
    # 优先级：命令行参数 > 环境变量 MCP_TRANSPORT > 默认 sse
    transport = sys.argv[1] if len(sys.argv) > 1 else os.getenv("MCP_TRANSPORT", "sse")
    mcp.run(transport)
