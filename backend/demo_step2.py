#!/usr/bin/env python3
"""
Step 2 Demo: RAG 模块实际使用演示
"""
import asyncio
import sys
import os

# 添加backend目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app.rag.retriever import Retriever
from app.rag.memory import ConversationMemory
from app.tools.rag_tool import RAGTool
from app.utils.logger import get_logger

logger = get_logger("demo_step2")


async def demo_retriever():
    """演示 Retriever 的使用"""
    print("=" * 60)
    print("Demo: Retriever 使用演示")
    print("=" * 60)
    
    # 创建 Retriever
    print("\n1. 创建 Retriever...")
    retriever = Retriever()
    
    # 添加金融文档
    print("\n2. 添加金融文档...")
    documents = [
        {
            "text": "Tesla Inc. (TSLA) reported strong Q4 2024 earnings. Revenue increased by 25% year-over-year to $25.2 billion. The company delivered 500,000 vehicles in Q4, beating analyst expectations.",
            "metadata": {"source": "Tesla Earnings Report", "date": "2024-01-25"}
        },
        {
            "text": "Apple Inc. (AAPL) showed positive results in Q4 2024. iPhone sales grew by 10% in the holiday quarter. Services revenue reached an all-time high of $22 billion.",
            "metadata": {"source": "Apple Earnings Report", "date": "2024-01-24"}
        },
        {
            "text": "Google's parent company Alphabet demonstrated resilience in Q4 2024. Cloud revenue grew by 30% year-over-year. YouTube advertising revenue increased significantly.",
            "metadata": {"source": "Alphabet Earnings Report", "date": "2024-01-23"}
        },
        {
            "text": "Microsoft's Azure cloud platform continued to gain market share in Q4 2024. Revenue grew by 28% year-over-year. AI services contributed significantly to growth.",
            "metadata": {"source": "Microsoft Earnings Report", "date": "2024-01-22"}
        },
        {
            "text": "Amazon's AWS remained the leading cloud service provider in Q4 2024. Revenue grew by 20% year-over-year. Operating margins improved significantly.",
            "metadata": {"source": "Amazon Earnings Report", "date": "2024-01-21"}
        },
    ]
    
    for doc in documents:
        retriever.add_document(doc["text"], doc["metadata"])
    
    print(f"   [OK] 添加 {len(documents)} 个文档, 总块数: {retriever.doc_count}")
    
    # 测试查询
    print("\n3. 测试查询...")
    queries = [
        "What was Tesla's revenue growth in Q4 2024?",
        "How did cloud services perform across tech companies?",
        "Which company had the best iPhone sales?",
    ]
    
    for query in queries:
        print(f"\n   查询: '{query}'")
        results = retriever.retrieve(query, top_k=2)
        for i, r in enumerate(results):
            print(f"     {i+1}. {r['text'][:80]}...")
            print(f"        分数: {r['score']:.3f}, 来源: {r['metadata'].get('source', 'unknown')}")
    
    return retriever


async def demo_memory():
    """演示 ConversationMemory 的使用"""
    print("\n" + "=" * 60)
    print("Demo: ConversationMemory 使用演示")
    print("=" * 60)
    
    # 创建 ConversationMemory
    print("\n1. 创建 ConversationMemory...")
    memory = ConversationMemory(max_short_term=5)
    
    # 模拟对话
    print("\n2. 模拟对话...")
    conversations = [
        ("user", "What is the current stock price of Tesla?"),
        ("assistant", "Tesla (TSLA) is currently trading at $250 per share."),
        ("user", "What about Apple?"),
        ("assistant", "Apple (AAPL) is currently trading at $180 per share."),
        ("user", "Which tech company had the best Q4 2024 earnings?"),
        ("assistant", "Based on the earnings reports, Tesla had the strongest Q4 2024 with 25% revenue growth."),
    ]
    
    for role, content in conversations:
        if role == "user":
            memory.add_user_message(content)
        else:
            memory.add_assistant_message(content)
        print(f"   [{role}] {content[:50]}...")
    
    # 归档重要信息到长期记忆
    print("\n3. 归档重要信息到长期记忆...")
    memory.archive_to_long_term(
        "Tesla reported strong Q4 2024 earnings with revenue increasing by 25% to $25.2 billion.",
        {"source": "earnings_report", "company": "Tesla"}
    )
    memory.archive_to_long_term(
        "Apple's iPhone sales grew by 10% in the holiday quarter of 2024.",
        {"source": "earnings_report", "company": "Apple"}
    )
    
    # 测试混合上下文
    print("\n4. 测试混合上下文...")
    query = "Tell me about Tesla's performance"
    context = memory.get_combined_context(query)
    print(f"   查询: '{query}'")
    print(f"   上下文长度: {len(context)} 字符")
    print(f"   内容预览:")
    for line in context.split("\n")[:5]:
        print(f"     {line[:80]}...")
    
    return memory


