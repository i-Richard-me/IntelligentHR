"""
SQL助手的API入口模块。
提供HTTP接口供外部调用SQL助手服务。
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from langgraph.checkpoint.memory import MemorySaver

from backend.sql_assistant.graph.assistant_graph import run_sql_assistant

from langchain_core.globals import set_llm_cache
from langchain_community.cache import SQLiteCache

set_llm_cache(SQLiteCache(database_path="data/llm_cache/langchain.db"))

# 创建FastAPI应用
app = FastAPI(title="SQL助手API")


class QueryRequest(BaseModel):
    """查询请求模型"""

    query: str
    session_id: Optional[str] = None


class QueryResponse(BaseModel):
    """查询响应模型"""

    message: str
    session_id: str


# 创建全局状态保存器
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
            checkpoint_saver=checkpoint_saver,
        )

        # 获取最后一条助手消息
        messages = result.get("messages", [])
        if not messages:
            raise ValueError("未获取到助手回复")

        last_message = messages[-1].content

        # 返回响应
        return QueryResponse(
            message=last_message,
            session_id=request.session_id or result.get("thread_id", ""),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理查询失败: {str(e)}")


@app.get("/health")
async def health_check():
    """健康检查接口

    Returns:
        Dict: 服务状态信息
    """
    return {"status": "healthy"}
