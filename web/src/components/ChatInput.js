import React, { useState, useEffect, useRef, forwardRef, useImperativeHandle } from 'react';
import { Send, ChevronRight } from 'lucide-react';

const ChatInput = forwardRef(({ onSendMessage, onNextScene, hasNextHint, currentSceneIndex, totalScenes, nextHint }, ref) => {
  const [input, setInput] = useState('');
  const textareaRef = useRef(null);

  // 暴露聚焦方法给父组件
  useImperativeHandle(ref, () => ({
    focus: () => {
      textareaRef.current?.focus();
    }
  }));

  useEffect(() => {
    const handleQuickAction = (e) => {
      setInput(e.detail);
      // 快速操作时自动聚焦到输入框
      textareaRef.current?.focus();
    };
    window.addEventListener('quickAction', handleQuickAction);
    return () => window.removeEventListener('quickAction', handleQuickAction);
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    console.log('handleSubmit called:', input);
    if (input.trim() && onSendMessage) {
      console.log('onSendMessage called with:', input);
      onSendMessage(input);
      setInput('');
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleNextScene = () => {
    if (onNextScene && hasNextHint) {
      onNextScene();
    }
  };

  return (
    <div className="border-t border-white/10 bg-gray-800">
      <div className="max-w-3xl mx-auto px-4 py-4">
        <form onSubmit={handleSubmit} className="relative">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入消息..."
            rows={1}
            className="w-full bg-chatgpt-input-bg border border-chatgpt-border rounded-lg px-4 py-3 pr-12 text-white placeholder-gray-400 resize-none focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/50 transition-all"
            style={{ minHeight: '48px', maxHeight: '200px' }}
          />
          <button
            type="submit"
            disabled={!input.trim()}
            className="absolute right-2 bottom-2 p-2 rounded-md bg-green-600 hover:bg-green-500 disabled:bg-gray-600 disabled:cursor-not-allowed transition-colors"
          >
            <Send className="w-5 h-5 text-white" />
          </button>
        </form>
        {hasNextHint && totalScenes > 0 && (
          <div className="mt-3 flex items-center justify-between">
            <div className="text-sm text-gray-400">
              环节 {currentSceneIndex + 1} / {totalScenes}
            </div>
            <button
              onClick={handleNextScene}
              className={`flex items-center gap-2 px-4 py-2 rounded-md transition-colors ${hasNextHint ? 'bg-blue-600 hover:bg-blue-500' : 'bg-gray-600 cursor-not-allowed'}`}
              disabled={!hasNextHint}
            >
              <span>{nextHint || '下一环节'}</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        )}
        <p className="text-center text-xs text-gray-500 mt-2">
          按 Enter 发送，Shift + Enter 换行
        </p>
      </div>
    </div>
  );
});

ChatInput.displayName = 'ChatInput';

export default ChatInput;