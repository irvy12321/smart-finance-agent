# MCP 学习示例（FastMCP server + SSE client）

一个最小、可直接跑通的 [MCP（Model Context Protocol）](https://modelcontextprotocol.io/)
入门示例，用来理解 MCP 的三大核心能力：

| 能力 | 说明 | 本示例中的体现 |
| --- | --- | --- |
| **tools** | 可被客户端调用的函数 | `hello` / `add` / `subtract` / `multiply` / `divide` |
| **prompts** | 可复用的提示模板 | `introduce_china_province`（字符串）/ `debug_code`（对话式） |
| **resources** | 可被读取的数据源（含带参数的资源模板） | `hello://world`、`db://tables`、`db://tables/{table_name}/data/{limit}`、`db://tables/{table_name}/schema` |

服务端使用 `FastMCP`，客户端通过 **SSE** 传输连接。`db://` 系列资源从一个本地
MySQL 库 `db_mcp` 读取数据。

## 目录结构

```
examples/mcp-learning/
├── mcp_server.py     # MCP 服务端（tools / prompts / resources）
├── mcp_client.py     # MCP 客户端（SSE）
├── requirements.txt  # 依赖（已固定版本，仅含示例真正需要的包）
├── seed.sql          # 初始化 db_mcp 库与 chinese_movie_ratings 表
└── README.md
```

## 1. 安装依赖（建议用独立虚拟环境）

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
```

## 2. 准备 MySQL（仅 `db://` 资源需要）

需要一个本地 MySQL，默认连接配置见 `mcp_server.py` 中的 `DB_CONFIG`
（库名 `db_mcp`、账号 `root` / `root`、端口 `3306`）。导入示例数据：

```bash
mysql -u root -p < seed.sql
```

> 若本机没有 MySQL，server 仍可正常启动，**tools / prompts 不受影响**，
> 只有 `db://` 资源会返回友好的错误信息（连接池是惰性创建的）。

## 3. 启动服务端

```bash
python mcp_server.py        # 默认 SSE，监听 0.0.0.0:8002
# 或显式指定传输方式：
python mcp_server.py stdio  # 改用 stdio
```

## 4. 运行客户端

另开一个终端：

```bash
python mcp_client.py
```

客户端会依次：列出并调用 tools、列出并读取 prompts、列出 resources 与
resource templates、读取 `db://tables` 与 `db://tables/chinese_movie_ratings/data/20`。

## 常见问题

- **客户端连不上**：确认 server 以 **SSE** 方式启动（客户端连接的是
  `http://localhost:8002/sse`），而不是 `stdio`。
- **`db://` 资源报错**：检查 MySQL 是否在运行、`db_mcp` 库与 `chinese_movie_ratings`
  表是否已通过 `seed.sql` 创建、账号密码是否与 `DB_CONFIG` 一致。
- **终端里中文显示为乱码**：这是 Windows 控制台代码页的显示问题，数据本身是
  正确的 UTF-8（`json.dumps(..., ensure_ascii=False)`）。可执行 `chcp 65001`
  切换到 UTF-8 代码页。
