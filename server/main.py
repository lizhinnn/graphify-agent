from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from typing import Union, Dict
from server.config import settings
from agent.manager import agent_manager
import json
import os
from pathlib import Path

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


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """聊天接口，支持 ReAct 模式和工具调用，返回流式响应"""
    try:
        # 使用流式响应
        return StreamingResponse(
            agent_manager.run_stream(request.message),
            media_type="text/event-stream"
        )
    except Exception as e:
        print(f"DEBUG: 错误信息: {str(e)}")
        raise HTTPException(status_code=500, detail=f"LLM调用失败: {str(e)}")


@app.get("/api/graphs/{filename}")
async def get_graph_file(filename: str):
    """获取图谱文件"""
    try:
        # 构建文件路径
        graph_path = Path("storage/graphs") / filename
        
        # 检查文件是否存在
        if not graph_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        # 返回文件
        return FileResponse(graph_path)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error accessing graph file: {str(e)}")