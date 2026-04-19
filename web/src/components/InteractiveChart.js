import React from 'react';
// 直接导入 react-plotly.js，它会自动使用 plotly.js-dist-min
import Plot from 'react-plotly.js';

function InteractiveChart({ plotData }) {
  console.log("即将渲染的图表数据:", plotData);
  
  // 后端返回的结构已经是标准的 Plotly 格式 {data: [...], layout: {...}}
  const chartData = plotData.data;
  
  if (!plotData || !chartData || !plotData.layout) {
    return (
      <div className="bg-gray-800 rounded-lg p-4 text-gray-400">
        图表数据无效
      </div>
    );
  }

  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <Plot
        data={chartData}
        layout={plotData.layout}
        config={plotData.config || {
          responsive: true,
          displayModeBar: true,
          scrollZoom: true
        }}
        style={{ width: '100%', height: '400px' }}
        useResizeHandler={true}
      />
    </div>
  );
}

export default InteractiveChart;
