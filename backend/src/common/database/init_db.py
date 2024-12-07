"""数据库初始化模块

负责创建数据库和表结构
"""
from pathlib import Path
import logging
from config.config import config
from .connections import db_connections
from .base import TaskBase, EntityConfigBase, CollectionBase  # 更新导入
from sqlalchemy import create_engine, text
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)

def create_database_if_not_exists(url: str) -> None:
    """创建数据库（如果不存在）

    Args:
        url: 数据库连接URL
    """
    parsed = urlparse(url)
    if parsed.scheme.startswith('mysql'):
        # 提取数据库名称
        database = parsed.path.strip('/')

        # 解析查询参数
        query_params = parse_qs(parsed.query)
        charset = query_params.get('charset', ['utf8mb4'])[0]

        # 创建没有指定数据库的连接URL
        root_url = f"{parsed.scheme}://{parsed.username}:{parsed.password}@{parsed.hostname}:{parsed.port or 3306}"

        # 连接到MySQL服务器（不指定数据库）
        engine = create_engine(
            root_url,
            isolation_level="AUTOCOMMIT",
            pool_pre_ping=True
        )

        try:
            # 创建数据库
            with engine.connect() as conn:
                conn.execute(
                    text(f"CREATE DATABASE IF NOT EXISTS `{database}` CHARACTER SET {charset} COLLATE {charset}_unicode_ci")
                )
                logger.info(f"确保数据库存在: {database}")
        finally:
            engine.dispose()

def init_database() -> None:
    """初始化所有数据库

    - 确保数据库存在
    - 初始化数据库连接
    - 创建数据库表
    """
    try:
        # 确保数据库存在
        for db_name, db_config in config.database.items():
            if db_config.url.startswith('sqlite:///'):
                db_path = Path(db_config.url.replace('sqlite:///', ''))
                db_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                create_database_if_not_exists(db_config.url)

        # 初始化任务数据库
        task_engine = db_connections.init_engine(
            "task_db",
            config.database.task_db.url,
            echo=config.database.task_db.echo,
            pool_size=config.database.task_db.pool_size,
            max_overflow=config.database.task_db.max_overflow,
        )
        TaskBase.metadata.create_all(bind=task_engine)
        logger.info("任务数据库表初始化完成")

        # 初始化实体配置数据库
        entity_config_engine = db_connections.init_engine(
            "app_config_db",
            config.database.app_config_db.url,
            echo=config.database.app_config_db.echo,
            pool_size=config.database.app_config_db.pool_size,
            max_overflow=config.database.app_config_db.max_overflow,
        )
        EntityConfigBase.metadata.create_all(bind=entity_config_engine)
        logger.info("实体配置数据库表初始化完成")

        # 初始化Collection配置数据库（新增）
        collection_engine = db_connections.init_engine(
            "app_config_db",
            config.database.app_config_db.url,
            echo=config.database.app_config_db.echo,
            pool_size=config.database.app_config_db.pool_size,
            max_overflow=config.database.app_config_db.max_overflow,
        )
        CollectionBase.metadata.create_all(bind=collection_engine)
        logger.info("Collection配置数据库表初始化完成")

    except Exception as e:
        logger.error(f"数据库初始化失败: {str(e)}")
        raise
