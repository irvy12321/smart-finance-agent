import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()
from core.orchestrator import Orchestrator

orch = Orchestrator()
print("System initialized successfully")
print(f"Tools registered: {len(orch.registry.list_tools())}")
for t in orch.registry.list_tools():
    print(f"  - {t['name']}: {t['description'][:60]}")
print("系统已就绪! 在 .env 中配置 SILICONFLOW_API_KEY 即可调用MiMo模型。")
