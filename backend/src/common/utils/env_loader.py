import os
from pathlib import Path
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

def load_env() -> None:
    """加载环境变量
    
    从项目根目录的 .env 文件加载环境变量
    如果找不到 .env 文件，会尝试向上查找最近的 .env 文件
    """
    # 获取当前文件所在目录
    current_dir = Path(__file__).resolve().parent

    # 向上查找直到找到 .env 文件或到达根目录
    env_file = None
    search_dir = current_dir
    while search_dir.parent != search_dir:  # 未到达根目录
        possible_env = search_dir / '.env'
        if possible_env.is_file():
            env_file = possible_env
            break
        search_dir = search_dir.parent

    if env_file is None:
        logger.warning("未找到 .env 文件")
        return

    # 加载找到的 .env 文件
    load_dotenv(env_file)
    logger.info(f"环境变量已从 {env_file} 加载")

    # 验证关键环境变量
    required_vars = [
        "SMART_LLM_PROVIDER",
        "SMART_LLM_MODEL",
        "VECTOR_DB_HOST",
        "VECTOR_DB_PORT"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.warning(f"以下环境变量未设置: {', '.join(missing_vars)}")