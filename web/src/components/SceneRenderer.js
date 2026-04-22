import React, { useState, useRef, useEffect } from 'react';

function patchHtmlForIframe(htmlContent) {
  const baseCss = `
    <style>
      * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
      }
      html, body {
        background: #111827 !important;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        color: #f3f4f6;
        min-height: 100vh;
        overflow-x: hidden;
      }
      html, body, #root {
        width: 100%;
        height: 100%;
      }
      #mynetwork {
        width: 100% !important;
        height: 100% !important;
      }
      .vis-navigation {
        position: absolute !important;
        right: 10px !important;
        bottom: 10px !important;
      }
    </style>
    <script src="https://unpkg.com/plotly.js-dist/plotly.js"></script>
    <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <link rel="stylesheet" href="https://unpkg.com/vis-network/styles/vis-network.min.css" />
  `;

  const hasHtmlTag = htmlContent.includes('<html') || htmlContent.includes('<body');
  
  if (hasHtmlTag) {
    return htmlContent
      .replace(/<head>/i, `<head>${baseCss}`)
      .replace(/<body[^>]*>/i, (match) => match.replace('>', ' style="background: #111827;">'));
  }
  
  return `<!DOCTYPE html><html><head><meta charset="utf-8">${baseCss}</head><body><div id="root">${htmlContent}</div></body></html>`;
}

function GraphRenderer({ data }) {
  const containerRef = useRef(null);
  const networkRef = useRef(null);

  useEffect(() => {
    if (!data || !containerRef.current) return;

    const container = containerRef.current;
    
    if (data.type === 'vis_network') {
      const nodes = new window.vis.DataSet(data.nodes || []);
      const edges = new window.vis.DataSet(data.edges || []);
      
      const options = data.options || {
        nodes: {
          shape: 'dot',
          size: 16,
          font: { color: '#f3f4f6', size: 14 },
          borderWidth: 2,
          shadow: true
        },
        edges: {
          width: 2,
          shadow: true,
          smooth: { type: 'continuous' }
        },
        physics: {
          stabilization: { iterations: 100 },
          barnesHut: {
            gravitationalConstant: -2000,
            springLength: 150
          }
        },
        interaction: {
          hover: true,
          tooltipDelay: 200,
          zoomView: true,
          dragView: true
        }
      };

      networkRef.current = new window.vis.Network(container, { nodes, edges }, options);
    }

    return () => {
      if (networkRef.current) {
        networkRef.current.destroy();
      }
    };
  }, [data]);

  const resetView = () => {
    if (networkRef.current) {
      networkRef.current.fit({ animation: true });
    }
  };

  return (
    <div className="relative w-full h-full bg-gray-900">
      <div ref={containerRef} className="w-full h-full" id="mynetwork" />
      <button
        onClick={resetView}
        className="absolute top-2 right-2 px-3 py-1 bg-gray-700 hover:bg-gray-600 text-white text-xs rounded transition-colors"
      >
        重置视图
      </button>
    </div>
  );
}

function MathRenderer({ data }) {
  const [error, setError] = useState(null);

  const renderMath = (tex) => {
    if (window.katex) {
      try {
        return window.katex.renderToString(tex, {
          throwOnError: false,
          displayMode: true,
          output: 'html'
        });
      } catch (e) {
        return `<div class="text-red-400">公式渲染错误: ${e.message}</div>`;
      }
    }
    return `<pre class="text-gray-300">${tex}</pre>`;
  };

  useEffect(() => {
    const loadKatex = async () => {
      if (!window.katex) {
        const script = document.createElement('script');
        script.src = 'https://unpkg.com/katex@0.16.9/dist/katex.min.js';
        script.onload = () => {
          const link = document.createElement('link');
          link.rel = 'stylesheet';
          link.href = 'https://unpkg.com/katex@0.16.9/dist/katex.min.css';
          document.head.appendChild(link);
          setError(null);
        };
        script.onerror = () => setError('KaTeX 加载失败');
        document.head.appendChild(script);
      }
    };
    loadKatex();
  }, []);

  if (error) {
    return <div className="text-red-400 p-4">{error}</div>;
  }

  if (!data || !data.content) {
    return <div className="text-gray-400 p-4">无公式内容</div>;
  }

  return (
    <div className="bg-gray-800 rounded-lg p-6 overflow-x-auto">
      <div
        className="text-lg leading-relaxed"
        dangerouslySetInnerHTML={{ __html: renderMath(data.content) }}
      />
      {data.steps && data.steps.length > 0 && (
        <div className="mt-4 space-y-2">
          {data.steps.map((step, index) => (
            <div key={index} className="flex items-start space-x-3">
              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-600 text-white text-sm flex items-center justify-center">
                {index + 1}
              </span>
              <div
                className="flex-1 text-lg"
                dangerouslySetInnerHTML={{ __html: renderMath(step) }}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function InteractiveHtmlRenderer({ data, onFullscreenToggle, isFullscreen }) {
  const sandbox = 'allow-scripts allow-same-origin allow-forms allow-modals';
  const patchedHtml = patchHtmlForIframe(data);

  return (
    <div className={`relative rounded-lg border border-gray-600 overflow-hidden ${isFullscreen ? 'fixed inset-0 z-50' : ''}`}>
      <div className="flex items-center justify-between bg-gray-900 px-4 py-2 border-b border-gray-700">
        <span className="text-sm font-medium text-gray-300">交互内容</span>
        <button
          onClick={onFullscreenToggle}
          className="text-gray-400 hover:text-white transition-colors"
          aria-label={isFullscreen ? "退出全屏" : "全屏"}
        >
          {isFullscreen ? (
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          ) : (
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 3H5a2 2 0 00-2 2v3m18 0V5a2 2 0 00-2-2h-3m0 18h3a2 2 0 002-2v-3M3 16v3a2 2 0 002 2h3" />
            </svg>
          )}
        </button>
      </div>
      <div className={isFullscreen ? 'h-[calc(100vh-48px)]' : 'h-[500px]'}>
        <iframe
          srcDoc={patchedHtml}
          sandbox={sandbox}
          style={{ width: '100%', height: '100%', border: 'none' }}
          title="Interactive Content"
        />
      </div>
    </div>
  );
}

function SceneRenderer({ data, type }) {
  const [isFullscreen, setIsFullscreen] = useState(false);

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };

  if (!data || !type) {
    return (
      <div className="flex items-center justify-center h-64 bg-gray-800 rounded-lg">
        <span className="text-gray-400">无渲染数据</span>
      </div>
    );
  }

  switch (type) {
    case 'graph_data':
      return <GraphRenderer data={data} />;
    
    case 'interactive_html':
      return <InteractiveHtmlRenderer data={data} onFullscreenToggle={toggleFullscreen} isFullscreen={isFullscreen} />;
    
    case 'math_derivation':
      return <MathRenderer data={data} />;
    
    default:
      return (
        <div className="flex items-center justify-center h-64 bg-gray-800 rounded-lg">
          <span className="text-gray-400">不支持的渲染类型: {type}</span>
        </div>
      );
  }
}

export default SceneRenderer;
export { patchHtmlForIframe };