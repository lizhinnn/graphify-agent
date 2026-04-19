from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Union, Dict
from server.config import settings
from agent.manager import agent_manager
import json

app = FastAPI()

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3003"],  # 前端地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    content: Union[str, Dict]
    type: str


@app.get("/")
def read_root():
    return {"message": "Graphify Agent API"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """聊天接口，支持 ReAct 模式和工具调用"""
    try:
        response = agent_manager.run(request.message)
        # 增加打印，方便观察占位符是否被替换成功
        print(f"DEBUG: 发往前端的内容预览: {response['content'][:100]}...")
        return ChatResponse(content=response["content"], type=response["type"])
    except Exception as e:
        print(f"DEBUG: 错误信息: {str(e)}")
        raise HTTPException(status_code=500, detail=f"LLM调用失败: {str(e)}")
