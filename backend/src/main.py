from config.config import config
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.v1 import v1_router
from modules.text_analysis.services import TaskProcessor as AnalysisTaskProcessor
from modules.text_classification.services import TaskProcessor as ClassificationTaskProcessor
from modules.data_cleaning.services import TaskProcessor as CleaningTaskProcessor
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

# 创建任务处理器实例
analysis_processor = None
classification_processor = None
cleaning_processor = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用程序生命周期管理器
    处理启动和关闭事件
    """
    # 启动时的初始化代码
    try:
        # 初始化数据库
        logger.info("正在初始化数据库...")
        init_database()

        # 启动文本分析任务处理器
        logger.info("正在启动文本分析任务处理器...")
        global analysis_processor
        analysis_processor = AnalysisTaskProcessor()
        asyncio.create_task(analysis_processor.start_processing())

        # 启动文本分类任务处理器
        logger.info("正在启动文本分类任务处理器...")
        global classification_processor
        classification_processor = ClassificationTaskProcessor()
        asyncio.create_task(classification_processor.start_processing())

        # 启动数据清洗任务处理器
        logger.info("正在启动数据清洗任务处理器...")
        global cleaning_processor
        cleaning_processor = CleaningTaskProcessor()
        asyncio.create_task(cleaning_processor.start_processing())

        logger.info("所有任务处理器初始化完成")
    except Exception as e:
        logger.error(f"应用启动失败: {str(e)}")
        raise

    yield  # 应用运行中...

    # 关闭时的清理代码
    logger.info("正在关闭应用...")
    # 这里可以添加需要的清理代码，比如关闭数据库连接等

# 创建FastAPI应用
app = FastAPI(
    title="Text Analysis API",
    description="文本分析服务API",
    version="1.0.0",
    lifespan=lifespan
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

if __name__ == "__main__":
    uvicorn.run(
        "main:app", 
        host=config.server.host,
        port=config.server.port,
        reload=config.server.reload
    )