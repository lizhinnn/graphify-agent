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
    setLoadingStage(1);

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

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let aiResponseContent = '';
      let aiResponseId = Date.now() + 2;
      let isReceivingFinal = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        while (buffer.includes('\n')) {
          const lineEnd = buffer.indexOf('\n');
          let line = buffer.substring(0, lineEnd);
          buffer = buffer.substring(lineEnd + 1);

          if (line.endsWith('\r')) {
            line = line.slice(0, -1);
          }

          if (line.startsWith('data: ')) {
            const jsonStr = line.replace(/^data: /, '');

            if (!jsonStr || jsonStr.trim() === '') continue;

            try {
              const data = JSON.parse(jsonStr);

              if (data.type === 'thought') {
                // 保存原始内容用于最终答案
                aiResponseContent += data.content;
                // 在加载中状态，过滤掉 [INTERACTIVE_HTML] 部分，只显示纯文本
                let displayContent = aiResponseContent;
                if (typeof displayContent === 'string') {
                  // 过滤掉 [INTERACTIVE_HTML] 标记及其内容
                  displayContent = displayContent.replace(/\[INTERACTIVE_HTML\]\s*```html\n[\s\S]*?```/m, '').trim();
                  // 过滤掉普通 HTML 代码块
                  displayContent = displayContent.replace(/```html\n[\s\S]*?```/m, '').trim();
                }
                setMessages(prev => {
                  const updated = prev.map(msg =>
                    msg.id === loadingMessage.id
                      ? { ...msg, content: displayContent, isLoading: true }
                      : msg
                  );
                  return updated;
                });
              } else if (data.type === 'final_answer') {
                isReceivingFinal = true;
                aiResponseContent = data.content;
                
                setMessages(prev => {
                  const updated = prev.map(msg =>
                    msg.id === loadingMessage.id
                      ? { ...msg, content: aiResponseContent, isLoading: false }
                      : msg
                  );
                  return updated;
                });
              }
            } catch (e) {
              console.error('解析 SSE 数据失败:', e.message, 'Raw:', jsonStr);
            }
          }
        }
      }

      setIsLoading(false);
      setLoadingMessageId(null);
      setLoadingStartTime(null);
      setLoadingStage(0);
    } catch (error) {
      console.error('调用 LLM API 失败:', error);
      alert(`API 请求失败: ${error.message}\n\n请确保：\n1. 后端服务已启动\n2. OPENAI_API_KEY 已正确配置\n3. 网络连接正常`);
      const errorResponse = {
        id: Date.now() + 2,
        role: 'assistant',
        content: `抱歉，发生了错误：\n\n${error.message}\n\n请确保：\n1. 后端服务已启动\n2. OPENAI_API_KEY 已正确配置\n3. 网络连接正常`,
        isLoading: false
      };
      setMessages(prev => {
        const updated = prev.filter(msg => !msg.isLoading || msg.id !== loadingMessage.id);
        return [...updated, errorResponse];
      });
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