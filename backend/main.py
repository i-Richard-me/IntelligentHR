import os
import sys
import argparse
from fastapi import FastAPI
import uvicorn
import logging

# 将项目根目录添加到 Python 路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.text_processing.translation.translation_service import (
    router as translation_router,
)
from backend.text_processing.translation.translation_service import (
    initialize_translation_service,
    get_translation_service_status,
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化 FastAPI 应用
app = FastAPI(title="智能HR助手 API")

# 添加翻译服务路由
app.include_router(translation_router)


@app.on_event("startup")
async def startup_event():
    if args.task in ["translation", "all"]:
        logger.info("正在初始化翻译服务...")
        initialize_translation_service()


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "translation_service": get_translation_service_status(),
        # 其他服务的状态检查可以在这里添加
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="启动智能HR助手API")
    parser.add_argument(
        "--task",
        type=str,
        choices=["translation", "all"],
        default="all",
        help="选择要启动的任务：translation 或 all",
    )
    args = parser.parse_args()

    uvicorn.run(app, host="0.0.0.0", port=8765)
