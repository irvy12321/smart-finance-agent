# Step 2: RAG 模块

## 概述

Step 2 完成了 RAG（Retrieval-Augmented Generation）模块的搭建，支持：

- **Embedding**: 文本向量化（支持 dev/prod 模式）
- **VectorStore**: FAISS 向量存储，支持持久化
- **Chunker**: 智能文本分块
- **Retriever**: 语义检索
- **Memory**: 对话记忆管理（短期 + 鷟期）
- **RAG Tool**: 集成到工具系统

## 架构说明

```
┌─────────────────────────────────────────────────────────┐
│                    RAG 模块架构                          │
│                                                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│  │   Loader    │ →  │   Chunker   │ →  │  Embedder   │ │
│  │  (文本加载)  │    │  (文本分块)  │    │  (向量嵌入)  │ │
│  └─────────────┘    └─────────────┘    └─────────────┘ │
│                                                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│  │  Retriever  │ ←  │ VectorStore │ ←  │   Memory    │ │
│  │  (语义检索)  │    │ (FAISS存储)  │    │ (对话记忆)  │ │
│  └─────────────┘    └─────────────┘    └─────────────┘ │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │              RAG Tool (工具接口)                  │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## 文件结构

```
backend/
├── app/
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── embed.py          # Embedding 模块
│   │   ├── vector_store.py   # FAISS 向量存储
│   │   ├── chunker.py        # 文本分块
│   │   ├── retriever.py      # 语义检索器
│   │   ├── loader.py         # 文本加载器
│   │   └── memory.py         # 对话记忆管理
│   ├── tools/
│   │   └── rag_tool.py       # RAG 工具
│   └── infrastructure/
│       └── config_rag.yaml   # RAG 配置文件
├── verify_step2.py           # 验证脚本
├── demo_step2.py             # 演示脚本
└── STEP2_README.md           # 本文档
```

## 快速开始

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

主要依赖：
- `faiss-cpu`: FAISS 向量数据库
- `sentence-transformers`: 生产模式 Embedding
- `numpy`: 数值计算

### 2. 配置

编辑 `app/infrastructure/config_rag.yaml`：

```yaml
# RAG 配置
chunk_size: 500
chunk_overlap: 50
embedding_dim: 384
top_k: 5

# Embedding 配置
embedding:
  mode: "dev"  # "dev" 或 "prod"
  model_name: "BAAI/bge-m3"
  dim: 1024
  batch_size: 32
  device: "cpu"
```

### 3. 验证模块

```bash
python verify_step2.py
```

### 4. 运行演示

```bash
python demo_step2.py
```

## 核心类说明

### 1. Embedder

#### HashEmbedder (开发模式)

```python
from app.rag.embed import HashEmbedder

embedder = HashEmbedder(dimension=384)

# 单文本嵌入
vec = embedder.embed_text("Tesla stock analysis")

# 批量嵌入
texts = ["Apple earnings", "Google revenue"]
vecs = embedder.embed_batch(texts)
```

#### BGEEmbedder (生产模式)

```python
from app.rag.embed import BGEEmbedder

embedder = BGEEmbedder(model_name="BAAI/bge-m3", device="cpu")

# 首次调用会加载模型
vec = embedder.embed_text("Tesla stock analysis")
```

#### 工厂函数

```python
from app.rag.embed import create_embedder

# 根据配置自动选择
embedder = create_embedder()
```

### 2. VectorStore

```python
from app.rag.vector_store import VectorStore
import numpy as np

# 创建 VectorStore
store = VectorStore(dim=384)

# 添加向量
texts = ["Tesla earnings", "Apple revenue"]
embeddings = np.random.randn(2, 384).astype(np.float32)
metadata = [{"source": "doc_1"}, {"source": "doc_2"}]
store.add(embeddings, texts, metadata)

# 搜索
query_vec = np.random.randn(384).astype(np.float32)
results = store.search(query_vec, top_k=2)

# 持久化
store.save("./data/vector_store")

# 加载
new_store = VectorStore(dim=384)
new_store.load("./data/vector_store")
```

### 3. Chunker

```python
from app.rag.chunker import chunk_text

# 文本分块
text = "Long text..."
chunks = chunk_text(text, chunk_size=500, overlap=50)
```

### 4. Retriever

```python
from app.rag.retriever import Retriever

# 创建 Retriever
retriever = Retriever()

# 添加文档
retriever.add_document("Tesla reported strong Q4 2024 earnings.", {"source": "earnings"})

