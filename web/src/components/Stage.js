import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { ArrowRight, Brain, BookOpen } from 'lucide-react';
import SceneRenderer from './SceneRenderer';

function Stage({ content, outline, sceneType, sceneArray, currentSceneIndex, onSceneSelect }) {
  const parseOutline = (content) => {
    if (!content) return [];

    // 尝试解析 JSON 格式的大纲
    try {
      const outlineObj = JSON.parse(content);
      if (outlineObj.modules && Array.isArray(outlineObj.modules)) {
        return outlineObj.modules.map(module => module.name || module);
      }
    } catch (e) {
      // 如果不是 JSON，尝试解析 Markdown 格式
      const outlineMatches = content.match(/^\d+\.\s+.+$/gm);
      return outlineMatches || [];
    }

    return [];
  };

  // 优先使用 sceneArray 动态渲染步骤条，否则回退到 parseOutline
  const steps = sceneArray && sceneArray.length > 0
    ? sceneArray.map((scene, idx) => scene.title || `步骤 ${idx + 1}`)
    : parseOutline(outline);

  // 获取当前模块的加载状态
  const isCurrentModuleLoading = sceneArray && sceneArray[currentSceneIndex]?.isLoading;

  const parseContentStructure = (content) => {
    if (!content) return { title: null, body: null, nextHint: null };

    // 提取 [SECTION_START: 标题] 中的标题
    const sectionStartMatch = content.match(/\[SECTION_START:\s*([^\]]+)\]/);
    const title = sectionStartMatch ? sectionStartMatch[1].trim() : null;

    // 提取 [NEXT_HINT: 提示文字]
    const nextHintMatch = content.match(/\[NEXT_HINT:\s*([^\]]+)\]/);
    const nextHint = nextHintMatch ? nextHintMatch[1].trim() : null;

    // 提取正文内容（使用更健壮的正则表达式）
    let body = content;
    if (sectionStartMatch && nextHintMatch) {
      // 提取 [SECTION_START] 和 [NEXT_HINT] 之间的内容
      const bodyMatch = content.match(/\[SECTION_START:\s*[^\]]+\]([\s\S]*?)\[NEXT_HINT:\s*[^\]]+\]/);
      if (bodyMatch) {
        body = bodyMatch[1].replace(/\[SECTION_END\]/, '').trim();
      } else {
        // 后备方案：使用简单替换
        body = content;
        body = body.replace(sectionStartMatch[0], '');
        body = body.replace(nextHintMatch[0], '');
        body = body.replace(/\[SECTION_END\]/, '').trim();
      }
    } else {
      // 后备方案：使用简单替换
      body = content;
      if (sectionStartMatch) {
        body = body.replace(sectionStartMatch[0], '');
      }
      if (nextHintMatch) {
        body = body.replace(nextHintMatch[0], '');
      }
      body = body.replace(/\[SECTION_END\]/, '').trim();
    }

    return { title, body, nextHint };
  };

  const parseSceneContent = (content) => {
    if (!content) return { type: null, data: null };

    // 匹配新的场景标记格式 [SCENE_START: XXX] 和 [SCENE_END]
    const sceneMatch = content.match(/\[SCENE_START:\s*([^\]]+)\]([\s\S]*?)\[SCENE_END\]/m);
    if (sceneMatch) {
      const sceneType = sceneMatch[1].trim().toUpperCase();
      let sceneContent = sceneMatch[2].trim();

      switch (sceneType) {
        case 'GRAPH':
          // 提取 HTML 代码
          const htmlMatch = sceneContent.match(/```html\n([\s\S]*?)```/m);
          if (htmlMatch) {
            return { type: 'interactive_html', data: htmlMatch[1] };
          }
          return { type: 'interactive_html', data: sceneContent };
        
        case 'MATH':
          // 提取 LaTeX 代码
          const latexMatch = sceneContent.match(/```latex\n([\s\S]*?)```/m);
          if (latexMatch) {
            return { type: 'math_derivation', data: { content: latexMatch[1] } };
          }
          return { type: 'math_derivation', data: { content: sceneContent } };
        
        case 'INTERACTIVE':
          return { type: 'interactive_html', data: sceneContent };
        
        default:
          return { type: null, data: sceneContent };
      }
    }

    return { type: null, data: null };
  };

  const renderType = sceneType || 'interactive_html';
  const { type, data } = parseSceneContent(content);

  // 解析内容结构
  const { title, body, nextHint } = parseContentStructure(content);

  // 渲染骨架屏
  const renderSkeleton = () => (
    <div className="space-y-4 p-6">
      <div className="h-8 bg-gray-700 rounded w-3/4 animate-pulse"></div>
      <div className="h-4 bg-gray-700 rounded w-full animate-pulse"></div>
      <div className="h-4 bg-gray-700 rounded w-5/6 animate-pulse"></div>
      <div className="h-4 bg-gray-700 rounded w-3/4 animate-pulse"></div>
      <div className="h-4 bg-gray-700 rounded w-full animate-pulse"></div>
      <div className="h-16 bg-gray-700 rounded animate-pulse"></div>
    </div>
  );

  // 渲染 Markdown 内容
  const renderMarkdown = (mdContent) => (
    <ReactMarkdown
      remarkPlugins={[remarkMath]}
      rehypePlugins={[rehypeKatex]}
      components={{
        h1: ({ children }) => <h1 className="text-2xl font-bold text-green-400 mb-4">{children}</h1>,
        h2: ({ children }) => <h2 className="text-xl font-bold text-green-300 mb-3">{children}</h2>,
        h3: ({ children }) => <h3 className="text-lg font-bold text-green-200 mb-2">{children}</h3>,
        strong: ({ children }) => <strong className="text-white font-bold">{children}</strong>,
        em: ({ children }) => <em className="text-gray-300 italic">{children}</em>,
        ul: ({ children }) => <ul className="list-disc pl-6 space-y-1">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal pl-6 space-y-1">{children}</ol>,
        li: ({ children }) => <li className="text-gray-100">{children}</li>,
        p: ({ children }) => <p className="text-gray-100 mb-4">{children}</p>,
        blockquote: ({ children }) => (
          <blockquote className="border-l-4 border-green-500 pl-4 italic text-gray-300 my-4">
            {children}
          </blockquote>
        ),
        table: ({ children }) => (
          <table className="border-collapse w-full my-4">
            {children}
          </table>
        ),
        th: ({ children }) => (
          <th className="border border-gray-600 px-4 py-2 bg-gray-700 text-left text-white">
            {children}
          </th>
        ),
        td: ({ children }) => (
          <td className="border border-gray-600 px-4 py-2 text-gray-100">
            {children}
          </td>
        ),
        code: ({ node, inline, className, children, ...props }) => {
          if (inline) {
            return (
              <code className="bg-gray-700 text-green-300 px-1.5 py-0.5 rounded text-sm">
                {children}
              </code>
            );
          }
          return (
            <pre className="bg-gray-900 p-4 rounded-md overflow-x-auto my-4">
              <code className={className} {...props}>
                {children}
              </code>
            </pre>
          );
        },
        // 为数学公式添加边距
        math: ({ children }) => (
          <div className="my-4">
            {children}
          </div>
        ),
        inlineMath: ({ children }) => (
          <span className="text-green-300">{children}</span>
        )
      }}
    >
      {mdContent}
    </ReactMarkdown>
  );

  return (
    <div className="flex-1 flex flex-col bg-gray-800 p-4 overflow-y-auto">
      {steps.length > 0 && (
        <div className="mb-4 pb-4 border-b border-gray-700">
          <div className="flex items-center space-x-2">
            {steps.map((stepName, index) => (
              <React.Fragment key={index}>
                <div
                  className={`flex flex-col items-center justify-center min-w-[80px] h-10 rounded-full transition-all cursor-pointer hover:scale-105 ${
                    index === currentSceneIndex
                      ? 'bg-green-500 scale-110'
                      : index < currentSceneIndex
                      ? 'bg-blue-600'
                      : 'bg-gray-600'
                  } text-white`}
                  onClick={() => onSceneSelect && onSceneSelect(index)}
                >
                  {index === currentSceneIndex && isCurrentModuleLoading ? (
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  ) : (
                    <span className="text-xs font-medium">{index + 1}</span>
                  )}
                  <span className="text-[10px] mt-1 max-w-[70px] truncate" title={stepName}>
                    {stepName}
                  </span>
                </div>
                {index < steps.length - 1 && (
                  <div className={`flex-1 h-1 mx-1 ${index < currentSceneIndex ? 'bg-green-500' : 'bg-gray-600'}`}></div>
                )}
              </React.Fragment>
            ))}
          </div>
        </div>
      )}
      <div className="flex-1">
        {isCurrentModuleLoading ? (
          <div className="flex flex-col h-full">
            <div className="flex items-center mb-6">
              <Brain className="w-6 h-6 text-green-400 mr-2" />
              <h2 className="text-xl font-bold text-white">
                {sceneArray && sceneArray[currentSceneIndex]?.title ? sceneArray[currentSceneIndex].title : '正在生成内容'}
              </h2>
            </div>
            {renderSkeleton()}
          </div>
        ) : type && data ? (
          <SceneRenderer data={data} type={type} />
        ) : content ? (
          <div className="prose prose-invert max-w-none">
            {title && (
              <div className="flex items-center mb-6">
                <BookOpen className="w-6 h-6 text-green-400 mr-2" />
                <h2 className="text-2xl font-bold text-white">{title}</h2>
              </div>
            )}
            {body && renderMarkdown(body)}
            {nextHint && (
              <div className="mt-8 p-6 bg-gradient-to-r from-gray-700 to-gray-800 rounded-lg border border-gray-600">
                <h3 className="text-lg font-semibold text-green-300 mb-3 flex items-center">
                  <ArrowRight className="w-5 h-5 mr-2" />
                  下一步建议
                </h3>
                <p className="text-gray-300 mb-4">{nextHint}</p>
                <button
                  className="px-4 py-2 bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white rounded-md transition-colors flex items-center"
                  onClick={() => onSceneSelect && onSceneSelect(currentSceneIndex + 1)}
                >
                  <span>继续学习</span>
                  <ArrowRight className="w-4 h-4 ml-2" />
                </button>
              </div>
            )}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-500">
            教学内容将显示在这里
          </div>
        )}
      </div>
    </div>
  );
}

export default Stage;