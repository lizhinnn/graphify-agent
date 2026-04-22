import React, { useState, useEffect, useRef } from 'react';
import Sidebar from './components/Sidebar';
import Navbar from './components/Navbar';
import MessageList from './components/MessageList';
import ChatInput from './components/ChatInput';
import Stage from './components/Stage';

const API_BASE = 'http://localhost:8000';

function App() {
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [currentScene, setCurrentScene] = useState(null);
  const [currentOutline, setCurrentOutline] = useState(null);
  const [sceneArray, setSceneArray] = useState([]);
  const [currentSceneIndex, setCurrentSceneIndex] = useState(0);
  const [hasNextHint, setHasNextHint] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingMessageId, setLoadingMessageId] = useState(null);
  const [loadingStartTime, setLoadingStartTime] = useState(null);
  const [loadingStage, setLoadingStage] = useState(0);
  const isInitialLoad = useRef(true);
  const chatInputRef = useRef(null);

  const fetchSessions = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/sessions`);
      if (response.ok) {
        const sessions = await response.json();
        setConversations(sessions);
        if (isInitialLoad.current && sessions.length > 0 && !currentConversationId) {
          setCurrentConversationId(sessions[0].id);
          fetchSessionMessages(sessions[0].id);
        }
        isInitialLoad.current = false;
      }
    } catch (error) {
      console.error('获取会话列表失败:', error);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, []);

  // 获取会话历史消息
  const fetchSessionMessages = async (sessionId) => {
    try {
      const response = await fetch(`${API_BASE}/api/sessions/${sessionId}`);
      if (response.ok) {
        const sessionMessages = await response.json();
        // 转换后端消息格式以适配前端
        const formattedMessages = sessionMessages.map(msg => ({
          id: msg.id || Date.now() + Math.random(),
          role: msg.role,
          content: msg.content,
          isLoading: false
        }));
        setMessages(formattedMessages);
      }
    } catch (error) {
      console.error('获取会话历史失败:', error);
    }
  };

  useEffect(() => {
    let interval;
    if (isLoading && loadingStartTime) {
      interval = setInterval(() => {
        const elapsedTime = (Date.now() - loadingStartTime) / 1000;
        if (elapsedTime >= 15) {
          setLoadingStage(3);
        } else if (elapsedTime >= 5) {
          setLoadingStage(2);
        } else {
          setLoadingStage(1);
        }
      }, 1000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isLoading, loadingStartTime, loadingMessageId]);

  useEffect(() => {
    // 只处理基本的大纲提取，不再进行复杂的内容切分
    if (messages.length > 0) {
      const latestMessage = messages[messages.length - 1];
      if (latestMessage.role === 'assistant' && !latestMessage.isLoading) {
        const content = latestMessage.content;
        
        // 提取 Markdown 大纲
        if (content.includes('1. ') && content.includes('\n')) {
          setCurrentOutline(content);
        }
      }
    }
  }, [messages]);

  const handleNewConversation = () => {
  setCurrentConversationId(null); // 设为 null，让 UI 回到初始欢迎页
  setMessages([]);
  setCurrentScene(null);
  setCurrentOutline(null);
  setSceneArray([]);
  setCurrentSceneIndex(0);
  setHasNextHint(false);
  // 强制让输入框聚焦
  if (chatInputRef.current) {
    chatInputRef.current.focus(); 
  }
};

  const handleStartNewConversation = async () => {
    try {
      // 调用后端创建会话接口
      const response = await fetch(`${API_BASE}/api/sessions/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        const newSessionId = data.session_id;
        
        // 设置当前会话ID
        setCurrentConversationId(newSessionId);
        // 刷新会话列表
        await fetchSessions();
        // 清空状态
        setMessages([]);
        setCurrentScene(null);
        setCurrentOutline(null);
        setSceneArray([]);
        setCurrentSceneIndex(0);
        setHasNextHint(false);
        
        // 延迟聚焦，确保组件已渲染
        setTimeout(() => {
          chatInputRef.current?.focus();
        }, 100);
      }
    } catch (error) {
      console.error('创建新会话失败:', error);
      // 失败时回退到原逻辑
      handleNewConversation();
      setTimeout(() => {
        chatInputRef.current?.focus();
      }, 100);
    }
  };

  const handleSelectConversation = async (id) => {
    setCurrentConversationId(id);
    // 清空当前状态，防止旧对话的教学状态残留
    setMessages([]);
    setSceneArray([]);
    setCurrentOutline(null);
    setCurrentSceneIndex(0);
    setHasNextHint(false);
    // 获取会话历史
    await fetchSessionMessages(id);
  };

  const handleDeleteConversation = async (id) => {
    try {
      const response = await fetch(`${API_BASE}/api/sessions/${id}`, {
        method: 'DELETE'
      });
      if (response.ok) {
        const sessionsRes = await fetch(`${API_BASE}/api/sessions`);
        if (sessionsRes.ok) {
          const updatedSessions = await sessionsRes.json();
          setConversations(updatedSessions);
          
          // 如果删除的是当前会话，需要切换到其他会话
          if (currentConversationId === id) {
            if (updatedSessions.length > 0) {
              // 选中第一个会话
              setCurrentConversationId(updatedSessions[0].id);
              await fetchSessionMessages(updatedSessions[0].id);
            } else {
              // 没有更多会话了，回到初始页面
              handleNewConversation();
            }
          }
        }
      }
    } catch (error) {
      console.error('删除会话失败:', error);
    }
  };

  const handleNextScene = () => {
    if (currentSceneIndex < sceneArray.length - 1) {
      // 添加过渡动画效果
      const stageElement = document.querySelector('.flex-1.flex.flex-col.bg-gray-800');
      if (stageElement) {
        stageElement.style.opacity = '0';
        stageElement.style.transition = 'opacity 0.3s ease';
      }
      
      setCurrentSceneIndex(prev => prev + 1);
      
      // 自动同步：滚动到最新状态并恢复透明度
      setTimeout(() => {
        const chatContainer = document.querySelector('.flex-1.overflow-y-auto');
        if (chatContainer) {
          chatContainer.scrollTop = chatContainer.scrollHeight;
        }
        if (stageElement) {
          stageElement.style.opacity = '1';
        }
      }, 150);
    }
  };

  const handleNextHint = (hintText) => {
    // 构造 NEXT_HINT_ACTION 消息
    const actionMessage = `[NEXT_HINT_ACTION: ${hintText}]`;
    handleSendMessage(actionMessage);
  };

  const handleSceneSelect = (index) => {
    if (index >= 0 && index < sceneArray.length) {
      setCurrentSceneIndex(index);
    }
  };

