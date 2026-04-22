import React, { useState } from 'react';
import { Plus, Trash2, MessageSquare } from 'lucide-react';

function Sidebar({ conversations, currentConversationId, onSelectConversation, onNewConversation, onDeleteConversation }) {
  return (
    <div className="w-64 bg-chatgpt-sidebar h-full flex flex-col">
      <div className="p-3">
        <button
          onClick={onNewConversation}
          className="w-full flex items-center gap-2 px-4 py-3 rounded-md border border-white/10 hover:bg-white/5 transition-colors text-white"
        >
          <Plus className="w-5 h-5" />
          新建对话
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-3 pb-3">
        <div className="space-y-1">
          {conversations.map((conv) => (
            <div
              key={conv.id}
              className="relative group"
            >
              <button
                onClick={() => onSelectConversation(conv.id)}
                className={`w-full text-left px-4 py-3 rounded-md transition-colors text-sm truncate flex items-center gap-2 ${
                  currentConversationId === conv.id
                    ? 'bg-white/10 text-white border-l-4 border-blue-500'
                    : 'text-gray-300 hover:bg-white/5'
                }`}
              >
                <MessageSquare className="w-4 h-4 flex-shrink-0" />
                {conv.title}
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  if (onDeleteConversation) {
                    onDeleteConversation(conv.id);
                  }
                }}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-md bg-red-500/80 hover:bg-red-500 text-white opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <Trash2 className="w-3 h-3" />
              </button>
            </div>
          ))}
        </div>
      </div>

      <div className="p-3 border-t border-white/10">
        <div className="flex items-center gap-3 px-4 py-2 text-gray-300 text-sm">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-green-400 to-blue-500 flex items-center justify-center text-white font-semibold text-xs">
            User
          </div>
          <span className="truncate">用户</span>
        </div>
      </div>
    </div>
  );
}

export default Sidebar;