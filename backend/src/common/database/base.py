"""数据库基础模块

提供 SQLAlchemy 基类和元类
"""
from sqlalchemy.orm import declarative_base
from sqlalchemy import MetaData

# 为所有表添加默认的字符集和排序规则配置
naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

# 创建支持 MySQL 的元数据对象
task_metadata = MetaData(naming_convention=naming_convention)
entity_config_metadata = MetaData(naming_convention=naming_convention)
collection_metadata = MetaData(naming_convention=naming_convention)

# 创建各数据库的Base类
TaskBase = declarative_base(metadata=task_metadata)
EntityConfigBase = declarative_base(metadata=entity_config_metadata)
CollectionBase = declarative_base(metadata=collection_metadata)

# 添加通用表参数方法
def get_table_args():
    """获取通用的表参数配置"""
    return {
        'mysql_engine': 'InnoDB',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_unicode_ci'
    }