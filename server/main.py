from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from typing import Union, Dict, List, Optional
from server.config import settings
from fastapi import Depends
from server.database import create_db_and_tables, get_db_session, ChatSession, ChatMessage
from server.schemas import ChatRequest, SessionInfo, MessageInfo
from agent.manager import agent_manager
import json
import os
from pathlib import Path
import uuid
from datetime import datetime

app = FastAPI()

# 启动时创建数据库表
@app.on_event("startup")
def startup_event():
    create_db_and_tables()

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 前端地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatResponse(BaseModel):
    content: Union[str, Dict]
    type: str


@app.get("/")
def read_root():
    return {"message": "Graphify Agent API"}


# --- server/main.py 修改 /api/chat 接口部分 ---

@app.post("/api/chat")
async def chat(request: ChatRequest):
    try:
        if not request.message or not request.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        db = get_db_session()
        
        # --- 核心修复：处理空 Session ID ---
        actual_session_id = request.session_id
        is_new_session = False
        
        if not actual_session_id:
            actual_session_id = str(uuid.uuid4())
            new_session = ChatSession(
                id=actual_session_id,
                title=request.message[:20] + ("..." if len(request.message) > 20 else "")
            )
            db.add(new_session)
            db.commit()
            is_new_session = True
        # ------------------------------------

        async def event_generator():
            # 1. 如果是新会话，先发一个信号给前端
            if is_new_session:
                yield f"data: {json.dumps({'type': 'session_created', 'session_id': actual_session_id})}\n\n"

            # 2. 保存用户消息
            user_msg = ChatMessage(
                session_id=actual_session_id,
                role="user",
                content=request.message
            )
            db.add(user_msg)
            db.commit()

            # 3. 调用 Agent 逻辑 (保持你原有的 agent_manager 调用)
            try:
                async for chunk in agent_manager.run_stream(request.message, actual_session_id):
                    yield f"data: {json.dumps(chunk)}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def extract_content_from_chunk(chunk: str) -> str:
    """从 SSE chunk 中提取 AI 响应内容"""
    try:
        if chunk.startswith("data: "):
            data_str = chunk[6:].strip()
            if data_str:
                data = json.loads(data_str)
                if data.get("type") in ["thought", "final_answer", "module_content"]:
                    return data.get("content", "")
    except:
        pass
    return ""


@app.get("/api/sessions")
async def get_sessions():
    """获取所有会话列表"""
    db = get_db_session()
    sessions = db.query(ChatSession).order_by(ChatSession.updated_at.desc()).all()
    return [{
        "id": session.id,
        "title": session.title,
        "created_at": session.created_at,
        "updated_at": session.updated_at
    } for session in sessions]


@app.get("/api/sessions/{session_id}")
async def get_session_messages(session_id: str):
    """获取指定会话的历史消息"""
    db = get_db_session()
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at).all()
    return [{
        "id": message.id,
        "session_id": message.session_id,
        "role": message.role,
        "content": message.content,
        "is_thought": message.is_thought,
        "created_at": message.created_at
    } for message in messages]


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除指定会话"""
    db = get_db_session()
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # 删除会话的所有消息
    db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
    # 删除会话
    db.delete(session)
    db.commit()
    return {"message": "Session deleted successfully"}


@app.post("/api/sessions/create")
async def create_session():
    """创建新会话"""
    db = get_db_session()
    new_session_id = str(uuid.uuid4())
    new_session = ChatSession(
        id=new_session_id,
        title="未命名对话"
    )
    db.add(new_session)
    db.commit()
    return {"session_id": new_session_id}


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