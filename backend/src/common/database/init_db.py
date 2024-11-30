from common.database.base import Base, engine
import logging

logger = logging.getLogger(__name__)


def init_database():
    """初始化数据库

    创建所有在Base中注册的数据表
    如果表已存在，则不会重复创建
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表初始化完成")
    except Exception as e:
        logger.error(f"数据库初始化失败: {str(e)}")
        raise
