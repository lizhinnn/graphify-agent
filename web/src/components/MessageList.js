import React, { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { Copy, Check, Sparkles } from 'lucide-react';
import InteractiveRenderer from './InteractiveRenderer';

function MessageList({ messages, isLoading, loadingStage }) {
  const messagesEndRef = useRef(null);
  const [copiedId, setCopiedId] = useState(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleCopy = async (content, messageId) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedId(messageId);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (err) {
      console.error('复制失败:', err);
    }
  };

  const renderAvatar = (role) => {
    if (role === 'user') {
      return (
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-400 to-purple-500 flex items-center justify-center text-white font-semibold text-xs flex-shrink-0">
          User
        </div>
      );
    }
    return (
      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-green-400 to-emerald-500 flex items-center justify-center text-white font-semibold text-xs flex-shrink-0">
        AI
      </div>
    );
  };

  const extractInteractiveHtml = (content) => {
    if (typeof content !== 'string') {
      return { interactiveHtmls: [], textContent: JSON.stringify(content) };
    }

    console.log("开始检测交互式HTML数据:", content);

    const interactiveHtmlRegex = /\[INTERACTIVE_HTML\]\s*```html\n([\s\S]*?)```/g;
    const matches = content.matchAll(interactiveHtmlRegex);
    
    const interactiveHtmls = [];
    let textContent = content;
    
    for (const match of matches) {
      if (match[1]) {
        const htmlCode = match[1].trim();
        interactiveHtmls.push(htmlCode);
        textContent = textContent.replace(match[0], '').trim();
        console.log("提取到的HTML代码:", htmlCode);
      }
    }

    // 如果没有找到 [INTERACTIVE_HTML] 标记，尝试匹配普通的 HTML 代码块
    if (interactiveHtmls.length === 0) {
      const simpleCodeBlockRegex = /```html\n([\s\S]*?)```/g;
      const simpleMatches = content.matchAll(simpleCodeBlockRegex);
      
      for (const match of simpleMatches) {
        if (match[1]) {
          const htmlCode = match[1].trim();
          interactiveHtmls.push(htmlCode);
          textContent = textContent.replace(match[0], '').trim();
          console.log("从普通代码块提取到的HTML:", htmlCode);
        }
      }
    }

    console.log("未检测到交互式HTML数据，返回原内容");
    return { interactiveHtmls, textContent };
  };

  const getCleanDisplayContent = (content) => {
    if (typeof content !== 'string') {
      return JSON.stringify(content);
    }

    // 检测 [INTERACTIVE_HTML] 标记
    const interactiveHtmlStart = content.indexOf('[INTERACTIVE_HTML]');
    
    // 检测可能的半截标记
    const partialInteractiveHtmlStart = content.indexOf('[INTERACTIVE');
    
    if (interactiveHtmlStart !== -1) {
      // 截取标记之前的文本
      const cleanContent = content.substring(0, interactiveHtmlStart).trim();
      // 添加占位提示
      return cleanContent + '\n\n> 📊 **图谱生成中...**';
    } else if (partialInteractiveHtmlStart !== -1) {
      // 处理半截标记的情况
      const cleanContent = content.substring(0, partialInteractiveHtmlStart).trim();
      return cleanContent + '\n\n> 📊 **图谱生成中...**';
    }

    // 没有检测到标记，返回原始文本
    return content;
  };

  return (
    <div id="message-container" className="flex-1 overflow-y-auto p-4 space-y-4">
      <div className="max-w-3xl mx-auto py-6 px-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-gray-400">
            <div className="w-16 h-16 mb-4 rounded-full bg-gradient-to-br from-green-400 to-emerald-500 flex items-center justify-center">
              <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <p className="text-lg">知识图谱智能体</p>
            <p className="text-sm mt-2">我可以帮您分析文档、构建知识图谱</p>
          </div>
        )}

        {messages.map((message, index) => (
          <div
            key={message.id || index}
            className={`flex gap-4 py-6 ${
              message.role === 'user' ? 'bg-transparent' : ''
            }`}
          >
            {renderAvatar(message.role)}
            <div className="flex-1 pt-1 min-w-0">
              <div className="font-semibold text-white mb-1 text-sm flex items-center gap-2">
                {message.role === 'user' ? '你' : '知识图谱智能体'}
                {message.role === 'assistant' && !message.isLoading && (
                  <Sparkles className="w-3 h-3 text-gray-400" />
                )}
              </div>

              {message.isLoading ? (
                <div className="prose prose-invert prose-sm max-w-none text-gray-100">
                  {(() => {
                    // 在加载中状态，使用 getCleanDisplayContent 过滤内容
                    const cleanContent = getCleanDisplayContent(message.content);
                    return (
                      <ReactMarkdown
                        remarkPlugins={[remarkMath]}
                        rehypePlugins={[rehypeKatex]}
                        components={{
                          // 确保 code 块不会误伤公式
                          code({node, inline, className, children, ...props}) {
                            return <code className={className} {...props}>{children}</code>
                          }
                        }}
                      >
                        {cleanContent}
                      </ReactMarkdown>
                    );
                  })()}
                </div>
              ) : (
                <>
                  <div className="prose prose-invert prose-sm max-w-none text-gray-100">
                    {(() => {
                      // 对于已完成的消息，仍然使用 extractInteractiveHtml 提取内容
                      // 但在显示文本时使用 getCleanDisplayContent 过滤
                      const { interactiveHtmls } = extractInteractiveHtml(message.content);
                      const cleanContent = getCleanDisplayContent(message.content);
                      return (
                        <>
                          {cleanContent && (
                            <ReactMarkdown
                              remarkPlugins={[remarkMath]}
                              rehypePlugins={[rehypeKatex]}
                              components={{
                                // 确保 code 块不会误伤公式
                                code({node, inline, className, children, ...props}) {
                                  return <code className={className} {...props}>{children}</code>
                                }
                              }}
                            >
                              {cleanContent}
                            </ReactMarkdown>
                          )}
                          {interactiveHtmls.map((htmlContent, index) => (
                            <div key={index} className="mt-4 mb-4 animate-fade-in">
                              <InteractiveRenderer htmlContent={htmlContent} />
                            </div>
                          ))}
                        </>
                      );
                    })()}
                  </div>

                  {message.role === 'assistant' && (!isLoading || index < messages.length - 1) && (
                    <div className="flex items-center justify-between mt-2 pt-2 border-t border-gray-700/50">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleCopy(message.content, message.id || index)}
                          className="flex items-center gap-1.5 px-2 py-1 text-xs text-gray-400 hover:text-white hover:bg-white/10 rounded transition-colors"
                        >
                          {copiedId === (message.id || index) ? (
                            <>
                              <Check className="w-3 h-3" />
                              <span>已复制</span>
                            </>
                          ) : (
                            <>
                              <Copy className="w-3 h-3" />
                              <span>复制</span>
                            </>
                          )}
                        </button>
                      </div>
                      <span className="text-xs text-gray-500 italic">回答已结束</span>
                    </div>
                  )}
                  {message.role === 'assistant' && isLoading && index === messages.length - 1 && (
                    <div className="mt-2 pt-2 flex items-center justify-center">
                      <span className="text-xs text-gray-400 animate-pulse">正在思考...</span>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
}

export default MessageList;