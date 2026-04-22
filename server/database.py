from sqlmodel import SQLModel, Field, create_engine, Session as SQLSession
from datetime import datetime
from typing import Optional, List

# 数据库连接
DATABASE_URL = "sqlite:///./graphify.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# 创建数据库表
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

# 会话模型
class ChatSession(SQLModel, table=True):
    id: str = Field(primary_key=True, description="会话 ID")
    title: str = Field(default="新对话", description="会话标题")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")

# 消息模型
class ChatMessage(SQLModel, table=True):
    id: Optional[int] = Field(primary_key=True, default=None)
    session_id: str = Field(description="会话 ID")
    role: str = Field(description="角色 (user/assistant)")
    content: str = Field(description="消息内容")
    is_thought: bool = Field(default=False, description="是否为思考过程")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")

# 获取数据库会话
def get_db_session() -> SQLSession:
    return SQLSession(engine)
