"""测试小米MiMo官方API调用"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from infrastructure.llm_client import LLMClient
from infrastructure.config import get_llm_config


async def test_mimo():
    """测试MiMo模型的基本调用"""
    config = get_llm_config()
    print("=" * 50)
    print("小米MiMo官方API测试")
    print("=" * 50)
    print("模型:", config.model)
    print("API地址:", config.api_base)
    print("API密钥:", config.api_key[:10] + "..." if config.api_key else "未配置")

    if not config.api_key or config.api_key == "your-mimo-api-key-here":
        print("\n错误: 请在 .env 文件中配置 MIMO_API_KEY")
        return

    print("\n正在测试MiMo模型调用...")
    llm = LLMClient(config)

    try:
        response = await llm.complete(
            prompt="你好，请用一句话介绍小米MiMo模型的特点。",
            system="你是小米开发的AI助手MiMo。",
            temperature=0.3,
            max_tokens=200,
        )
        print("\nMiMo回复:")
        print("-" * 50)
        print(response)
        print("-" * 50)
        print("\n测试成功!")
    except Exception as e:
        print("\n测试失败:", e)
        print("请检查:")
        print("1. MIMO_API_KEY 是否正确")
        print("2. 网络连接是否正常")


if __name__ == "__main__":
    asyncio.run(test_mimo())
