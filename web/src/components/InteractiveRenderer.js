import React from 'react';
import SceneRenderer from './SceneRenderer';

function InteractiveRenderer({ htmlContent, type = 'interactive_html' }) {
  const getSceneData = () => {
    if (!htmlContent) return null;

    if (type === 'interactive_html') {
      return htmlContent;
    }

    return htmlContent;
  };

  const data = getSceneData();

  return (
    <div className="my-4">
      <SceneRenderer data={data} type={type} />
    </div>
  );
}

export default InteractiveRenderer;