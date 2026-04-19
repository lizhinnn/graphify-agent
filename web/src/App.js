import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import Navbar from './components/Navbar';
import MessageList from './components/MessageList';
import ChatInput from './components/ChatInput';

function App() {
  const [conversations, setConversations] = useState([
    { id: 1, title: '知识图谱分析示例' },
    { id: 2, title: '文档抽取任务' },
  ]);
  const [currentConversationId, setCurrentConversationId] = useState(1);
  const [messages, setMessages] = useState([
    {
      id: Date.now(),
      role: 'assistant',
      content: '你好！我是知识图谱智能体。我可以帮助你：\n\n1. **文档分析** - 分析PDF、Markdown等文档内容\n2. **实体抽取** - 从文本中提取实体和关系\n3. **知识图谱构建** - 将信息可视化为知识图谱\n\n请问有什么可以帮助你的？',
      isLoading: false
    }
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingMessageId, setLoadingMessageId] = useState(null);
  const [loadingStartTime, setLoadingStartTime] = useState(null);
  const [loadingStage, setLoadingStage] = useState(0);

  // 处理分阶段 Loading 状态
  useEffect(() => {
    let interval;
    if (isLoading && loadingStartTime) {
      interval = setInterval(() => {
        const elapsedTime = (Date.now() - loadingStartTime) / 1000;
        if (elapsedTime >= 120) {
          // 120秒超时，停止 Loading
          clearInterval(interval);
          const errorResponse = {
            id: Date.now() + 2,
            role: 'assistant',
            content: '请求超时：当前网络较慢，请耐心等待。服务器响应时间超过 120 秒，请稍后再试。',
            isLoading: false
          };
          setMessages(prev => {
            const updated = prev.filter(msg => !msg.isLoading || msg.id !== loadingMessageId);
            return [...updated, errorResponse];
          });
          setIsLoading(false);
          setLoadingMessageId(null);
          setLoadingStartTime(null);
          setLoadingStage(0);
        } else if (elapsedTime >= 15) {
          setLoadingStage(3); // 数据量较大，正在努力渲染图表...
        } else if (elapsedTime >= 5) {
          setLoadingStage(2); // 正在调用数学工具生成坐标点...
        } else {
          setLoadingStage(1); // 正在启动 AI 思考引擎...
        }
      }, 1000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isLoading, loadingStartTime, loadingMessageId]);

  const handleNewConversation = () => {
    const newId = conversations.length + 1;
    const newConversation = { id: newId, title: `新对话 ${newId}` };
    setConversations([newConversation, ...conversations]);
    setCurrentConversationId(newId);
    setMessages([]);
  };

  const handleSelectConversation = (id) => {
    setCurrentConversationId(id);
  };

  const handleSendMessage = async (content) => {
    const userMessage = { id: Date.now(), role: 'user', content, isLoading: false };
    const loadingMessage = { id: Date.now() + 1, role: 'assistant', content: '', isLoading: true };
    
    setMessages([...messages, userMessage, loadingMessage]);
    setIsLoading(true);
    setLoadingMessageId(loadingMessage.id);
    setLoadingStartTime(Date.now());
    setLoadingStage(1); // 初始状态

    try {
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: content }),
      });

      if (!response.ok) {
        const text = await response.text();
        console.log('错误响应内容:', text);
        try {
          const errorData = JSON.parse(text);
          throw new Error(errorData.detail || `请求失败: ${response.status}`);
        } catch (e) {
          throw new Error(`请求失败: ${response.status}\n${text}`);
        }
      }

      // 增加防御性逻辑，先获取文本内容
      const text = await response.text();
      console.log('响应内容:', text);
      
      // 解析 JSON
      let data;
      try {
        data = JSON.parse(text);
      } catch (e) {
        console.error('JSON 解析失败:', e);
        throw new Error(`服务器返回的数据格式错误: ${e.message}`);
      }

      const aiResponse = {
        id: Date.now() + 2,
        role: 'assistant',
        content: data.content,
        type: data.type,
        isLoading: false
      };
      
      setMessages(prev => {
        const updated = prev.filter(msg => !msg.isLoading || msg.id === loadingMessage.id);
        return [...updated, aiResponse];
      });
      // 重置状态
      setIsLoading(false);
      setLoadingMessageId(null);
      setLoadingStartTime(null);
      setLoadingStage(0);
    } catch (error) {
      console.error('调用 LLM API 失败:', error);
      // 显示错误提示
      alert(`API 请求失败: ${error.message}\n\n请确保：\n1. 后端服务已启动\n2. OPENAI_API_KEY 已正确配置\n3. 网络连接正常`);
      const errorResponse = {
        id: Date.now() + 2,
        role: 'assistant',
        content: `抱歉，发生了错误：\n\n${error.message}\n\n请确保：\n1. 后端服务已启动\n2. OPENAI_API_KEY 已正确配置\n3. 网络连接正常`,
        isLoading: false
      };
      setMessages(prev => {
        const updated = prev.filter(msg => !msg.isLoading || msg.id === loadingMessage.id);
        return [...updated, errorResponse];
      });
      // 重置状态
      setIsLoading(false);
      setLoadingMessageId(null);
      setLoadingStartTime(null);
      setLoadingStage(0);
    }
  };

  const currentConversation = conversations.find(c => c.id === currentConversationId);

  return (
    <div className="flex h-screen bg-gray-900 text-white">
      <Sidebar
        conversations={conversations}
        currentConversationId={currentConversationId}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
      />

      <div className="flex-1 flex flex-col">
        <Navbar title={currentConversation?.title || '知识图谱智能体'} />
        <MessageList messages={messages} isLoading={isLoading} loadingStage={loadingStage} />
        <ChatInput onSendMessage={handleSendMessage} />
      </div>
    </div>
  );
}

export default App;