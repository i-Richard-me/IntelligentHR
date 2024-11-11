import os
import sys
from pathlib import Path

# 获取当前文件的绝对路径
current_file = Path(__file__).resolve() if "__file__" in globals() else Path.cwd()
# 获取项目根目录（当前目录的上两级）
project_root = current_file.parent
# 添加到 Python 路径
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 现在尝试导入
from utils.llm_tools import init_language_model, LanguageModelChain
from utils.env_loader import load_env

load_env()

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from langgraph.checkpoint.memory import MemorySaver

# 导入SQL助手相关代码
from backend.sql_assistant.sql_langgraph import run_sql_assistant

app = FastAPI(title="SQL助手API")

# 请求模型
class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None

# 响应模型
class QueryResponse(BaseModel):
    message: str
    session_id: str

# 创建一个全局的状态保存器
checkpoint_saver = MemorySaver()

@app.post("/api/sql-assistant", response_model=QueryResponse)
async def process_query(request: QueryRequest) -> QueryResponse:
    """处理SQL查询请求
    
    Args:
        request: 包含查询文本和可选会话ID的请求对象
        
    Returns:
        QueryResponse: 包含助手回复和会话ID的响应对象
        
    Raises:
        HTTPException: 处理失败时抛出
    """
    try:
        # 运行SQL助手
        result = run_sql_assistant(
            query=request.query,
            thread_id=request.session_id,
            checkpoint_saver=checkpoint_saver
        )
        
        # 获取最后一条助手消息
        messages = result.get("messages", [])
        if not messages:
            raise ValueError("未获取到助手回复")
            
        last_message = messages[-1].content
        
        # 返回响应
        return QueryResponse(
            message=last_message,
            session_id=request.session_id or result.get("thread_id", "")
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"处理查询失败: {str(e)}"
        )

# 健康检查接口
@app.get("/health")
async def health_check():
    return {"status": "healthy"}