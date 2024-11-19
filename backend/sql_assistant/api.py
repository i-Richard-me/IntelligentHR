"""
SQL助手的API入口模块。
提供HTTP接口供外部调用SQL助手服务。
"""

import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from langgraph.checkpoint.memory import MemorySaver

from backend.sql_assistant.graph.assistant_graph import run_sql_assistant
from backend.sql_assistant.utils.user_mapper import UserMapper

from langchain_core.globals import set_llm_cache
from langchain_community.cache import SQLiteCache

# set_llm_cache(SQLiteCache(database_path="data/llm_cache/langchain.db"))


if os.getenv("PHOENIX_ENABLED", "false").lower() == "true":
    from phoenix.otel import register
    from openinference.instrumentation.langchain import LangChainInstrumentor

    tracer_provider = register(
        project_name="sql_assistant",
        endpoint="http://localhost:6006/v1/traces",
    )

    LangChainInstrumentor().instrument(tracer_provider=tracer_provider)

# 创建FastAPI应用
app = FastAPI(title="SQL助手API")


class QueryRequest(BaseModel):
    """查询请求模型"""

    query: str
    session_id: Optional[str] = None
    username: Optional[str] = "anonymous"


class QueryResponse(BaseModel):
    """查询响应模型"""

    message: str
    session_id: str


checkpoint_saver = MemorySaver()
user_mapper = UserMapper()


@app.post("/api/sql-assistant", response_model=QueryResponse)
async def process_query(request: QueryRequest) -> QueryResponse:
    """处理SQL查询请求"""
    try:
        # 查询用户ID
        user_id = user_mapper.get_user_id(request.username)
        if user_id is None and request.username != "anonymous":
            raise HTTPException(
                status_code=404, detail=f"用户 {request.username} 不存在或已禁用"
            )

        # 运行SQL助手
        result = run_sql_assistant(
            query=request.query,
            thread_id=request.session_id,
            checkpoint_saver=checkpoint_saver,
            user_id=user_id,
        )

        # 获取最后一条助手消息
        messages = result.get("messages", [])
        if not messages:
            raise ValueError("未获取到助手回复")

        last_message = messages[-1].content

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
