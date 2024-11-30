from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.v1 import v1_router
from modules.text_analysis.services import TaskProcessor
from common.utils.env_loader import load_env
from common.database.init_db import init_database
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

# 添加 CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册V1版本的路由
app.include_router(v1_router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化"""
    try:
        # 初始化数据库
        logger.info("正在初始化数据库...")
        init_database()

        # 启动任务处理器
        logger.info("正在启动任务处理器...")
        processor = TaskProcessor()
        asyncio.create_task(processor.start_processing())

        logger.info("应用初始化完成")
    except Exception as e:
        logger.error(f"应用启动失败: {str(e)}")
        raise

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)