#!/usr/bin/env python3
"""
Step 2 验证脚本: 测试 RAG 模块
"""
import os
import sys

# 添加backend目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv()


def test_embedder():
    """测试 Embedding 模块"""
    print("=" * 60)
    print("测试 Embedding 模块")
    print("=" * 60)

    try:
        from app.rag.embed import HashEmbedder, create_embedder

        # 测试 HashEmbedder (开发模式)
        print("\n1. 测试 HashEmbedder (开发模式)...")
        hash_embedder = HashEmbedder(dimension=384)

        # 测试单文本嵌入
        text = "Tesla stock price analysis"
        vec = hash_embedder.embed_text(text)
        print(f"   [OK] 单文本嵌入: dim={len(vec)}, norm={sum(v*v for v in vec)**0.5:.3f}")

        # 测试批量嵌入
        texts = ["Apple earnings", "Google revenue", "Microsoft cloud"]
        vecs = hash_embedder.embed_batch(texts)
        print(f"   [OK] 批量嵌入: shape={vecs.shape}")

        # 测试 create_embedder 工厂函数
        print("\n2. 测试 create_embedder 工厂函数...")
        embedder = create_embedder()
        print(f"   [OK] 创建 {type(embedder).__name__}: dim={embedder.dim}")

        print("\n" + "=" * 60)
        print("Embedding 模块测试通过!")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n[FAIL] Embedding 模块测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_vector_store():
    """测试 VectorStore 模块"""
    print("\n" + "=" * 60)
    print("测试 VectorStore 模块")
    print("=" * 60)

    try:
        import numpy as np

        from app.rag.vector_store import VectorStore

        # 创建 VectorStore
        print("\n1. 创建 VectorStore...")
        dim = 384
        store = VectorStore(dim=dim)
        print(f"   [OK] VectorStore 创建成功: dim={dim}")

        # 测试添加向量
        print("\n2. 测试添加向量...")
        texts = ["Tesla stock analysis", "Apple earnings report", "Google revenue growth"]
        embeddings = np.random.randn(len(texts), dim).astype(np.float32)
        metadata = [{"source": f"doc_{i}"} for i in range(len(texts))]

        store.add(embeddings, texts, metadata)
        print(f"   [OK] 添加 {len(texts)} 个向量, 总数: {store.size}")

        # 测试搜索
        print("\n3. 测试搜索...")
        query_vec = np.random.randn(dim).astype(np.float32)
        results = store.search(query_vec, top_k=2)
        print(f"   [OK] 搜索结果: {len(results)} 个")
        for i, r in enumerate(results):
            print(f"     {i+1}. {r['text'][:30]}... (score: {r['score']:.3f})")

        # 测试保存和加载
        print("\n4. 测试保存和加载...")
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            store.save(tmpdir)
            print(f"   [OK] 保存到: {tmpdir}")

            # 创建新的 store 并加载
            new_store = VectorStore(dim=dim)
            loaded = new_store.load(tmpdir)
            print(f"   [OK] 加载成功: {loaded}, 向量数: {new_store.size}")

        print("\n" + "=" * 60)
        print("VectorStore 模块测试通过!")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n[FAIL] VectorStore 模块测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_chunker():
    """测试文本分块模块"""
    print("\n" + "=" * 60)
    print("测试文本分块模块")
    print("=" * 60)

    try:
        from app.rag.chunker import chunk_text

        # 测试短文本
        print("\n1. 测试短文本分块...")
        short_text = "This is a short text."
        chunks = chunk_text(short_text, chunk_size=100)
        print(f"   [OK] 短文本: {len(chunks)} 个块")

        # 测试长文本
        print("\n2. 测试长文本分块...")
        long_text = """
        Tesla Inc. (TSLA) reported strong Q4 2024 earnings.
        Revenue increased by 25% year-over-year.
        The company delivered 500,000 vehicles in Q4.

        Apple Inc. (AAPL) also reported positive results.
        iPhone sales grew by 10% in the holiday quarter.
        Services revenue reached an all-time high.

        Google's parent company Alphabet showed resilience.
        Cloud revenue grew by 30% year-over-year.
        YouTube advertising revenue increased significantly.
        """
        chunks = chunk_text(long_text, chunk_size=200, overlap=50)
        print(f"   [OK] 长文本: {len(chunks)} 个块")
        for i, chunk in enumerate(chunks[:3]):
            print(f"     块 {i+1}: {chunk[:50]}...")

        print("\n" + "=" * 60)
        print("文本分块模块测试通过!")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n[FAIL] 文本分块模块测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_retriever():
    """测试 Retriever 模块"""
    print("\n" + "=" * 60)
    print("测试 Retriever 模块")
    print("=" * 60)

    try:
        from app.rag.retriever import Retriever

        # 创建 Retriever
        print("\n1. 创建 Retriever...")
        retriever = Retriever()
        print(f"   [OK] Retriever 创建成功: dim={retriever.embedder.dim}")

        # 测试添加文档
        print("\n2. 测试添加文档...")
        documents = [
            "Tesla Inc. reported strong Q4 2024 earnings with revenue increasing by 25%.",
            "Apple Inc. showed positive results with iPhone sales growing by 10%.",
            "Google's parent company Alphabet demonstrated resilience with cloud revenue growth.",
            "Microsoft's Azure cloud platform continued to gain market share.",
            "Amazon's AWS remained the leading cloud service provider.",
        ]

        for i, doc in enumerate(documents):
            retriever.add_document(doc, {"source": f"doc_{i}", "category": "tech"})
        print(f"   [OK] 添加 {len(documents)} 个文档, 总块数: {retriever.doc_count}")

        # 测试检索
        print("\n3. 测试检索...")
        queries = [
            "Tesla earnings report",
            "cloud revenue growth",
            "iPhone sales",
        ]

        for query in queries:
            results = retriever.retrieve(query, top_k=2)
            print(f"\n   查询: '{query}'")
            for i, r in enumerate(results):
                print(f"     {i+1}. {r['text'][:50]}... (score: {r['score']:.3f})")

        print("\n" + "=" * 60)
        print("Retriever 模块测试通过!")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n[FAIL] Retriever 模块测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_memory():
    """测试 ConversationMemory 模块"""
    print("\n" + "=" * 60)
    print("测试 ConversationMemory 模块")
    print("=" * 60)

    try:
        from app.rag.memory import ConversationMemory

        # 创建 ConversationMemory
        print("\n1. 创建 ConversationMemory...")
        memory = ConversationMemory(max_short_term=5)
        print("   [OK] ConversationMemory 创建成功")

        # 测试添加消息
        print("\n2. 测试添加消息...")
        memory.add_user_message("What is the current stock price of Tesla?")
        memory.add_assistant_message("Tesla (TSLA) is currently trading at $250.")
        memory.add_user_message("What about Apple?")
        memory.add_assistant_message("Apple (AAPL) is currently trading at $180.")
        print(f"   [OK] 添加 4 条消息, 轮次: {memory.turn_count}")

        # 测试短期记忆上下文
        print("\n3. 测试短期记忆上下文...")
        context = memory.get_short_term_context(max_tokens=500)
        print(f"   [OK] 上下文长度: {len(context)} 字符")
        print(f"   内容预览: {context[:100]}...")

        # 测试长期记忆归档
        print("\n4. 测试长期记忆归档...")
        memory.archive_to_long_term(
            "Tesla reported strong Q4 2024 earnings with revenue increasing by 25%.",
            {"source": "earnings_report"}
        )
        print("   [OK] 归档成功")

        # 测试混合上下文
        print("\n5. 测试混合上下文...")
        combined = memory.get_combined_context("Tesla earnings")
        print(f"   [OK] 混合上下文长度: {len(combined)} 字符")

        print("\n" + "=" * 60)
        print("ConversationMemory 模块测试通过!")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n[FAIL] ConversationMemory 模块测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rag_tool():
    """测试 RAG 工具"""
    print("\n" + "=" * 60)
    print("测试 RAG 工具")
    print("=" * 60)

    try:
        import asyncio

        from app.tools.rag_tool import RAGTool

        # 创建 RAG 工具
        print("\n1. 创建 RAG 工具...")
        rag_tool = RAGTool()
        print(f"   [OK] RAG 工具创建成功: {rag_tool.name}")

        # 测试添加文档
        print("\n2. 测试添加文档...")
        documents = [
            "Tesla Inc. reported strong Q4 2024 earnings.",
            "Apple Inc. showed positive results.",
            "Google's cloud revenue grew significantly.",
        ]

        for doc in documents:
            rag_tool.add_document(doc)
        print(f"   [OK] 添加 {len(documents)} 个文档")

        # 测试执行查询
        print("\n3. 测试执行查询...")
        async def test_query():
            result = await rag_tool.execute(query="Tesla earnings", top_k=2)
            return result

        result = asyncio.run(test_query())
        print(f"   [OK] 查询结果: success={result.success}")
        if result.success:
            data = result.data
            print(f"   结果数: {len(data.get('results', []))}")

        print("\n" + "=" * 60)
        print("RAG 工具测试通过!")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n[FAIL] RAG 工具测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Step 2 验证脚本 - RAG 模块")
    print("=" * 60)

    results = []

    # 运行所有测试
    results.append(("Embedder", test_embedder()))
    results.append(("VectorStore", test_vector_store()))
    results.append(("Chunker", test_chunker()))
    results.append(("Retriever", test_retriever()))
    results.append(("Memory", test_memory()))
    results.append(("RAG Tool", test_rag_tool()))

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    for test_name, result in results:
        status = "[OK] 通过" if result else "[FAIL] 失败"
        print(f"{test_name}: {status}")

    all_passed = all(r for _, r in results)
    print(f"\n总体结果: {'全部通过' if all_passed else '存在失败'}")

    if all_passed:
        print("\n恭喜! Step 2 RAG 模块验证成功!")
        print("RAG 模块已准备好集成到 Orchestrator 中")
    else:
        print("\n请修复失败的测试后再继续")