async def demo_rag_tool():
    """演示 RAG 工具的使用"""
    print("\n" + "=" * 60)
    print("Demo: RAG 工具使用演示")
    print("=" * 60)
    
    # 创建 RAG 工具
    print("\n1. 创建 RAG 工具...")
    rag_tool = RAGTool()
    
    # 添加文档
    print("\n2. 添加文档...")
    documents = [
        "Tesla Inc. reported strong Q4 2024 earnings with revenue increasing by 25%.",
        "Apple Inc. showed positive results with iPhone sales growing by 10%.",
        "Google's cloud revenue grew significantly by 30% year-over-year.",
        "Microsoft's Azure platform continued to gain market share.",
        "Amazon's AWS remained the leading cloud service provider.",
    ]
    
    for doc in documents:
        rag_tool.add_document(doc)
    
    print(f"   [OK] 添加 {len(documents)} 个文档")
    
    # 测试查询
    print("\n3. 测试查询...")
    queries = [
        "Tesla earnings",
        "cloud revenue growth",
        "iPhone sales",
    ]
    
    for query in queries:
        print(f"\n   查询: '{query}'")
        result = await rag_tool.execute(query=query, top_k=2)
        if result.success:
            data = result.data
            results = data.get("results", [])
            for i, r in enumerate(results):
                print(f"     {i+1}. {r['text'][:60]}... (score: {r['score']:.3f})")
        else:
            print(f"     错误: {result.error}")
    
    return rag_tool


async def demo_integrated_rag():
    """演示集成 RAG 的完整流程"""
    print("\n" + "=" * 60)
    print("Demo: 集成 RAG 的完整流程")
    print("=" * 60)
    
    # 创建组件
    print("\n1. 创建组件...")
    retriever = Retriever()
    memory = ConversationMemory(max_short_term=5, retriever=retriever)
    
    # 添加知识库
    print("\n2. 添加知识库...")
    knowledge_base = [
        "Tesla Inc. (TSLA) is an electric vehicle and clean energy company founded in 2003.",
        "Tesla's Q4 2024 revenue was $25.2 billion, a 25% increase year-over-year.",
        "Tesla delivered 500,000 vehicles in Q4 2024, beating analyst expectations.",
        "Apple Inc. (AAPL) is a technology company that designs and sells consumer electronics.",
        "Apple's Q4 2024 iPhone sales grew by 10% in the holiday quarter.",
        "Apple's Services revenue reached an all-time high of $22 billion in Q4 2024.",
    ]
    
    for doc in knowledge_base:
        retriever.add_document(doc)
    
    print(f"   [OK] 添加 {len(knowledge_base)} 条知识")
    
    # 模拟对话流程
    print("\n3. 模拟对话流程...")
    
    # 用户提问
    user_query = "Tell me about Tesla's Q4 2024 performance"
    print(f"\n   用户: {user_query}")
    
    # 添加到短期记忆
    memory.add_user_message(user_query)
    
    # 从长期记忆检索相关信息
    print("\n   检索相关信息...")
    relevant_docs = retriever.retrieve(user_query, top_k=3)
    print(f"   找到 {len(relevant_docs)} 条相关文档:")
    for i, doc in enumerate(relevant_docs):
        print(f"     {i+1}. {doc['text'][:60]}... (score: {doc['score']:.3f})")
    
    # 生成回答（模拟）
    answer = "Based on the latest earnings report, Tesla had a strong Q4 2024. Revenue increased by 25% to $25.2 billion, and the company delivered 500,000 vehicles, beating analyst expectations."
    print(f"\n   助手: {answer}")
    
    # 添加助手回复到短期记忆
    memory.add_assistant_message(answer, {"source": "rag_enhanced"})
    
    # 归档到长期记忆
    memory.archive_to_long_term(
        f"Q: {user_query}\nA: {answer}",
        {"source": "conversation", "topic": "Tesla earnings"}
    )
    
    # 测试后续查询
    print("\n4. 测试后续查询...")
    follow_up_query = "What about Apple's performance?"
    print(f"\n   用户: {follow_up_query}")
    
    # 获取混合上下文
    context = memory.get_combined_context(follow_up_query)
    print(f"   上下文长度: {len(context)} 字符")
    print(f"   上下文预览:")
    for line in context.split("\n")[:5]:
        print(f"     {line[:80]}...")
    
    print("\n" + "=" * 60)
    print("集成 RAG 流程演示完成!")
    print("=" * 60)


async def main():
    """主演示函数"""
    print("Step 2 Demo: RAG 模块实际使用演示")
    print("=" * 60)
    
    # 演示 Retriever
    await demo_retriever()
    
    # 演示 ConversationMemory
    await demo_memory()
    
    # 演示 RAG 工具
    await demo_rag_tool()
    
    # 演示集成 RAG 流程
    await demo_integrated_rag()
    
    print("\n" + "=" * 60)
    print("Step 2 Demo 完成!")
    print("=" * 60)
    print("\nRAG 模块功能:")
    print("  - Embedding: 支持 dev (HashEmbedder) 和 prod (BGEEmbedder) 模式")
    print("  - VectorStore: FAISS 向量存储，支持持久化")
    print("  - Chunker: 智能文本分块")
    print("  - Retriever: 语义检索")
    print("  - Memory: 短期记忆 + 长期记忆")
    print("  - RAG Tool: 集成到工具系统")


if __name__ == "__main__":
    asyncio.run(main())