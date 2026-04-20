import React, { useState } from 'react';

function InteractiveRenderer({ htmlContent }) {
  const [isFullscreen, setIsFullscreen] = useState(false);
  const sandbox = "allow-scripts allow-same-origin";

  const baseCss = `
    <style>
      * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
      }
      body {
        margin: 0;
        padding: 0;
        background: #1f2937;
        font-family: system-ui, -apple-system, sans-serif;
        color: #f3f4f6;
        min-height: 100vh;
      }
      html, body, #root {
        width: 100%;
        height: 100%;
      }
      /* 确保 vis.js 图表占满容器 */
      #mynetwork {
        width: 100% !important;
        height: 100% !important;
      }
    </style>
  `;

  const fullHtml = htmlContent.includes('<html') || htmlContent.includes('<body')
    ? htmlContent
    : `<!DOCTYPE html><html><head><meta charset="utf-8">${baseCss}</head><body><div id="root">${htmlContent}</div></body></html>`;

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };

  return (
    <div className={`relative rounded-lg border border-gray-600 overflow-hidden ${isFullscreen ? 'fixed inset-0 z-50' : 'my-4'}`}>
      {/* 标题栏 */}
      <div className="flex items-center justify-between bg-gray-900 px-4 py-2 border-b border-gray-700">
        <span className="text-sm font-medium text-gray-300">Graph Visualization</span>
        <button
          onClick={toggleFullscreen}
          className="text-gray-400 hover:text-white transition-colors"
          aria-label={isFullscreen ? "Exit fullscreen" : "Enter fullscreen"}
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
      {/* 图表容器 */}
      <div className={isFullscreen ? 'h-[calc(100vh-48px)]' : 'h-[500px]'}>
        <iframe
          srcDoc={fullHtml}
          sandbox={sandbox}
          style={{ width: '100%', height: '100%', border: 'none' }}
          title="Graph Visualization"
        />
      </div>
    </div>
  );
}

export default InteractiveRenderer;