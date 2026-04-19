import React from 'react';

function InteractiveRenderer({ htmlContent }) {
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
        padding: 16px;
        background: #1f2937;
        font-family: system-ui, -apple-system, sans-serif;
        color: #f3f4f6;
        min-height: 100vh;
      }
      html, body, #root {
        width: 100%;
        height: 100%;
      }
    </style>
  `;

  const fullHtml = htmlContent.includes('<html') || htmlContent.includes('<body')
    ? htmlContent
    : `<!DOCTYPE html><html><head><meta charset="utf-8">${baseCss}</head><body><div id="root">${htmlContent}</div></body></html>`;

  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <iframe
        srcDoc={fullHtml}
        sandbox={sandbox}
        style={{ width: '100%', height: '400px', border: 'none', borderRadius: '8px' }}
        title="Interactive Content"
      />
    </div>
  );
}

export default InteractiveRenderer;