const handleSendMessage = async (text) => {
    if (!text.trim()) return;

    // 1. 构造用户消息并立即显示在 UI 上
    const userMessage = { 
      role: 'user', 
      content: text, 
      id: Date.now() 
    };
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setLoadingStage(1);

    try {
      // 2. 发起 POST 请求。注意：如果 currentConversationId 是 null，后端将识别为新会话
      const response = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: text,
          session_id: currentConversationId // 此时可能是 null
        }),
      });

      if (!response.ok) {
        throw new Error('网络响应异常');
      }

      // 3. 准备处理 SSE 流式响应
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let assistantMessageContent = '';
      let isFirstChunk = true;

      // 创建一个空的助手消息占位
      setMessages(prev => [...prev, { role: 'assistant', content: '', id: 'loading' }]);

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const jsonString = line.slice(6).trim();
            if (!jsonString) continue;

            try {
              const data = JSON.parse(jsonString);

              // --- 核心逻辑 A: 捕获后端返回的新 Session ID ---
              if (data.type === 'session_created') {
                const newId = data.session_id;
                setCurrentConversationId(newId);
                // 立即重新获取侧边栏列表，让新对话出现在左侧
                fetchSessions(); 
                continue;
              }

              // --- 核心逻辑 B: 处理内容更新 ---
              if (data.type === 'thought') {
                // 处理思考过程（可选）
                setLoadingStage(2);
              } else if (data.type === 'content') {
                assistantMessageContent += data.content;
                setMessages(prev => {
                  const newMessages = [...prev];
                  const lastIdx = newMessages.length - 1;
                  newMessages[lastIdx] = { 
                    ...newMessages[lastIdx], 
                    content: assistantMessageContent,
                    id: Date.now() // 流结束后会固定 ID
                  };
                  return newMessages;
                });
              } else if (data.type === 'scene') {
                // 更新右侧 Stage 的可视化场景数据
                setCurrentScene(data.content);
                if (data.scene_array) {
                  setSceneArray(data.scene_array);
                }
              } else if (data.type === 'outline') {
                // 更新学习大纲
                setCurrentOutline(data.content);
              }
            } catch (e) {
              console.error("解析流数据出错:", e, jsonString);
            }
          }
        }
      }
    } catch (error) {
      console.error("发送消息失败:", error);
      // 可以在此处添加错误提示 UI
    } finally {
      setIsLoading(false);
      setLoadingStage(0);
    }
  };

  // 系统核心能力演示组件（左侧区域）
  const FeatureShowcase = () => (
    <div className="flex-1 flex flex-col items-center justify-center p-8 bg-gray-900">
      <div className="max-w-2xl w-full">
        <h2 className="text-2xl font-bold mb-6 text-blue-400 text-center">系统核心能力演示</h2>
        <div className="space-y-4">
          <div className="bg-gray-800 p-5 rounded-lg border border-gray-700">
            <h3 className="font-semibold mb-3 text-blue-300 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-green-400"></span>
              知识图谱抽取
            </h3>
            <p className="text-sm text-gray-400 mb-2">基于 NetworkX 的图谱节点与关系描述：</p>
            <code className="text-xs text-gray-300 bg-gray-700 p-2 rounded block">
              {`nodes: [控制系统] → [传递函数] → [二阶系统]
links: [控制系统] ──→ [传递函数]
           └──→ [时域响应]`}
            </code>
          </div>
          <div className="bg-gray-800 p-5 rounded-lg border border-gray-700">
            <h3 className="font-semibold mb-3 text-blue-300 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-purple-400"></span>
              数学公式联动
            </h3>
            <p className="text-sm text-gray-400 mb-2">复杂控制理论公式：</p>
            <code className="text-xs text-gray-300 bg-gray-700 p-2 rounded block">
              {`G(s) = ω²/(s² + 2ζωs + ω²)
拉普拉斯变换: L{f(t)} = ∫₀^∞ f(t)e⁻ˢᵗdt`}
            </code>
          </div>
          <div className="bg-gray-800 p-5 rounded-lg border border-gray-700">
            <h3 className="font-semibold mb-3 text-blue-300 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-yellow-400"></span>
              文档智能解析
            </h3>
            <p className="text-sm text-gray-400">支持 PDF、Markdown 等文档格式的智能分析与信息提取</p>
          </div>
        </div>
      </div>
    </div>
  );

  const currentConversation = conversations.find(c => c.id === currentConversationId);

  return (
    <div className="flex h-screen bg-gray-900 text-white">
      <Sidebar
        conversations={conversations}
        currentConversationId={currentConversationId}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
        onDeleteConversation={handleDeleteConversation}
      />

      <div className="flex-1 flex">
        {/* 左侧内容区 (60%) */}
        <div className="w-3/5 flex flex-col border-r border-gray-700">
          <Navbar title={currentConversation?.title || '知识图谱智能体'} />
          {currentConversationId === null && messages.length === 0 && !isLoading ? (
            <FeatureShowcase />
          ) : (
            <Stage
              content={sceneArray.length > 0 ? sceneArray[currentSceneIndex]?.content : currentScene}
              outline={currentOutline}
              sceneArray={sceneArray}
              currentSceneIndex={currentSceneIndex}
              onSceneSelect={handleSceneSelect}
            />
          )}
        </div>

{/* 右侧交互区 (40%) */}
        <div className="w-2/5 flex flex-col bg-gray-900 border-l border-gray-700">
          {/* 判断逻辑：只有当没有 ID 且没有消息时，才显示欢迎/初始页面 */}
          {currentConversationId === null && messages.length === 0 && !isLoading ? (
            <div className="flex-1 flex flex-col overflow-y-auto">
              {/* 这里直接内联 QuickActions 的渲染逻辑，确保功能直达 */}
              <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
                <div className="w-16 h-16 bg-blue-500/20 rounded-2xl flex items-center justify-center mb-6">
                  <span className="text-3xl">🤖</span>
                </div>
                <h2 className="text-2xl font-bold text-white mb-2">知识图谱智能体</h2>
                <p className="text-gray-400 mb-8">开始探索智能文档分析之旅</p>
                
                <div className="w-full max-w-sm space-y-3">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider text-left px-1">猜你想问</p>

                  <button
                    onClick={() => handleSendMessage("帮我分析上传的 PDF 文档")}
                    className="w-full p-4 text-left bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-xl transition-all text-sm text-gray-300"
                  >
                    帮我分析上传的 PDF 文档
                  </button>

                  <button
                    onClick={() => handleSendMessage("生成一个简单的 PID 控制图谱")}
                    className="w-full p-4 text-left bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-xl transition-all text-sm text-gray-300"
                  >
                    生成一个简单的 PID 控制图谱
                  </button>

                  <button
                    onClick={() => handleStartNewConversation()}
                    className="w-full p-4 text-center bg-blue-600 hover:bg-blue-500 text-white rounded-xl transition-all font-medium"
                  >
                    开始新对话
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <>
              {/* 对话页面 */}
              <MessageList 
                messages={messages} 
                isLoading={isLoading} 
                loadingStage={loadingStage} 
                onNextHint={handleNextHint} 
              />
              <ChatInput
                ref={chatInputRef}
                onSendMessage={handleSendMessage}
                onNextScene={handleNextScene}
                hasNextHint={hasNextHint}
                currentSceneIndex={currentSceneIndex}
                totalScenes={sceneArray.length}
                nextHint={sceneArray[currentSceneIndex]?.nextHint}
              />
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;