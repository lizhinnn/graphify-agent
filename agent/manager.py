from openai import OpenAI
from server.config import settings
from server.database import get_db_session, ChatMessage
from agent.prompt_templates import SYSTEM_PROMPT, CONCEPT_DETECTION_PROMPT
from agent.tools import TOOLS
import re
import json
import httpx


class AgentManager:
    def __init__(self):
        self.tools = TOOLS
        self.tools_map = {tool.name: tool for tool in self.tools}
        # 配置 httpx 客户端以支持长连接
        httpx_client = httpx.Client(
            timeout=httpx.Timeout(120.0, connect=30.0, read=120.0, write=60.0),
            limits=httpx.Limits(max_connections=50, max_keepalive_connections=10),
            headers={"Connection": "keep-alive"}
        )
        
        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_API_BASE,
            timeout=120.0,
            http_client=httpx_client
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
                
                # 清洗 Markdown 代码块围栏
                if code_content.startswith('```') and code_content.endswith('```'):
                    code_content = code_content[3:-3].strip()
                elif code_content.startswith('```html') and code_content.endswith('```'):
                    code_content = code_content[7:-3].strip()
                elif code_content.startswith('```latex') and code_content.endswith('```'):
                    code_content = code_content[8:-3].strip()
                
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
            
            # 清洗 Markdown 代码块围栏
            if code_content.startswith('```') and code_content.endswith('```'):
                code_content = code_content[3:-3].strip()
            elif code_content.startswith('```html') and code_content.endswith('```'):
                code_content = code_content[7:-3].strip()
            elif code_content.startswith('```latex') and code_content.endswith('```'):
                code_content = code_content[8:-3].strip()
            
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

    async def run_stream(self, query, session_id=None):
        """实现 ReAct 模式的核心调度逻辑，返回异步生成器"""
        # 识别用户意图，判断是否为概念学习
        is_concept_learning = False
        
        # 构建初始消息
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        
        # 加载会话历史作为上下文
        if session_id:
            try:
                db = get_db_session()
                # 获取最近的 10 条消息作为上下文
                historical_messages = db.query(ChatMessage).filter(
                    ChatMessage.session_id == session_id
                ).order_by(ChatMessage.created_at.desc()).limit(10).all()
                
                # 反转顺序，确保时间顺序正确
                historical_messages = list(reversed(historical_messages))
                
                for msg in historical_messages:
                    messages.append({
                        "role": msg.role,
                        "content": msg.content
                    })
                
                print(f"加载了 {len(historical_messages)} 条历史消息作为上下文")
            except Exception as e:
                print(f"加载历史消息失败: {e}")
        
        # 添加当前用户消息
        messages.append({"role": "user", "content": query})
        
        try:
            # 使用 LLM 进行智能判断
            detection_prompt = CONCEPT_DETECTION_PROMPT.format(query=query)
            detection_messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": detection_prompt}
            ]
            
            detection_response = self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=detection_messages,
                temperature=0,
                timeout=30,
                stream=False
            )
            
            detection_content = detection_response.choices[0].message.content
            print(f"概念学习检测结果: {detection_content}")
            
            # 解析 JSON 响应
            detection_result = json.loads(detection_content)
            is_concept_learning = detection_result.get('is_concept_learning', False)
        except Exception as e:
            print(f"概念学习检测失败，使用备用逻辑: {e}")
            # 备用逻辑：基于关键词匹配
            concept_keywords = [
                '概念', '原理', '定义', '解释', '是什么', '为什么', '如何', '学习', '理解',
                '分析', '解析', '详解', '介绍', '概述', '说明', '含义', '意义', '本质',
                '特性', '特征', '属性', '规律', '法则', '定理', '公式', '推导', '证明',
                '演示', '分析'  # 增加深度学习诉求词汇
            ]
            
            # 否定关键词（排除明显不是概念学习的请求）
            negative_keywords = [
                '代码', '编程', '实现', '开发', '调试', '修复', 'bug', '错误',
                'LeetCode', '算法', '题解', '刷题', '考试', '测试', '作业',
                '命令', '操作', '配置', '安装', '部署', '运行', '启动'
            ]
            
            # 检查是否包含概念学习关键词
            has_concept_keywords = any(keyword in query for keyword in concept_keywords)
            
            # 检查是否包含否定关键词
            has_negative_keywords = any(keyword in query for keyword in negative_keywords)
            
            # 只有当包含概念学习关键词且不包含否定关键词时，才认为是概念学习
            if has_concept_keywords and not has_negative_keywords:
                # 进一步判断：如果查询包含具体的技术概念或理论名称，更可能是概念学习
                technical_terms = ['二阶系统', '单位阶跃响应', '传递函数', '稳定性', '反馈系统',
                                  '控制系统', '信号处理', '数学模型', '算法原理', '数据结构']
                has_technical_terms = any(term in query for term in technical_terms)
                
                is_concept_learning = True or has_technical_terms

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
                    # 提取 JSON 字符串
                    json_str = outline_match.group(1)
                    
                    # JSON 格式容错处理
                    # 1. 移除多余的转义字符
                    json_str = json_str.replace('\\n', ' ').replace('\\t', ' ')
                    # 2. 移除首尾空白
                    json_str = json_str.strip()
                    # 3. 确保字符串使用双引号
                    json_str = re.sub(r"'(\w+)':", r'"\1":', json_str)
                    json_str = re.sub(r":\s*'([^']*)'", r': "\1"', json_str)
                    
                    course_outline = json.loads(json_str)
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
                    print(f"尝试解析的 JSON 字符串: {json_str}")
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
            
            # 存储已生成的模块内容，用于上下文管理
            generated_content = []
            
            # 异常检测：存储之前的 Final Answer 内容，用于检测重复或偏离
            previous_final_answers = []
            
            # 初始化模块消息列表，确保变量生命周期完整
            module_messages = messages.copy()
            module_messages.append({"role": "assistant", "content": ai_response})
            
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
                
                # 构建当前模块的消息，确保包含最初的 SYSTEM_PROMPT、用户的原始 query 以及当前的大纲
                current_messages = messages.copy()  # 包含 SYSTEM_PROMPT 和原始 query
                current_messages.append({"role": "assistant", "content": ai_response})  # 添加大纲
                
                # 添加前面已生成模块的上下文，并明确告诉 LLM 当前步骤
                if generated_content:
                    context = "\n".join(generated_content)
                    current_messages.append({"role": "user", "content": f"教学大纲共有 {total_modules} 个模块，你目前处于第 {i+1} 步（模块名称：'{module_name}'）。\n\n原始查询：{query}\n\n已生成的模块内容：\n{context}\n\n请专注于完成当前模块 '{module_name}' 的内容，保持与前面内容的连贯性。\n\n重要：你的回答必须与原始查询 '{query}' 相关，严禁生成与主题无关的内容。"})
                else:
                    current_messages.append({"role": "user", "content": f"教学大纲共有 {total_modules} 个模块，你目前处于第 {i+1} 步（模块名称：'{module_name}'）。\n\n原始查询：{query}\n\n请生成模块 '{module_name}' 的内容。\n\n重要：你的回答必须与原始查询 '{query}' 相关，严禁生成与主题无关的内容。"})
                
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
                final_answer_last_length = 0
                thought_buffer = ""
                thought_last_length = 0
                
                for chunk in module_response:
                    if chunk.choices[0].delta.content:
                        chunk_content = chunk.choices[0].delta.content
                        module_content += chunk_content
                        
                        if "Final Answer:" in module_content and not is_final_answer:
                            # 标记进入 Final Answer 阶段
                            is_final_answer = True
                            # 提取 Final Answer 之前的 Thought 内容
                            thought_match = re.search(r"Thought:\s*(.+?)\s*Final Answer:", module_content, re.DOTALL)
                            if thought_match:
                                thought_buffer = thought_match.group(1)
                                # 发送完整的 Thought 内容
                                yield f"data: {json.dumps({'type': 'thought', 'content': thought_buffer})}\n\n"
                                thought_last_length = len(thought_buffer)
                            # 提取 Final Answer 内容
                            final_answer_match = re.search(r"Final Answer:\s*(.+)", module_content, re.DOTALL)
                            if final_answer_match:
                                final_answer_buffer = final_answer_match.group(1)
                                # 发送初始 Final Answer 内容
                                yield f"data: {json.dumps({'type': 'module_content', 'module_name': module_name, 'content': final_answer_buffer})}\n\n"
                                yield f"data: {json.dumps({'type': 'final_answer', 'content': final_answer_buffer})}\n\n"
                                final_answer_last_length = len(final_answer_buffer)
                            else:
                                final_answer_buffer = ""
                        elif is_final_answer:
                            # 只更新 Final Answer 内容，避免重复推送
                            final_answer_match = re.search(r"Final Answer:\s*(.+)", module_content, re.DOTALL)
                            if final_answer_match:
                                new_final_answer = final_answer_match.group(1)
                                # 只有当内容发生变化时才推送
                                if new_final_answer != final_answer_buffer:
                                    final_answer_buffer = new_final_answer
                                    # 计算增量部分
                                    delta_content = final_answer_buffer[final_answer_last_length:]
                                    if delta_content:
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
                                        
                                        # 发送模块内容的流式数据（增量）
                                        yield f"data: {json.dumps({'type': 'module_content', 'module_name': module_name, 'content': delta_content})}\n\n"
                                        yield f"data: {json.dumps({'type': 'final_answer', 'content': delta_content})}\n\n"
                                        final_answer_last_length = len(final_answer_buffer)
                        elif not is_final_answer:
                            # 累积 Thought 内容
                            thought_buffer += chunk_content
                            # 发送增量 Thought 内容
                            delta_thought = thought_buffer[thought_last_length:]
                            if delta_thought:
                                yield f"data: {json.dumps({'type': 'thought', 'content': delta_thought})}\n\n"
                                thought_last_length = len(thought_buffer)
                
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
                            try:
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
                            except Exception as e:
                                # 捕获工具执行异常，返回友好错误提示
                                print(f"工具执行失败: {e}")
                                observation = f"Observation: Tool execution failed: {str(e)}. Please try again or use a different approach."
                                # 推送错误消息给前端
                                yield f"data: {json.dumps({'type': 'error', 'content': f'工具执行失败: {str(e)}，正在继续...'})}\n\n"

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
                            tool_content_last_length = 0
                            for chunk in tool_response:
                                if chunk.choices[0].delta.content:
                                    chunk_content = chunk.choices[0].delta.content
                                    tool_content += chunk_content
                                    # 发送增量内容
                                    delta_content = tool_content[tool_content_last_length:]
                                    if delta_content:
                                        yield f"data: {json.dumps({'type': 'final_answer', 'content': delta_content})}\n\n"
                                        tool_content_last_length = len(tool_content)
                            
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
                
                # 异常检测：检查生成的内容
                current_final_answer = final_answer_buffer if is_final_answer else module_content
                
                # 检查是否与原始查询相关
                is_relevant = True
                query_keywords = [word for word in query.split() if len(word) > 1]
                if query_keywords:
                    content_lower = current_final_answer.lower()
                    query_lower = query.lower()
                    
                    # 提取查询的核心关键词（长度大于2的词）
                    core_query_keywords = [keyword for keyword in query_keywords if len(keyword) > 2]
                    
                    # 检查是否包含查询中的核心关键词
                    has_core_query_keywords = any(keyword.lower() in content_lower for keyword in core_query_keywords)
                    
                    # 检查是否包含与主题无关的内容（如 LeetCode、算法题等）
                    irrelevant_terms = [
                        'leetcode', '刷题', '算法题', '代码练习', '编程题',
                        'c++', 'java', 'python', 'javascript', '代码实现',
                        '算法', '数据结构', '面试题', '力扣'
                    ]
                    has_irrelevant_content = any(term in content_lower for term in irrelevant_terms)
                    
                    # 检查学科领域一致性
                    # 控制工程相关关键词
                    control_engineering_terms = ['二阶系统', '单位阶跃响应', '传递函数', '稳定性', '反馈系统', '控制系统', '时域响应', '频域分析']
                    # 数学相关关键词
                    math_terms = ['数学', '公式', '推导', '证明', '定理', '方程', '函数']
                    # 物理相关关键词
                    physics_terms = ['物理', '力学', '电磁', '光学', '热学', '能量']
                    
                    # 确定查询的学科领域
                    query_control_terms = any(term in query_lower for term in control_engineering_terms)
                    query_math_terms = any(term in query_lower for term in math_terms)
                    query_physics_terms = any(term in query_lower for term in physics_terms)
                    
                    # 检查内容是否与学科领域一致
                    content_control_terms = any(term in content_lower for term in control_engineering_terms)
                    content_math_terms = any(term in content_lower for term in math_terms)
                    content_physics_terms = any(term in content_lower for term in physics_terms)
                    
                    # 学科领域一致性检查（放宽条件）
                    domain_consistent = True
                    if query_control_terms and not content_control_terms and not has_core_query_keywords:
                        domain_consistent = False
                    elif query_math_terms and not content_math_terms and not has_core_query_keywords:
                        domain_consistent = False
                    elif query_physics_terms and not content_physics_terms and not has_core_query_keywords:
                        domain_consistent = False
                    
                    # 放宽判断条件：只要包含核心关键词或学科领域相关术语，就认为是相关的
                    if (not has_core_query_keywords and not content_control_terms and not content_math_terms and not content_physics_terms) or has_irrelevant_content:
                        is_relevant = False
                        print(f"警告：模块 '{module_name}' 生成的内容可能与主题无关")
                        yield f"data: {json.dumps({'type': 'warning', 'content': f'模块 {module_name} 生成的内容可能与主题无关，正在重新生成...'})}\n\n"
                
                # 检查是否有重复内容
                is_duplicate = False
                for prev_answer in previous_final_answers:
                    # 计算内容相似度（简单的重叠率）
                    prev_words = set(prev_answer.split())
                    current_words = set(current_final_answer.split())
                    overlap_rate = len(prev_words.intersection(current_words)) / len(prev_words.union(current_words))
                    if overlap_rate > 0.7:
                        is_duplicate = True
                        print(f"警告：模块 '{module_name}' 生成的内容与之前的内容高度相似")
                        yield f"data: {json.dumps({'type': 'warning', 'content': f'模块 {module_name} 生成的内容与之前的内容高度相似，正在重新生成...'})}\n\n"
                        break
                
                # 如果内容不相关或重复，重新生成
                if not is_relevant or is_duplicate:
                    # 构建重新生成的消息
                    retry_messages = messages.copy()
                    retry_messages.append({"role": "assistant", "content": ai_response})
                    retry_messages.append({"role": "user", "content": f"你之前生成的模块 '{module_name}' 内容与原始查询 '{query}' 无关或与之前内容重复。请重新生成与主题相关的内容，严禁生成 LeetCode 等与主题无关的代码练习题。"})
                    
                    # 重新调用 LLM
                    retry_response = self.client.chat.completions.create(
                        model=settings.LLM_MODEL,
                        messages=retry_messages,
                        temperature=0,
                        timeout=100,
                        stream=True
                    )
                    
                    # 收集重新生成的响应
                    retry_content = ""
                    retry_final_answer = ""
                    retry_is_final_answer = False
                    retry_final_answer_last_length = 0
                    retry_thought_last_length = 0
                    retry_thought_buffer = ""
                    
                    for chunk in retry_response:
                        if chunk.choices[0].delta.content:
                            chunk_content = chunk.choices[0].delta.content
                            retry_content += chunk_content
                            
                            if "Final Answer:" in retry_content and not retry_is_final_answer:
                                retry_is_final_answer = True
                                # 提取 Final Answer 之前的 Thought 内容
                                retry_thought_match = re.search(r"Thought:\s*(.+?)\s*Final Answer:", retry_content, re.DOTALL)
                                if retry_thought_match:
                                    retry_thought_buffer = retry_thought_match.group(1)
                                    # 发送完整的 Thought 内容
                                    yield f"data: {json.dumps({'type': 'thought', 'content': retry_thought_buffer})}\n\n"
                                    retry_thought_last_length = len(retry_thought_buffer)
                                # 提取 Final Answer 内容
                                retry_final_match = re.search(r"Final Answer:\s*(.+)", retry_content, re.DOTALL)
                                if retry_final_match:
                                    retry_final_answer = retry_final_match.group(1)
                                    # 发送初始 Final Answer 内容
                                    yield f"data: {json.dumps({'type': 'module_content', 'module_name': module_name, 'content': retry_final_answer})}\n\n"
                                    yield f"data: {json.dumps({'type': 'final_answer', 'content': retry_final_answer})}\n\n"
                                    retry_final_answer_last_length = len(retry_final_answer)
                            elif retry_is_final_answer:
                                retry_final_match = re.search(r"Final Answer:\s*(.+)", retry_content, re.DOTALL)
                                if retry_final_match:
                                    new_retry_final_answer = retry_final_match.group(1)
                                    # 只有当内容发生变化时才推送
                                    if new_retry_final_answer != retry_final_answer:
                                        retry_final_answer = new_retry_final_answer
                                        # 计算增量部分
                                        delta_content = retry_final_answer[retry_final_answer_last_length:]
                                        if delta_content:
                                            # 处理场景
                                            scenes = self._extract_scene_from_content(retry_final_answer)
                                            for scene in scenes:
                                                if scene not in self.scenes_queue:
                                                    self.scenes_queue.append(scene)
                                                    try:
                                                        async for msg in self._push_scene_update(scene):
                                                            yield msg
                                                    except Exception as e:
                                                        print(f"处理场景更新失败: {e}")
                                                        yield f"data: {json.dumps({'type': 'error', 'content': '场景渲染失败'})}\n\n"
                                            # 发送增量内容
                                            yield f"data: {json.dumps({'type': 'module_content', 'module_name': module_name, 'content': delta_content})}\n\n"
                                            yield f"data: {json.dumps({'type': 'final_answer', 'content': delta_content})}\n\n"
                                            retry_final_answer_last_length = len(retry_final_answer)
                            elif not retry_is_final_answer:
                                # 累积 Thought 内容
                                retry_thought_buffer += chunk_content
                                # 发送增量 Thought 内容
                                delta_thought = retry_thought_buffer[retry_thought_last_length:]
                                if delta_thought:
                                    yield f"data: {json.dumps({'type': 'thought', 'content': delta_thought})}\n\n"
                                    retry_thought_last_length = len(retry_thought_buffer)
                    
                    current_final_answer = retry_final_answer if retry_is_final_answer else retry_content
                
                # 存储当前的 Final Answer 用于后续检测
                previous_final_answers.append(current_final_answer)
                
                # 存储当前模块的内容，用于后续模块的上下文
                generated_content.append(f"## {module_name}\n{current_final_answer}")
                
                # 更新模块消息列表，包含当前模块的内容
                module_messages.append({"role": "assistant", "content": current_final_answer})
                
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
                final_answer_last_length = 0
                thought_last_length = 0
                thought_buffer = ""

                for chunk in response:
                    if chunk.choices[0].delta.content:
                        chunk_content = chunk.choices[0].delta.content
                        ai_response += chunk_content

                        if "Final Answer:" in ai_response and not is_final_answer:
                            is_final_answer = True
                            # 提取 Final Answer 之前的 Thought 内容
                            thought_match = re.search(r"Thought:\s*(.+?)\s*Final Answer:", ai_response, re.DOTALL)
                            if thought_match:
                                thought_buffer = thought_match.group(1)
                                # 发送完整的 Thought 内容
                                yield f"data: {json.dumps({'type': 'thought', 'content': thought_buffer})}\n\n"
                                thought_last_length = len(thought_buffer)
                            # 提取 Final Answer 内容
                            final_answer_match = re.search(r"Final Answer:\s*(.+)", ai_response, re.DOTALL)
                            if final_answer_match:
                                final_answer_buffer = final_answer_match.group(1)
                                # 发送初始 Final Answer 内容
                                yield f"data: {json.dumps({'type': 'final_answer', 'content': final_answer_buffer})}\n\n"
                                final_answer_last_length = len(final_answer_buffer)
                            else:
                                final_answer_buffer = ""
                        elif is_final_answer:
                            final_answer_match = re.search(r"Final Answer:\s*(.+)", ai_response, re.DOTALL)
                            if final_answer_match:
                                new_final_answer = final_answer_match.group(1)
                                # 只有当内容发生变化时才推送
                                if new_final_answer != final_answer_buffer:
                                    final_answer_buffer = new_final_answer
                                    # 计算增量部分
                                    delta_content = final_answer_buffer[final_answer_last_length:]
                                    if delta_content:
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
                                        # 发送增量 Final Answer 内容
                                        yield f"data: {json.dumps({'type': 'final_answer', 'content': delta_content})}\n\n"
                                        final_answer_last_length = len(final_answer_buffer)
                        elif not is_final_answer:
                            # 累积 Thought 内容
                            thought_buffer += chunk_content
                            # 发送增量 Thought 内容
                            delta_thought = thought_buffer[thought_last_length:]
                            if delta_thought:
                                yield f"data: {json.dumps({'type': 'thought', 'content': delta_thought})}\n\n"
                                thought_last_length = len(thought_buffer)

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
                            try:
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
                            except Exception as e:
                                # 捕获工具执行异常，返回友好错误提示
                                print(f"工具执行失败: {e}")
                                observation = f"Observation: Tool execution failed: {str(e)}. Please try again or use a different approach."
                                # 推送错误消息给前端
                                yield f"data: {json.dumps({'type': 'error', 'content': f'工具执行失败: {str(e)}，正在继续...'})}\n\n"

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