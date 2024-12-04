"""数据库基础模块

提供 SQLAlchemy 基类和元类
"""
from sqlalchemy.orm import declarative_base

# 创建任务数据库的Base类
TaskBase = declarative_base()

# 创建实体配置数据库的Base类
EntityConfigBase = declarative_base()