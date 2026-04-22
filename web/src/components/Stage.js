import React from 'react';
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
          <div className="flex flex-col items-center justify-center h-full text-gray-400">
            <div className="w-10 h-10 border-4 border-gray-600 border-t-green-500 rounded-full animate-spin mb-4"></div>
            <p>正在生成...</p>
            <p className="text-sm mt-2">{sceneArray && sceneArray[currentSceneIndex]?.title ? `正在生成 ${sceneArray[currentSceneIndex].title}` : '正在生成内容'}</p>
          </div>
        ) : type && data ? (
          <SceneRenderer data={data} type={type} />
        ) : content ? (
          <div dangerouslySetInnerHTML={{ __html: content }} />
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