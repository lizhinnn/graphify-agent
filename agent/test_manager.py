import asyncio
from agent.manager import agent_manager

async def test_concept_learning_detection():
    """测试概念学习意图识别"""
    test_queries = [
        "解释一下神经网络的概念",
        "什么是机器学习原理",
        "如何理解深度学习",
        "帮我学习数据结构",
        "计算1+1等于多少"
    ]
    
    print("测试概念学习意图识别:")
    for query in test_queries:
        # 模拟概念学习检测逻辑
        is_concept_learning = False
        concept_keywords = ['概念', '原理', '定义', '解释', '是什么', '为什么', '如何', '学习', '理解']
        for keyword in concept_keywords:
            if keyword in query:
                is_concept_learning = True
                break
        print(f"'{query}' -> {'概念学习' if is_concept_learning else '普通查询'}")

async def test_run_stream():
    """测试 run_stream 函数"""
    test_query = "解释一下反馈控制系统的概念"
    print(f"\n测试 run_stream 函数，查询: {test_query}")
    
    try:
        async for chunk in agent_manager.run_stream(test_query):
            print(chunk.strip())
    except Exception as e:
        print(f"测试出错: {e}")

if __name__ == "__main__":
    asyncio.run(test_concept_learning_detection())
    asyncio.run(test_run_stream())