# 检索
results = retriever.retrieve("Tesla earnings", top_k=3)

# 批量添加
texts = ["doc1", "doc2", "doc3"]
metadata = [{"source": f"doc_{i}"} for i in range(3)]
retriever.add_texts(texts, metadata)
```

### 5. ConversationMemory

```python
from app.rag.memory import ConversationMemory

# 创建记忆
memory = ConversationMemory(max_short_term=10)

# 添加对话
memory.add_user_message("What about Tesla?")
memory.add_assistant_message("Tesla had strong Q4 2024 earnings.")

# 归档到长期记忆
memory.archive_to_long_term("Tesla Q4 2024 revenue: $25.2B", {"source": "earnings"})

# 获取短期记忆上下文
short_ctx = memory.get_short_term_context(max_tokens=2000)

# 获取长期记忆检索结果
long_results = memory.retrieve_long_term("Tesla earnings", top_k=3)

# 获取混合上下文
combined = memory.get_combined_context("Tesla performance")
```

### 6. RAG Tool

```python
from app.tools.rag_tool import RAGTool
import asyncio

# 创建工具
rag_tool = RAGTool()

# 添加文档
rag_tool.add_document("Tesla reported strong Q4 2024 earnings.")

# 执行查询
async def query():
    result = await rag_tool.execute(query="Tesla earnings", top_k=3)
    return result

result = asyncio.run(query())
```

## 集成到 Orchestrator

RAG 模块已经集成到 Orchestrator 中：

### 1. 工具注册

在 `app/core/orchestrator.py` 中：

```python
def _register_tools(self):
    tools = [CrawlerTool(), NewsTool(), RAGTool()]
    for tool in tools:
        self.registry.register(tool)
```

### 2. 记忆管理

```python
class Orchestrator:
    def __init__(self):
        # ...
        self.memory = ConversationMemory()
    
    async def run(self, query: str):
        # 添加用户消息
        self.memory.add_user_message(query)
        
        # 获取上下文
        context = self.memory.get_combined_context(query)
        
        # 归档到长期记忆
        self.memory.archive_to_long_term(report.summary, {"source": "report"})
```

### 3. Planner 使用

Planner 可以在计划中使用 `rag_retrieve` 工具：

```json
{
  "task_id": "task_1",
  "tool_name": "rag_retrieve",
  "params": {"query": "Tesla financial analysis"},
  "description": "Retrieve related local documents"
}
```

## 配置说明

### Embedding 配置

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `mode` | 模式: "dev" 或 "prod" | "dev" |
| `model_name` | 模型名称 | "BAAI/bge-m3" |
| `dim` | 向量维度 | 1024 |
| `batch_size` | 批处理大小 | 32 |
| `device` | 设备: "cpu" 或 "cuda" | "cpu" |

### RAG 配置

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `chunk_size` | 文本块大小 | 500 |
| `chunk_overlap` | 重叠大小 | 50 |
| `embedding_dim` | Embedding 维度 | 384 |
| `top_k` | 返回结果数 | 5 |

## 性能优化

### 1. 批量处理

```python
# 批量添加文档
texts = ["doc1", "doc2", "doc3"]
metadata = [{"source": f"doc_{i}"} for i in range(3)]
retriever.add_texts(texts, metadata)
```

### 2. 持久化

```python
# 保存索引
store.save("./data/vector_store")

# 加载索引（避免重复构建）
store.load("./data/vector_store")
```

### 3. 生产模式

```yaml
embedding:
  mode: "prod"
  model_name: "BAAI/bge-m3"
  device: "cuda"  # 使用 GPU
```

## 故障排除

### 1. FAISS 安装问题

```bash
# CPU 版本
pip install faiss-cpu

# GPU 版本（需要 CUDA）
pip install faiss-gpu
```

### 2. sentence-transformers 安装问题

```bash
pip install sentence-transformers
```

### 3. 内存不足

- 减小 `batch_size`
- 使用 `HashEmbedder` 进行开发
- 分批添加文档

## 下一步

Step 2 完成后，可以继续：

- **Step 3**: 搭建工具（股票价格查询、财务报告分析、新闻摘要）
- **Step 4**: 封装完整的 API 接口
- **Step 5**: 前端 Chat 页面开发

## 参考资料

- [FAISS 文档](https://faiss.ai/)
- [sentence-transformers 文档](https://www.sbert.net/)
- [BAAI/bge-m3 模型](https://huggingface.co/BAAI/bge-m3)