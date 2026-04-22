import React, { useEffect, useRef, useState, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { Copy, Check, Sparkles, ChevronDown } from 'lucide-react';
import InteractiveRenderer from './InteractiveRenderer';
import ConceptSection from './ConceptSection';

function MessageList({ messages, isLoading, loadingStage, onNextHint }) {
  const messagesEndRef = useRef(null);
  const containerRef = useRef(null);
  const [copiedId, setCopiedId] = useState(null);
  const [isUserScrollingUp, setIsUserScrollingUp] = useState(false);
  const [showScrollToBottom, setShowScrollToBottom] = useState(false);
  const scrollThreshold = 100; // 滚动阈值

  // 节流函数
  const throttle = (func, delay) => {
    let inThrottle;
    return function() {
      const args = arguments;
      const context = this;
      if (!inThrottle) {
        func.apply(context, args);
        inThrottle = true;
        setTimeout(() => inThrottle = false, delay);
      }
    };
  };

  // 滚动监听函数
  const handleScroll = useCallback(throttle(() => {
    const container = containerRef.current;
    if (container) {
      const { scrollHeight, scrollTop, clientHeight } = container;
      // 判断用户是否向上滚动
      const isScrollingUp = scrollHeight - scrollTop > clientHeight + scrollThreshold;
      setIsUserScrollingUp(isScrollingUp);
      // 判断是否显示回到底部按钮
      setShowScrollToBottom(scrollHeight - scrollTop > clientHeight * 1.5);
    }
  }, 100), []);

  // 监听滚动事件
  useEffect(() => {
    const container = containerRef.current;
    if (container) {
      container.addEventListener('scroll', handleScroll);
      return () => container.removeEventListener('scroll', handleScroll);
    }
  }, [handleScroll]);

  // 条件滚动到底部
  useEffect(() => {
    if (!isUserScrollingUp) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isUserScrollingUp]);

  // 回到底部
  const scrollToBottom = () => {
    setIsUserScrollingUp(false);
    setShowScrollToBottom(false);
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleCopy = async (content, messageId) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedId(messageId);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (err) {
      console.error('复制失败:', err);
    }
  };

  const parseSections = (content) => {
    if (typeof content !== 'string') {
      return [{ type: 'text', content: JSON.stringify(content) }];
    }

    const sections = [];
    let lastIndex = 0;
    
    // 匹配完整的章节块 [SECTION_START: title] ... [SECTION_END]
    const sectionRegex = /\[SECTION_START:\s*([^\]]+)\]([\s\S]*?)\[SECTION_END\]/g;
    let match;
    
    while ((match = sectionRegex.exec(content)) !== null) {
      const startIndex = match.index;
      
      // 提取章节前的文本
      if (startIndex > lastIndex) {
        const preText = content.substring(lastIndex, startIndex).trim();
        if (preText) {
          sections.push({ type: 'text', content: preText });
        }
      }
      
      // 提取章节信息
      const title = match[1].trim();
      let sectionContent = match[2].trim();
      let nextHint = null;
      
      // 提取 NEXT_HINT
      const nextHintRegex = /\[NEXT_HINT:\s*([^\]]+)\]/;
      const nextHintMatch = sectionContent.match(nextHintRegex);
      if (nextHintMatch) {
        nextHint = nextHintMatch[1].trim();
        sectionContent = sectionContent.replace(nextHintMatch[0], '').trim();
      }
      
      sections.push({
        type: 'section',
        title,
        content: sectionContent,
        nextHint
      });
      
      lastIndex = startIndex + match[0].length;
    }
    
    // 提取章节后的文本
    if (lastIndex < content.length) {
      const postText = content.substring(lastIndex).trim();
      if (postText) {
        sections.push({ type: 'text', content: postText });
      }
    }
    
    // 处理不完整的章节（流式输出）
    const incompleteSectionStart = content.indexOf('[SECTION_START');
    if (incompleteSectionStart !== -1 && !content.includes('[SECTION_END]')) {
      // 如果内容以 [SECTION_START 开头但未闭合，仅显示已接收部分
      const partialText = content.substring(0, incompleteSectionStart).trim();
      if (partialText) {
        return [{ type: 'text', content: partialText }];
      }
    }
    
    return sections.length > 0 ? sections : [{ type: 'text', content }];
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
    <div id="message-container" ref={containerRef} className="flex-1 overflow-y-auto p-4 space-y-4 relative">
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
                      const { interactiveHtmls } = extractInteractiveHtml(message.content);
                      
                      // 解析章节结构
                      const sections = parseSections(message.content);
                      
                      return (
                        <>
                          {sections.map((section, index) => {
                            if (section.type === 'text') {
                              return (
                                <ReactMarkdown
                                  key={index}
                                  remarkPlugins={[remarkMath]}
                                  rehypePlugins={[rehypeKatex]}
                                  components={{
                                    code({node, inline, className, children, ...props}) {
                                      return <code className={className} {...props}>{children}</code>
                                    }
                                  }}
                                >
                                  {section.content}
                                </ReactMarkdown>
                              );
                            } else if (section.type === 'section') {
                              return (
                                <ConceptSection
                                  key={index}
                                  title={section.title}
                                  content={section.content}
                                  nextHint={section.nextHint}
                                  onNextHint={onNextHint}
                                />
                              );
                            }
                            return null;
                          })}
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

      {/* 回到最新内容按钮 */}
      {showScrollToBottom && (
        <button
          onClick={scrollToBottom}
          className="fixed bottom-6 right-6 w-12 h-12 rounded-full bg-gradient-to-br from-green-400 to-emerald-500 flex items-center justify-center text-white shadow-lg hover:shadow-xl transition-all z-10"
          aria-label="回到最新内容"
        >
          <ChevronDown className="w-5 h-5" />
        </button>
      )}
    </div>
  );
}

export default MessageList;