import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { ChevronDown, ChevronUp, ArrowRight } from 'lucide-react';

function ConceptSection({ title, content, nextHint, onNextHint }) {
  const [isExpanded, setIsExpanded] = useState(true);

  const toggleExpand = () => {
    setIsExpanded(!isExpanded);
  };

  const handleNextHint = () => {
    if (onNextHint && nextHint) {
      onNextHint(nextHint);
    }
  };

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg overflow-hidden mb-4">
      {/* 标题栏 */}
      <div 
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-750 transition-colors"
        onClick={toggleExpand}
      >
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          {isExpanded ? (
            <ChevronUp className="w-5 h-5 text-gray-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-gray-400" />
          )}
          {title}
        </h3>
      </div>

      {/* 内容区域 */}
      {isExpanded && (
        <div className="p-4 border-t border-gray-700">
          <div className="prose prose-invert prose-sm max-w-none text-gray-100">
            <ReactMarkdown
              remarkPlugins={[remarkMath]}
              rehypePlugins={[rehypeKatex]}
              components={{
                code({node, inline, className, children, ...props}) {
                  return <code className={className} {...props}>{children}</code>
                }
              }}
            >
              {content}
            </ReactMarkdown>
          </div>

          {/* 下一个提示按钮 */}
          {nextHint && (
            <div className="mt-4 pt-4 border-t border-gray-700">
              <button
                onClick={handleNextHint}
                className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white rounded-md transition-colors"
              >
                <span>{nextHint}</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default ConceptSection;