import React, { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Copy, Check, Sparkles } from 'lucide-react';
import InteractiveChart from './InteractiveChart';

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

  // 检测并提取图表数据的函数
  const extractPlotData = (content) => {
    // 容错处理：如果 content 不是字符串，转换为字符串
    if (typeof content !== 'string') {
      return { plotData: null, textContent: JSON.stringify(content) };
    }
    
    console.log("开始检测图表数据:", content);
    
    // 1. 尝试匹配 {"plotData":...} 格式
    const plotDataRegex = /\{\s*"plotData"\s*:[\s\S]*?\}/;
    const plotDataMatch = content.match(plotDataRegex);
    console.log("正则匹配结果 (plotData):", plotDataMatch);
    
    if (plotDataMatch) {
      try {
        const parsed = JSON.parse(plotDataMatch[0]);
        console.log("解析后的对象 (plotData):", parsed);
        if (parsed.plotData && parsed.plotData.data && parsed.plotData.layout) {
          const textContent = content.replace(plotDataMatch[0], '').trim();
          return {
            plotData: {
              data: parsed.plotData.data,
              layout: parsed.plotData.layout,
              config: parsed.plotData.config
            },
            textContent
          };
        }
      } catch (e) {
        console.log("plotData 解析失败:", e);
      }
    }
    
    // 2. 尝试匹配包含 data 和 layout 的 JSON 块
    const chartRegex = /\{[\s\S]*?"data"\s*:[\s\S]*?"layout"\s*:[\s\S]*?\}/;
    const chartMatch = content.match(chartRegex);
    console.log("正则匹配结果 (chart):", chartMatch);
    
    if (chartMatch) {
      try {
        const parsed = JSON.parse(chartMatch[0]);
        console.log("解析后的对象 (chart):", parsed);
        if (parsed.data && parsed.layout) {
          const textContent = content.replace(chartMatch[0], '').trim();
          return {
            plotData: {
              data: parsed.data,
              layout: parsed.layout,
              config: parsed.config
            },
            textContent
          };
        }
      } catch (e) {
        console.log("chart 解析失败:", e);
      }
    }

    // 3. 尝试直接解析整个内容为 JSON
    try {
      const parsed = JSON.parse(content);
      console.log("解析后的对象 (整个内容):", parsed);
      
      if ((parsed.type === 'plot' || parsed.type === 'plotly') && parsed.data && parsed.layout) {
        return {
          plotData: {
            data: parsed.data,
            layout: parsed.layout,
            config: parsed.config
          },
          textContent: ''
        };
      }
      
      // 4. 支持没有 type 字段但有 data 和 layout 的格式
      if (parsed.data && parsed.layout && !parsed.type) {
        // 自动补全 type: "plot"
        return {
          plotData: {
            data: parsed.data,
            layout: parsed.layout,
            config: parsed.config,
            type: "plot"
          },
          textContent: ''
        };
      }
      
      // 5. 检查是否具备图表特征（如包含 x, y 数组）
      if (parsed.data && Array.isArray(parsed.data)) {
        const hasChartFeatures = parsed.data.some(item => 
          item.x && Array.isArray(item.x) && item.y && Array.isArray(item.y)
        );
        if (hasChartFeatures) {
          return {
            plotData: {
              data: parsed.data,
              layout: parsed.layout || {},
              config: parsed.config || {},
              type: "plot"
            },
            textContent: ''
          };
        }
      }
    } catch (e) {
      console.log("直接解析失败:", e);
      
      // 6. 尝试查找 JSON 代码块（优先处理），支持 Windows 换行符 \r\n
      const jsonMatch = content.match(/```json\r?\n([\s\S]*?)\r?\n```/m);
      console.log("正则匹配结果 (json 代码块):", jsonMatch);
      
      if (jsonMatch) {
        try {
          const parsed = JSON.parse(jsonMatch[1]);
          console.log("解析后的对象 (json 代码块):", parsed);
          
          if ((parsed.type === 'plot' || parsed.type === 'plotly') && parsed.data && parsed.layout) {
            // 彻底移除 JSON 代码块和 [PLOT_DATA] 字样
            let textContent = content.replace(jsonMatch[0], '').replace(/\[PLOT_DATA\]/g, '').trim();
            return {
              plotData: {
                data: parsed.data,
                layout: parsed.layout,
                config: parsed.config
              },
              textContent
            };
          }
          
          // 支持没有 type 字段但有 data 和 layout 的格式
          if (parsed.data && parsed.layout && !parsed.type) {
            // 彻底移除 JSON 代码块和 [PLOT_DATA] 字样
            let textContent = content.replace(jsonMatch[0], '').replace(/\[PLOT_DATA\]/g, '').trim();
            return {
              plotData: {
                data: parsed.data,
                layout: parsed.layout,
                config: parsed.config,
                type: "plot"
              },
              textContent
            };
          }
          
          // 检查是否具备图表特征
          if (parsed.data && Array.isArray(parsed.data)) {
            const hasChartFeatures = parsed.data.some(item => 
              item.x && Array.isArray(item.x) && item.y && Array.isArray(item.y)
            );
            if (hasChartFeatures) {
              // 彻底移除 JSON 代码块和 [PLOT_DATA] 字样
              let textContent = content.replace(jsonMatch[0], '').replace(/\[PLOT_DATA\]/g, '').trim();
              return {
                plotData: {
                  data: parsed.data,
                  layout: parsed.layout || {},
                  config: parsed.config || {},
                  type: "plot"
                },
                textContent
              };
            }
          }
        } catch (e2) {
          console.log("json 代码块解析失败:", e2);
        }
      }
    }
    
    console.log("未检测到图表数据，返回原内容");
    return {
      plotData: null,
      textContent: content
    };
  };

  return (
    <div className="flex-1 overflow-y-auto">
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
                <div className="flex items-center gap-3 text-gray-400">
                  <div className="flex gap-1">
                    <span className="w-2 h-2 bg-green-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-2 h-2 bg-green-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-2 h-2 bg-green-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                  <span className="text-sm">
                    {loadingStage === 1 && "正在启动 AI 思考引擎..."}
                    {loadingStage === 2 && "正在调用数学工具生成坐标点..."}
                    {loadingStage === 3 && "数据量较大，正在努力渲染图表..."}
                    {loadingStage === 0 && "正在分析中..."}
                  </span>
                </div>
              ) : (
                <>
                  <div className="prose prose-invert prose-sm max-w-none text-gray-100">
                    {(() => {
                      const { plotData, textContent } = extractPlotData(message.content);
                      return (
                        <>
                          {textContent && <ReactMarkdown>{textContent}</ReactMarkdown>}
                          {plotData && (
                            <div className="mt-4 animate-fade-in">
                              <InteractiveChart plotData={plotData} />
                            </div>
                          )}
                        </>
                      );
                    })()}
                  </div>
                  
                  {message.role === 'assistant' && (
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