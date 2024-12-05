"""数据库初始化模块

负责创建数据库表结构
"""
from pathlib import Path
import logging
from config.config import config
from .connections import db_connections
from .base import TaskBase, EntityConfigBase

logger = logging.getLogger(__name__)

def init_database() -> None:
    """初始化所有数据库
    
    - 确保数据库目录存在
    - 初始化数据库连接
    - 创建数据库表
    """
    try:

        for db_name, db_config in config.database.items():
            if db_config.url.startswith('sqlite:///'):
                db_path = Path(db_config.url.replace('sqlite:///', ''))
                db_path.parent.mkdir(parents=True, exist_ok=True)

        # 初始化任务数据库
        task_engine = db_connections.init_engine(
            "task_db",
            config.database.task_db.url,
            echo=config.database.task_db.echo,
            pool_size=config.database.task_db.pool_size,
            max_overflow=config.database.task_db.max_overflow
        )
        TaskBase.metadata.create_all(bind=task_engine)
        logger.info("任务数据库表初始化完成")

        # 初始化实体配置数据库
        entity_config_engine = db_connections.init_engine(
            "entity_config_db",
            config.database.entity_config_db.url,
            echo=config.database.entity_config_db.echo,
            pool_size=config.database.entity_config_db.pool_size,
            max_overflow=config.database.entity_config_db.max_overflow
        )
        EntityConfigBase.metadata.create_all(bind=entity_config_engine)
        logger.info("实体配置数据库表初始化完成")

    except Exception as e:
        logger.error(f"数据库初始化失败: {str(e)}")
        raise