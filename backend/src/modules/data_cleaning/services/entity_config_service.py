"""
实体配置服务模块

提供实体配置的查询和管理功能
"""
from sqlalchemy.orm import Session
from typing import Optional, List
import logging
from ..models.entity_config import EntityConfig, EntityConfigResponse

logger = logging.getLogger(__name__)


class EntityConfigService:
    """实体配置服务类"""

    def __init__(self, db: Session):
        """初始化服务

        Args:
            db: 数据库会话
        """
        self.db = db

    def get_config(self, entity_type: str) -> Optional[EntityConfig]:
        """获取实体配置

        Args:
            entity_type: 实体类型

        Returns:
            Optional[EntityConfig]: 实体配置对象，如果不存在返回None

        Raises:
            Exception: 当数据库操作失败时抛出
        """
        try:
            config = self.db.query(EntityConfig).filter(
                EntityConfig.entity_type == entity_type
            ).first()

            if not config:
                logger.warning(f"未找到实体类型配置: {entity_type}")
                return None

            return config

        except Exception as e:
            logger.error(f"获取实体配置失败: {str(e)}")
            raise

    def list_configs(self) -> List[EntityConfig]:
        """获取所有实体配置列表

        Returns:
            List[EntityConfig]: 实体配置列表

        Raises:
            Exception: 当数据库操作失败时抛出
        """
        try:
            configs = self.db.query(EntityConfig).all()
            return configs
        except Exception as e:
            logger.error(f"获取实体配置列表失败: {str(e)}")
            raise

    def is_valid_entity_type(self, entity_type: str) -> bool:
        """检查实体类型是否有效

        Args:
            entity_type: 要检查的实体类型

        Returns:
            bool: 如果实体类型存在且有效返回True，否则返回False
        """
        try:
            return self.get_config(entity_type) is not None
        except Exception:
            return False