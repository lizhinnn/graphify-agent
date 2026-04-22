from openai import OpenAI
from server.config import settings
from agent.prompt_templates import SYSTEM_PROMPT
from agent.tools import TOOLS
import re
import json


class AgentManager:
    def __init__(self):
        self.tools = TOOLS
        self.tools_map = {tool.name: tool for tool in self.tools}
        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_API_BASE
        )
        self.tool_results = {
            "graphify": None,
            "generate_interactive_scene": None
        }
        self.scenes_queue = []

    def add_tool(self, tool):
        self.tools.append(tool)
        self.tools_map[tool.name] = tool

    def _extract_scene_from_content(self, content):
        """从内容中提取场景信息，兼容 [SECTION]、[SCENE] 和 [NEXT_HINT] 标签的嵌套关系"""
        scenes = []
        
        # 提取 SECTION 标签
        section_pattern = r'\[SECTION_START:\s*([^\]]+)\]([\s\S]*?)\[NEXT_HINT:\s*([^\]]+)\]\s*\[SECTION_END\]'
        section_matches = re.finditer(section_pattern, content)
        
        for section_match in section_matches:
            section_title = section_match.group(1).strip()
            section_content = section_match.group(2).strip()
            next_hint = section_match.group(3).strip()
            
            # 从 section 内容中提取 SCENE 标签
            scene_pattern = r'\[SCENE_START:\s*(\w+)\]\s*```(\w+)\n([\s\S]*?)```\s*\[SCENE_END\]'
            scene_matches = re.finditer(scene_pattern, section_content)
            
            for scene_match in scene_matches:
                scene_type = scene_match.group(1).upper()
                code_type = scene_match.group(2)
                code_content = scene_match.group(3).strip()
                
                scene_data = {
                    'type': scene_type,
                    'code_type': code_type,
                    'content': code_content,
                    'section_title': section_title,
                    'next_hint': next_hint
                }
                
                if scene_type == 'GRAPH':
                    scenes.append({**scene_data, 'render_type': 'graph_data'})
                elif scene_type == 'INTERACTIVE':
                    scenes.append({**scene_data, 'render_type': 'interactive_html'})
                elif scene_type == 'MATH':
                    scenes.append({**scene_data, 'render_type': 'math_derivation'})
        
        # 直接提取 SCENE 标签（不嵌套在 SECTION 中的情况）
        direct_scene_pattern = r'\[SCENE_START:\s*(\w+)\]\s*```(\w+)\n([\s\S]*?)```\s*\[SCENE_END\]'
        direct_scene_matches = re.finditer(direct_scene_pattern, content)
        
        for match in direct_scene_matches:
            scene_type = match.group(1).upper()
            code_type = match.group(2)
            code_content = match.group(3).strip()
            
            scene_data = {
                'type': scene_type,
                'code_type': code_type,
                'content': code_content
            }
            
            if scene_type == 'GRAPH':
                scenes.append({**scene_data, 'render_type': 'graph_data'})
            elif scene_type == 'INTERACTIVE':
                scenes.append({**scene_data, 'render_type': 'interactive_html'})
            elif scene_type == 'MATH':
                scenes.append({**scene_data, 'render_type': 'math_derivation'})
        
        return scenes

    async def _push_scene_update(self, scene):
        """推送场景更新消息"""
        try:
            yield f"data: {json.dumps({'type': 'scene_update', 'scene': scene})}\n\n"
        except Exception as e:
            print(f"推送场景更新失败: {e}")
            # 发送错误消息但不中断连接
            yield f"data: {json.dumps({'type': 'error', 'content': '场景渲染失败'})}\n\n"

    async def run_stream(self, query):
        """实现 ReAct 模式的核心调度逻辑，返回异步生成器"""
        # 识别用户意图，判断是否为概念学习
        is_concept_learning = False
        concept_keywords = ['概念', '原理', '定义', '解释', '是什么', '为什么', '如何', '学习', '理解']
        for keyword in concept_keywords:
            if keyword in query:
                is_concept_learning = True
                break

        # 构建初始消息
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query}
        ]

        # 跟踪工具调用状态
        tools_called = set()

        if is_concept_learning:
            # 第一步：生成教学大纲
            print("\n--- 正在调用 LLM 仅生成教学大纲 ---")
            yield f"data: {json.dumps({'type': 'stage', 'content': '正在生成教学大纲...'})}\n\n"
            
            # 构建生成大纲的消息
            outline_messages = messages.copy()
            outline_messages.append({"role": "user", "content": "请仅输出教学大纲，格式为 CourseOutline: {\"title\": \"标题\", \"modules\": [\"模块1\", \"模块2\", ...]}"})
            
            # 调用 LLM 生成大纲
            outline_response = self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=outline_messages,
                temperature=0,
                timeout=100,
                stream=False
            )
            
            ai_response = outline_response.choices[0].message.content
            print(f"--- 大纲生成完成：\n{ai_response}\n---")
            
            # 解析 CourseOutline
            course_outline = None
            # 尝试从不同格式中提取大纲
            # 1. 尝试从 [[OUTLINE_START]] 和 [[OUTLINE_END]] 标记中提取
            outline_match = re.search(r'\[\[OUTLINE_START\]\]\s*({[\s\S]*?)\s*\[\[OUTLINE_END\]\]', ai_response)
            if not outline_match:
                # 2. 尝试从 CourseOutline: 标记后提取
                outline_match = re.search(r'CourseOutline:\s*({[\s\S]*?)(?=\n|$)', ai_response, re.DOTALL)
            if not outline_match:
                # 3. 尝试提取任何 JSON 对象
                outline_match = re.search(r'\{[^}]*"title"[^}]*"modules"[^}]*\}', ai_response, re.DOTALL)
            
            if outline_match:
                try:
                    course_outline = json.loads(outline_match.group(1))
                    print(f"=== 识别到教学大纲: {course_outline.get('title', '未命名')}")
                    print(f"=== 大纲推理: {course_outline.get('reasoning', '未提供')}")
                    print(f"=== 模块列表: {[m.get('name') if isinstance(m, dict) else m for m in course_outline.get('modules', [])]}")
                    
                    # 检查是否包含必要的 modules 字段
                    if 'modules' not in course_outline or not isinstance(course_outline['modules'], list):
                        print("警告：大纲中缺少 modules 字段，使用默认模板")
                        # 使用默认的大纲模板作为兜底
                        course_outline['modules'] = [
                            {"name": "背景引入", "content": "简介", "need_formula": False, "need_visualization": False, "graph_nodes": []},
                            {"name": "深度解析", "content": "定义与推导", "need_formula": True, "formula_type": "block", "need_visualization": False, "graph_nodes": []},
                            {"name": "可视化演示", "content": "交互展示", "need_formula": False, "need_visualization": True, "visualization_type": "interactive", "graph_nodes": []},
                            {"name": "图谱关联", "content": "知识网络", "need_formula": False, "need_visualization": False, "graph_nodes": []},
                            {"name": "学习总结", "content": "要点回顾", "need_formula": False, "need_visualization": False, "graph_nodes": []}
                        ]
                    
                    # 提取 reasoning 字段（可选）
                    reasoning = course_outline.get('reasoning', '')
                    yield f"data: {json.dumps({'type': 'outline_generated', 'outline': course_outline, 'reasoning': reasoning})}\n\n"
                except json.JSONDecodeError as e:
                    print(f"错误：解析 CourseOutline 失败: {e}")
                    yield f"data: {json.dumps({'type': 'error', 'content': '大纲格式错误，正在重试...'})}\n\n"
                    # 尝试使用默认模板
                    course_outline = {
                        "title": "默认教学大纲",
                        "modules": [
                            {"name": "背景引入", "content": "简介", "need_formula": False, "need_visualization": False, "graph_nodes": []},
                            {"name": "深度解析", "content": "定义与推导", "need_formula": True, "formula_type": "block", "need_visualization": False, "graph_nodes": []},
                            {"name": "可视化演示", "content": "交互展示", "need_formula": False, "need_visualization": True, "visualization_type": "interactive", "graph_nodes": []},
                            {"name": "图谱关联", "content": "知识网络", "need_formula": False, "need_visualization": False, "graph_nodes": []},
                            {"name": "学习总结", "content": "要点回顾", "need_formula": False, "need_visualization": False, "graph_nodes": []}
                        ],
                        "reasoning": "使用默认模板因为原始大纲解析失败"
                    }
                    print("使用默认大纲模板")
                    yield f"data: {json.dumps({'type': 'outline_generated', 'outline': course_outline, 'reasoning': course_outline['reasoning']})}\n\n"
            else:
                print("错误：未找到 CourseOutline")
                yield f"data: {json.dumps({'type': 'error', 'content': '大纲格式错误，正在重试...'})}\n\n"
                # 使用默认的大纲模板作为兜底
                course_outline = {
                    "title": "默认教学大纲",
                    "modules": [
                        {"name": "背景引入", "content": "简介", "need_formula": False, "need_visualization": False, "graph_nodes": []},
                        {"name": "深度解析", "content": "定义与推导", "need_formula": True, "formula_type": "block", "need_visualization": False, "graph_nodes": []},
                        {"name": "可视化演示", "content": "交互展示", "need_formula": False, "need_visualization": True, "visualization_type": "interactive", "graph_nodes": []},
                        {"name": "图谱关联", "content": "知识网络", "need_formula": False, "need_visualization": False, "graph_nodes": []},
                        {"name": "学习总结", "content": "要点回顾", "need_formula": False, "need_visualization": False, "graph_nodes": []}
                    ],
                    "reasoning": "使用默认模板因为未找到大纲"
                }
                print("使用默认大纲模板")
                yield f"data: {json.dumps({'type': 'outline_generated', 'outline': course_outline, 'reasoning': course_outline['reasoning']})}\n\n"
            
            # 第二步：遍历大纲中的模块，逐个生成内容
            modules = course_outline.get('modules', [])
            total_modules = len(modules)
            
            if not modules:
                print("错误：大纲中没有模块")
                # 使用默认模块列表
                modules = [
                    {"name": "背景引入", "content": "简介", "need_formula": False, "need_visualization": False, "graph_nodes": []},
                    {"name": "深度解析", "content": "定义与推导", "need_formula": True, "formula_type": "block", "need_visualization": False, "graph_nodes": []},
                    {"name": "可视化演示", "content": "交互展示", "need_formula": False, "need_visualization": True, "visualization_type": "interactive", "graph_nodes": []},
                    {"name": "图谱关联", "content": "知识网络", "need_formula": False, "need_visualization": False, "graph_nodes": []},
                    {"name": "学习总结", "content": "要点回顾", "need_formula": False, "need_visualization": False, "graph_nodes": []}
                ]
                total_modules = len(modules)
                print("使用默认模块列表")
            
            # 构建包含大纲的初始消息
            module_messages = messages.copy()
            module_messages.append({"role": "assistant", "content": ai_response})
            
            # 存储已生成的模块内容，用于上下文管理
            generated_content = []
            
            for i, module in enumerate(modules):
                # 提取模块名称（支持对象和字符串两种格式）
                if isinstance(module, dict):
                    module_name = module.get('name', f'模块{i+1}')
                    module_content_hint = module.get('content', '')
                else:
                    module_name = str(module)
                    module_content_hint = ''
                
                print(f"\n--- 正在调用 LLM 生成模块 '{module_name}' ({i+1}/{total_modules}) ---")
                
                # 发送模块开始信号，包含当前步骤和总步骤数
                yield f"data: {json.dumps({'type': 'section_start', 'module': module_name, 'index': i, 'total': total_modules, 'content_hint': module_content_hint})}\n\n"
                
                # 构建当前模块的消息
                current_messages = module_messages.copy()
                
                # 添加前面已生成模块的上下文，并明确告诉 LLM 当前步骤
                if generated_content:
                    context = "\n".join(generated_content)
                    current_messages.append({"role": "user", "content": f"教学大纲共有 {total_modules} 个模块，你目前处于第 {i+1} 步（模块名称：'{module_name}'）。\n\n已生成的模块内容：\n{context}\n\n请专注于完成当前模块 '{module_name}' 的内容，保持与前面内容的连贯性。"})
                else:
                    current_messages.append({"role": "user", "content": f"教学大纲共有 {total_modules} 个模块，你目前处于第 {i+1} 步（模块名称：'{module_name}'）。\n\n请生成模块 '{module_name}' 的内容。"})
                
                # 调用 LLM 生成当前模块内容
                module_response = self.client.chat.completions.create(
                    model=settings.LLM_MODEL,
                    messages=current_messages,
                    temperature=0,
                    timeout=100,
                    stream=True
                )
                
                # 收集完整响应
                module_content = ""
                is_final_answer = False
                final_answer_buffer = ""
                
                for chunk in module_response:
                    if chunk.choices[0].delta.content:
                        chunk_content = chunk.choices[0].delta.content
                        module_content += chunk_content
                        
                        if "Final Answer:" in module_content and not is_final_answer:
                            is_final_answer = True
                            final_answer_match = re.search(r"Final Answer:\s*(.+)", module_content, re.DOTALL)
                            if final_answer_match:
                                final_answer_buffer = final_answer_match.group(1)
                            else:
                                final_answer_buffer = ""
                        elif is_final_answer:
                            final_answer_match = re.search(r"Final Answer:\s*(.+)", module_content, re.DOTALL)
                            if final_answer_match:
                                final_answer_buffer = final_answer_match.group(1)
                                
                                # 处理场景
                                scenes = self._extract_scene_from_content(final_answer_buffer)
                                for scene in scenes:
                                    if scene not in self.scenes_queue:
                                        self.scenes_queue.append(scene)
                                        try:
                                            async for msg in self._push_scene_update(scene):
                                                yield msg
                                        except Exception as e:
                                            print(f"处理场景更新失败: {e}")
                                            yield f"data: {json.dumps({'type': 'error', 'content': '场景渲染失败'})}\n\n"
                        
                        if not is_final_answer:
                            yield f"data: {json.dumps({'type': 'thought', 'content': chunk_content})}\n\n"
                        else:
                            # 发送模块内容的流式数据
                            yield f"data: {json.dumps({'type': 'module_content', 'module_name': module_name, 'content': final_answer_buffer})}\n\n"
                            yield f"data: {json.dumps({'type': 'final_answer', 'content': final_answer_buffer})}\n\n"
                
                # 处理工具调用
                action_match = re.search(r"Action:\s*(\w+)\s*(\{.*?\})", module_content, re.DOTALL)
                if action_match:
                    tool_name = action_match.group(1)
                    tools_called.add(tool_name)
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
                                # 存储交互场景参数
                                self.tool_results["generate_interactive_scene"] = tool_params
                                # 立即推送场景更新消息
                                interactive_scene = {
                                    'type': 'INTERACTIVE',
                                    'render_type': 'interactive_html',
                                    'content': f"<div class='p-4'>交互式场景已触发：{tool_params.get('concept', '系统')}</div>",
                                    'code_type': 'html'
                                }
                                async for msg in self._push_scene_update(interactive_scene):
                                    yield msg
                            elif tool_name == "graphify" and tool_params.get("action") == "get_sample_graph":
                                # 检查 graphify 工具的结果
                                if "error" in result or ("content" in result and "未找到图谱文件" in result["content"]):
                                    # 图谱文件不存在或出错，启动专业知识库模式
                                    observation = "Observation: Graph file not found. Entering professional knowledge base mode. You can now manually construct a knowledge graph using D3.js format in your Final Answer."
                                else:
                                    # 处理提取的图谱数据
                                    if "nodes" in result and "links" in result:
                                        # 构建包含节点和连线数据的观察结果
                                        observation = f"Observation: {{\"type\": \"graph_data\", \"nodes\": {json.dumps(result['nodes'])}, \"links\": {json.dumps(result['links'])}, \"highlight_ids\": {json.dumps(result.get('highlight_ids', []))}}}"
                                        # 存储图谱数据
                                        self.tool_results["graphify"] = {
                                            "nodes": result['nodes'],
                                            "links": result['links'],
                                            "highlight_ids": result.get('highlight_ids', [])
                                        }
                                        # 立即推送场景更新消息
                                        graph_scene = {
                                            'type': 'GRAPH',
                                            'render_type': 'graph_data',
                                            'content': json.dumps({
                                                'nodes': result['nodes'],
                                                'links': result['links'],
                                                'highlight_ids': result.get('highlight_ids', [])
                                            }),
                                            'code_type': 'json'
                                        }
                                        async for msg in self._push_scene_update(graph_scene):
                                            yield msg
                                    else:
                                        # 兼容旧格式
                                        observation = f"Observation: {json.dumps(result)}"
                                        # 存储图谱数据
                                        self.tool_results["graphify"] = result
                            else:
                                # 其他工具正常处理
                                observation = f"Observation: {json.dumps(result)}"

                            # 将工具执行结果作为 Observation 添加到消息列表
                            current_messages.append({"role": "assistant", "content": module_content})
                            current_messages.append({"role": "user", "content": observation})
                            
                            # 重新调用 LLM 处理工具结果
                            tool_response = self.client.chat.completions.create(
                                model=settings.LLM_MODEL,
                                messages=current_messages,
                                temperature=0,
                                timeout=100,
                                stream=True
                            )
                            
                            # 收集工具处理后的响应
                            tool_content = ""
                            for chunk in tool_response:
                                if chunk.choices[0].delta.content:
                                    chunk_content = chunk.choices[0].delta.content
                                    tool_content += chunk_content
                                    yield f"data: {json.dumps({'type': 'final_answer', 'content': tool_content})}\n\n"
                            
                            module_content = tool_content
                        else:
                            # 工具不存在
                            observation = f"Observation: Tool '{tool_name}' not found"
                            current_messages.append({"role": "assistant", "content": module_content})
                            current_messages.append({"role": "user", "content": observation})
                    except json.JSONDecodeError:
                        # 参数解析错误
                        observation = "Observation: Invalid JSON format for tool parameters"
                        current_messages.append({"role": "assistant", "content": module_content})
                        current_messages.append({"role": "user", "content": observation})
                elif "Action:" in module_content:
                    # 包含 Action: 但正则匹配失败
                    print(f"警告：正则匹配 Action 失败！原始响应：{module_content}")
                    # 向 AI 反馈格式错误
                    observation = "Observation: Invalid Action format. Please use the correct format: Action: tool_name {params}"
                    current_messages.append({"role": "assistant", "content": module_content})
                    current_messages.append({"role": "user", "content": observation})
                
                # 存储当前模块的内容，用于后续模块的上下文
                generated_content.append(f"## {module_name}\n{final_answer_buffer if is_final_answer else module_content}")
                
                # 更新模块消息列表，包含当前模块的内容
                module_messages.append({"role": "assistant", "content": module_content})
                
                # 发送模块结束信号
                yield f"data: {json.dumps({'type': 'section_end', 'module': module_name, 'index': i})}\n\n"
            
            # 所有模块生成完成
            print("\n--- 所有模块生成完成 ---")
            yield f"data: {json.dumps({'type': 'all_sections_completed'})}\n\n"
            
            # 推送所有场景更新
            if self.scenes_queue:
                for scene in self.scenes_queue:
                    try:
                        async for msg in self._push_scene_update(scene):
                            yield msg
                    except Exception as e:
                        print(f"处理场景更新失败: {e}")
                        yield f"data: {json.dumps({'type': 'error', 'content': '场景渲染失败'})}\n\n"
            
            return
        else:
            # 非概念学习，按原有逻辑处理
            print("\n--- 正在调用 LLM 处理非概念学习查询 ---")
            
            max_iterations = 10
            for i in range(max_iterations):
                # 调用 LLM
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

                        if "Final Answer:" in ai_response and not is_final_answer:
                            is_final_answer = True
                            final_answer_match = re.search(r"Final Answer:\s*(.+)", ai_response, re.DOTALL)
                            if final_answer_match:
                                final_answer_buffer = final_answer_match.group(1)
                            else:
                                final_answer_buffer = ""
                        elif is_final_answer:
                            final_answer_match = re.search(r"Final Answer:\s*(.+)", ai_response, re.DOTALL)
                            if final_answer_match:
                                final_answer_buffer = final_answer_match.group(1)
                                
                                # 处理场景
                                scenes = self._extract_scene_from_content(final_answer_buffer)
                                for scene in scenes:
                                    if scene not in self.scenes_queue:
                                        self.scenes_queue.append(scene)
                                        try:
                                            async for msg in self._push_scene_update(scene):
                                                yield msg
                                        except Exception as e:
                                            print(f"处理场景更新失败: {e}")
                                            yield f"data: {json.dumps({'type': 'error', 'content': '场景渲染失败'})}\n\n"

                        if not is_final_answer:
                            yield f"data: {json.dumps({'type': 'thought', 'content': chunk_content})}\n\n"
                        else:
                            yield f"data: {json.dumps({'type': 'final_answer', 'content': final_answer_buffer})}\n\n"

                if is_final_answer and "Final Answer:" in ai_response:
                    # 处理工具调用
                    action_match = re.search(r"Action:\s*(\w+)\s*(\{.*?\})", ai_response, re.DOTALL)
                    if action_match:
                        tool_name = action_match.group(1)
                        tools_called.add(tool_name)
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
                                    # 存储交互场景参数
                                    self.tool_results["generate_interactive_scene"] = tool_params
                                    # 立即推送场景更新消息
                                    interactive_scene = {
                                        'type': 'INTERACTIVE',
                                        'render_type': 'interactive_html',
                                        'content': f"<div class='p-4'>交互式场景已触发：{tool_params.get('concept', '系统')}</div>",
                                        'code_type': 'html'
                                    }
                                    async for msg in self._push_scene_update(interactive_scene):
                                        yield msg
                                elif tool_name == "graphify" and tool_params.get("action") == "get_sample_graph":
                                    # 检查 graphify 工具的结果
                                    if "error" in result or ("content" in result and "未找到图谱文件" in result["content"]):
                                        # 图谱文件不存在或出错，启动专业知识库模式
                                        observation = "Observation: Graph file not found. Entering professional knowledge base mode. You can now manually construct a knowledge graph using D3.js format in your Final Answer."
                                    else:
                                        # 处理提取的图谱数据
                                        if "nodes" in result and "links" in result:
                                            # 构建包含节点和连线数据的观察结果
                                            observation = f"Observation: {{\"type\": \"graph_data\", \"nodes\": {json.dumps(result['nodes'])}, \"links\": {json.dumps(result['links'])}, \"highlight_ids\": {json.dumps(result.get('highlight_ids', []))}}}"
                                            # 存储图谱数据
                                            self.tool_results["graphify"] = {
                                                "nodes": result['nodes'],
                                                "links": result['links'],
                                                "highlight_ids": result.get('highlight_ids', [])
                                            }
                                            # 立即推送场景更新消息
                                            graph_scene = {
                                                'type': 'GRAPH',
                                                'render_type': 'graph_data',
                                                'content': json.dumps({
                                                    'nodes': result['nodes'],
                                                    'links': result['links'],
                                                    'highlight_ids': result.get('highlight_ids', [])
                                                }),
                                                'code_type': 'json'
                                            }
                                            async for msg in self._push_scene_update(graph_scene):
                                                yield msg
                                        else:
                                            # 兼容旧格式
                                            observation = f"Observation: {json.dumps(result)}"
                                            # 存储图谱数据
                                            self.tool_results["graphify"] = result
                                else:
                                    # 其他工具正常处理
                                    observation = f"Observation: {json.dumps(result)}"

                                # 将工具执行结果作为 Observation 添加到消息列表
                                messages.append({"role": "assistant", "content": ai_response})
                                messages.append({"role": "user", "content": observation})
                                continue
                            else:
                                # 工具不存在
                                observation = f"Observation: Tool '{tool_name}' not found"
                                messages.append({"role": "assistant", "content": ai_response})
                                messages.append({"role": "user", "content": observation})
                                continue
                        except json.JSONDecodeError:
                            # 参数解析错误
                            observation = "Observation: Invalid JSON format for tool parameters"
                            messages.append({"role": "assistant", "content": ai_response})
                            messages.append({"role": "user", "content": observation})
                            continue
                    
                    # 处理最终答案
                    enhanced_final_answer = final_answer_buffer
                    
                    if self.tool_results["graphify"]:
                        graph_data = self.tool_results["graphify"]
                        if isinstance(graph_data, dict) and "nodes" in graph_data:
                            node_names = [node.get("id", "") for node in graph_data["nodes"] if node.get("id")]
                            if node_names:
                                messages.append({"role": "assistant", "content": ai_response})
                                messages.append({"role": "user", "content": f"Observation: 图谱工具返回了以下节点：{', '.join(node_names)}。请在 Final Answer 中分析这些节点与当前概念的关系。"})
                                continue
                    
                    if self.tool_results["generate_interactive_scene"]:
                        scene_params = self.tool_results["generate_interactive_scene"]
                        concept = scene_params.get("concept", "系统")
                        interactive_guide = f"\n\n接下来，请通过下方的交互滑块来观察参数对{concept}的影响。\n"
                        enhanced_final_answer += interactive_guide
                    
                    # 推送场景更新
                    scenes = self._extract_scene_from_content(enhanced_final_answer)
                    for scene in scenes:
                        if scene not in self.scenes_queue:
                            self.scenes_queue.append(scene)
                            try:
                                async for msg in self._push_scene_update(scene):
                                    yield msg
                            except Exception as e:
                                print(f"处理场景更新失败: {e}")
                                yield f"data: {json.dumps({'type': 'error', 'content': '场景渲染失败'})}\n\n"
                    
                    print(f"--- AI 回复内容：\n{ai_response}\n---")
                    messages.append({"role": "assistant", "content": ai_response})
                    
                    # 推送所有场景更新
                    if self.scenes_queue:
                        for scene in self.scenes_queue:
                            try:
                                async for msg in self._push_scene_update(scene):
                                    yield msg
                            except Exception as e:
                                print(f"处理场景更新失败: {e}")
                                yield f"data: {json.dumps({'type': 'error', 'content': '场景渲染失败'})}\n\n"
                    
                    return

                # 添加 AI 回复日志
                print(f"--- [Step {i+1}] AI 回复内容：\n{ai_response}\n---")
                messages.append({"role": "assistant", "content": ai_response})

                # 处理工具调用
                action_match = re.search(r"Action:\s*(\w+)\s*(\{.*?\})", ai_response, re.DOTALL)
                if action_match:
                    tool_name = action_match.group(1)
                    tools_called.add(tool_name)
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
                                # 存储交互场景参数
                                self.tool_results["generate_interactive_scene"] = tool_params
                                # 立即推送场景更新消息
                                interactive_scene = {
                                    'type': 'INTERACTIVE',
                                    'render_type': 'interactive_html',
                                    'content': f"<div class='p-4'>交互式场景已触发：{tool_params.get('concept', '系统')}</div>",
                                    'code_type': 'html'
                                }
                                async for msg in self._push_scene_update(interactive_scene):
                                    yield msg
                            elif tool_name == "graphify" and tool_params.get("action") == "get_sample_graph":
                                # 检查 graphify 工具的结果
                                if "error" in result or ("content" in result and "未找到图谱文件" in result["content"]):
                                    # 图谱文件不存在或出错，启动专业知识库模式
                                    observation = "Observation: Graph file not found. Entering professional knowledge base mode. You can now manually construct a knowledge graph using D3.js format in your Final Answer."
                                else:
                                    # 处理提取的图谱数据
                                    if "nodes" in result and "links" in result:
                                        # 构建包含节点和连线数据的观察结果
                                        observation = f"Observation: {{\"type\": \"graph_data\", \"nodes\": {json.dumps(result['nodes'])}, \"links\": {json.dumps(result['links'])}, \"highlight_ids\": {json.dumps(result.get('highlight_ids', []))}}}"
                                        # 存储图谱数据
                                        self.tool_results["graphify"] = {
                                            "nodes": result['nodes'],
                                            "links": result['links'],
                                            "highlight_ids": result.get('highlight_ids', [])
                                        }
                                        # 立即推送场景更新消息
                                        graph_scene = {
                                            'type': 'GRAPH',
                                            'render_type': 'graph_data',
                                            'content': json.dumps({
                                                'nodes': result['nodes'],
                                                'links': result['links'],
                                                'highlight_ids': result.get('highlight_ids', [])
                                            }),
                                            'code_type': 'json'
                                        }
                                        async for msg in self._push_scene_update(graph_scene):
                                            yield msg
                                    else:
                                        # 兼容旧格式
                                        observation = f"Observation: {json.dumps(result)}"
                                        # 存储图谱数据
                                        self.tool_results["graphify"] = result
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

                            # 实时输出最终答案
                            yield f"data: {json.dumps({'type': 'final_answer', 'content': final_answer})}\n\n"

                            # 结束生成
                            return

            # 如果达到最大迭代次数仍无结果
            yield f"data: {json.dumps({'type': 'final_answer', 'content': '请求超时：AI 在多次尝试后未能生成响应，请稍后再试。'})}\n\n"


# 创建全局 AgentManager 实例
agent_manager = AgentManager()