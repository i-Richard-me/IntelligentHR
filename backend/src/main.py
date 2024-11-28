from fastapi import FastAPI
from api.v1 import v1_router
from modules.text_analysis.services import TaskProcessor
from common.utils.env_loader import load_env
import asyncio
import uvicorn
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 加载环境变量
load_env()

# 创建FastAPI应用
app = FastAPI(
    title="Text Analysis API",
    description="文本分析服务API",
    version="1.0.0"
)

# 注册V1版本的路由
app.include_router(v1_router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    """应用启动时初始化任务处理器"""
    logger.info("正在启动任务处理器...")
    processor = TaskProcessor()
    asyncio.create_task(processor.start_processing())
    logger.info("任务处理器启动完成")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)