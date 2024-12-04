"""实体配置模型定义
"""
from sqlalchemy import Column, String, Text
from common.database.base import Base
from pydantic import BaseModel


class EntityConfig(Base):
    """实体配置表数据库模型

    存储不同实体类型的配置信息，包括验证指令、分析指令、验证指令和collection名称
    """
    __tablename__ = "entity_configs"

    entity_type = Column(String(50), primary_key=True, comment="实体类型标识符")
    display_name = Column(String(100), nullable=False, comment="实体类型展示名称")
    description = Column(Text, nullable=True, comment="实体类型描述")
    validation_instructions = Column(Text, nullable=False, comment="验证指令")
    analysis_instructions = Column(Text, nullable=False, comment="分析指令")
    verification_instructions = Column(Text, nullable=False, comment="验证指令")
    collection_name = Column(String(100), nullable=False, comment="向量数据库collection名称")

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "entity_type": self.entity_type,
            "display_name": self.display_name,
            "description": self.description,
            "validation_instructions": self.validation_instructions,
            "analysis_instructions": self.analysis_instructions,
            "verification_instructions": self.verification_instructions,
            "collection_name": self.collection_name
        }


class EntityConfigResponse(BaseModel):
    """实体配置响应模型"""
    entity_type: str
    display_name: str
    description: str | None
    validation_instructions: str
    analysis_instructions: str
    verification_instructions: str
    collection_name: str

    class Config:
        from_attributes = True