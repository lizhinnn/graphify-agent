graphify-agent/ # 项目根目录
│
├── run.py # 启动脚本，同时启动前端和后端服务
├── pyproject.toml # Python项目配置（poetry依赖管理）
├── requirements.txt # pip依赖列表
├── .env # 环境变量配置（API密钥等）
├── .gitignore # Git忽略规则
│
├── agent/ # AI Agent核心模块（ReAct模式）
│ ├── **init**.py # 包初始化
│ ├── manager.py # AgentManager：ReAct循环调度、LLM调用、工具执行
│ ├── prompt\_templates.py # 系统提示词模板（定义ReAct格式和工具使用规范）
│ ├── tools\_adapter.py # 工具适配器（提供工具schema注册和执行接口）
│ ├── test\_manager.py # AgentManager异步测试（概念学习检测、run\_stream测试）
│ └── tools/ # 工具集（自动发现机制）
│ ├── **init**.py # 工具自动发现与注册
│ ├── base.py # Tool抽象基类（ABC模式）
│ ├── graphify\_tool.py # 知识图谱工具：实体抽取、关系抽取、图谱分析、文档摄取
│ ├── formula\_tool.py # 数学公式可视化工具（Plotly.js交互图表）
│ ├── search\_tool.py # 搜索工具（占位符，未实现）
│ └── interactive\_plot\_tool.py # 交互式绘图工具（增强版公式可视化）
│
├── graphify/ # 核心知识图谱处理包
│ ├── **init**.py # 包初始化，延迟导入映射
│ ├── **main**.py # CLI入口，支持install/query/path/explain等20+命令
│ ├── extract.py # 源码AST解析和文档语义提取（生成nodes和edges）
│ ├── build.py # 将nodes/edges组装成NetworkX图对象
│ ├── cluster.py # 社区检测（Leiden/Louvain算法），计算内聚度
│ ├── analyze.py # 图分析：god nodes(核心节点)、surprising connections(意外连接)
│ ├── report.py # 生成GRAPH\_REPORT.md人类可读报告
│ ├── validate.py # 验证提取JSON数据是否符合schema规范
│ ├── detect.py # 文件发现、类型分类(code/doc/paper/image)、语料库健康检查
│ ├── security.py # 安全工具：URL验证、安全fetch、路径验证、防SSRF
│ ├── export.py # 导出器：生成HTML/JSON/SVG/GraphML/Obsidian vault/Neo4j Cypher
│ ├── wiki.py # 维基百科风格markdown生成器（社区索引+文章）
│ ├── ingest.py # URL摄取：支持tweet/arxiv/pdf/web/YouTube转markdown
│ ├── cache.py # 文件级提取缓存（SHA256哈希），避免重复处理
│ ├── hooks.py # Git hooks集成（post-commit/post-checkout自动重建图）
│ ├── serve.py # MCP stdio服务器，暴露query\_graph/get\_node等工具给AI Agent
│ ├── watch.py # 文件夹监控，代码变更时自动AST重建（无需LLM）
│ ├── benchmark.py # Token削减基准测试：衡量图谱查询vs全语料库开销
│ ├── transcribe.py # 视频音频转录（faster-whisper + yt-dlp）
│ ├── manifest.py # 向后兼容的manifest helpers重导出
│ ├── skill.md # Claude Code skill定义文件
│ ├── skill-aider.md # Aider平台skill文件
│ ├── skill-codex.md # Codex平台skill文件
│ ├── skill-copilot.md # Copilot平台skill文件
│ ├── skill-claw\.md # Claw平台skill文件
│ ├── skill-droid.md # Droid平台skill文件
│ ├── skill-kiro.md # Kiro平台skill文件
│ ├── skill-opencode.md # OpenCode平台skill文件
│ ├── skill-trae.md # Trae平台skill文件
│ └── skill-windows.md # Windows平台skill文件
│
├── server/ # FastAPI后端服务
│ ├── **init**.py # 包初始化
│ ├── main.py # FastAPI应用入口，/api/chat聊天接口
│ ├── config.py # Settings配置类（加载.env、API密钥管理）
│ └── schemas.py # Pydantic数据模型（QueryRequest/QueryResponse）
│
├── storage/ # 存储目录
│ ├── graphs/ # 图谱JSON存储
│ │ ├── graph.json # 知识图谱数据
│ │ ├── graph.html # 交互式可视化HTML
│ │ └── graph原始.html # 原始图谱HTML
│ └── uploads/ # 用户上传文件
│ └── Modern\_Control\_Systems\_12th\_Edition\_origin\_fix.pdf # 上传的PDF文件
│
└── web/ # React前端应用
├── package.json # npm项目配置（React/Plotly.js/Tailwind）
├── tailwind.config.js # Tailwind CSS主题配置
├── postcss.config.js # PostCSS转换配置
├── public/
│ └── index.html # HTML入口文件
└── src/
├── index.js # React DOM渲染入口
├── index.css # 全局样式
├── App.js # 主应用组件（聊天界面核心逻辑）
└── components/
├── ChatInput.js # 消息输入框（支持Enter发送）
├── InteractiveChart.js # Plotly.js交互式数学图表渲染
├── InteractiveRenderer.js # iframe沙箱交互式可视化渲染器
├── MessageList.js # 消息列表（Markdown+图表数据提取渲染）
├── Navbar.js # 顶部导航栏
├── Sidebar.js # 侧边栏（对话管理）
├── Stage.js # 教学内容阶段展示组件（解析INTERACTIVE\_HTML/GRAPH\_DATA/MATH\_DERIVATION标记）
└── SceneRenderer.js # 场景渲染器（支持vis\_network图、interactive\_html交互、math\_derivation公式三种模式）
