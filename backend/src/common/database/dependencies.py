"""数据库依赖模块

提供统一的数据库会话依赖注入功能
"""
from typing import Generator
from fastapi import Depends
from sqlalchemy.orm import Session
import logging
from .connections import db_connections

logger = logging.getLogger(__name__)

def get_task_db() -> Generator[Session, None, None]:
    """获取任务数据库会话

    Yields:
        Session: 数据库会话对象
    """
    db = db_connections.get_session("task_db")
    if db is None:
        raise RuntimeError("无法获取任务数据库会话")
    try:
        yield db
    finally:
        db.close()

def get_app_config_db() -> Generator[Session, None, None]:
    """获取应用配置数据库会话

    Yields:
        Session: 数据库会话对象
    """
    db = db_connections.get_session("app_config_db")
    if db is None:
        raise RuntimeError("无法获取应用配置数据库会话")
    try:
        yield db
    finally:
        db.close()

# FastAPI 依赖项
TaskDbSession = Session
EntityConfigDbSession = Session