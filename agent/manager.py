from openai import OpenAI
from server.config import settings
from agent.prompt_templates import SYSTEM_PROMPT
from agent.tools import TOOLS
import re
import json


class AgentManager:
    def __init__(self):
        self.tools = TOOLS
        # 创建工具映射
        self.tools_map = {tool.name: tool for tool in self.tools}
        # 初始化 OpenAI 客户端
        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_API_BASE
        )
        # 存储当前图表数据
        self.current_plot_data = None

    def add_tool(self, tool):
        self.tools.append(tool)
        self.tools_map[tool.name] = tool

    async def run_stream(self, query):
        """实现 ReAct 模式的核心调度逻辑，返回异步生成器"""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query}
        ]

        max_iterations = 5
        for i in range(max_iterations):
            # 添加心跳日志
            print(f"\n--- [Step {i+1}] 正在调用 LLM ---")

            # 调用 LLM，temperature 设为 0 确保推理稳定性，设置 100 秒超时
            response = self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages,
                temperature=0,
                timeout=100,
                stream=True
            )

            # 收集完整响应
            ai_response = ""
            is_final_answer = False
            final_answer_buffer = ""

            for chunk in response:
                if chunk.choices[0].delta.content:
                    chunk_content = chunk.choices[0].delta.content
                    ai_response += chunk_content

                    # 检测是否进入 Final Answer 阶段
                    if "Final Answer:" in ai_response and not is_final_answer:
                        is_final_answer = True
                        # 提取 Final Answer: 之后的内容
                        final_answer_match = re.search(r"Final Answer:\s*(.+)", ai_response, re.DOTALL)
                        if final_answer_match:
                            final_answer_buffer = final_answer_match.group(1)
                        else:
                            final_answer_buffer = ""
                    elif is_final_answer:
                        # 继续收集 Final Answer 内容
                        final_answer_match = re.search(r"Final Answer:\s*(.+)", ai_response, re.DOTALL)
                        if final_answer_match:
                            final_answer_buffer = final_answer_match.group(1)

                    # 实时输出思考过程（不在 Final Answer 阶段时）
                    if not is_final_answer:
                        yield f"data: {json.dumps({'type': 'thought', 'content': chunk_content})}\n\n"
                    else:
                        # Final Answer 阶段，逐token输出
                        yield f"data: {json.dumps({'type': 'final_answer', 'content': final_answer_buffer})}\n\n"

            # Final Answer 完成后，直接结束
            if is_final_answer and "Final Answer:" in ai_response:
                # 添加 AI 回复日志
                print(f"--- [Step {i+1}] AI 回复内容：\n{ai_response}\n---")
                messages.append({"role": "assistant", "content": ai_response})
                return

            # 添加 AI 回复日志
            print(f"--- [Step {i+1}] AI 回复内容：\n{ai_response}\n---")
            messages.append({"role": "assistant", "content": ai_response})

            # 先解析 Action，使用 re.DOTALL 兼容换行
            action_match = re.search(r"Action:\s*(\w+)\s*(\{.*?\})", ai_response, re.DOTALL)
            if action_match:
                tool_name = action_match.group(1)
                try:
                    tool_params = json.loads(action_match.group(2))

                    # 执行工具
                    if tool_name in self.tools_map:
                        tool = self.tools_map[tool_name]
                        result = tool.execute(**tool_params)

                        # 数据拦截和脱敏
                        if tool_name == "generate_interactive_scene":
                            # 生成纯文字的观察结果
                            observation = "Interactive scene triggered"
                        else:
                            # 其他工具正常处理
                            observation = f"Observation: {json.dumps(result)}"

                        # 将工具执行结果作为 Observation 添加到消息列表
                        messages.append({"role": "user", "content": observation})
                    else:
                        # 工具不存在
                        observation = f"Observation: Tool '{tool_name}' not found"
                        messages.append({"role": "user", "content": observation})
                except json.JSONDecodeError:
                    # 参数解析错误
                    observation = "Observation: Invalid JSON format for tool parameters"
                    messages.append({"role": "user", "content": observation})
            elif "Action:" in ai_response:
                # 包含 Action: 但正则匹配失败
                print(f"警告：正则匹配 Action 失败！原始响应：{ai_response}")
                # 向 AI 反馈格式错误
                observation = "Observation: Invalid Action format. Please use the correct format: Action: tool_name {params}"
                messages.append({"role": "user", "content": observation})
            else:
                # 没有 Action，检查是否有 Final Answer
                if "Final Answer:" in ai_response:
                    # 提取 Final Answer 内容
                    final_answer_match = re.search(r"Final Answer:\s*(.+)", ai_response, re.DOTALL)
                    if final_answer_match:
                        final_answer = final_answer_match.group(1).strip()

                        # 处理图表数据 (旧格式兼容)
                        if self.current_plot_data:
                            # 使用替换逻辑
                            final_answer = final_answer.replace(
                                "[PLOT_DATA]",
                                f"\n\n```json\n{json.dumps(self.current_plot_data)}\n```"
                            )

                            # 重置当前图表数据，防止数据污染
                            self.current_plot_data = None

                        # 实时输出最终答案
                        yield f"data: {json.dumps({'type': 'final_answer', 'content': final_answer})}\n\n"

                        # 结束生成
                        return

        # 如果达到最大迭代次数仍无结果
        yield f"data: {json.dumps({'type': 'final_answer', 'content': '请求超时：AI 在多次尝试后未能生成响应，请稍后再试。'})}\n\n"


# 创建全局 AgentManager 实例
agent_manager = AgentManager()