from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum as SQLEnum, JSON, Boolean
from sqlalchemy.sql import func
import enum
from common.database.base import Base
from pydantic import BaseModel, Field

class TaskStatus(enum.Enum):
    """任务状态枚举类"""
    WAITING = "waiting"      # 等待处理
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"    # 已完成
    FAILED = "failed"         # 失败

class ClassificationTask(Base):
    """文本分类任务数据库模型"""
    __tablename__ = "classification_tasks"

    task_id = Column(String(36), primary_key=True, comment="任务ID")
    user_id = Column(String(36), nullable=False, index=True, comment="用户ID")
    status = Column(SQLEnum(TaskStatus), nullable=False, default=TaskStatus.WAITING, comment="任务状态")
    context = Column(Text, nullable=False, comment="分类上下文")
    categories = Column(JSON, nullable=False, comment="预定义的分类规则")
    is_multi_label = Column(Boolean, nullable=False, default=False, comment="是否为多标签分类")
    source_file_url = Column(Text, nullable=False, comment="源文件URL")
    result_file_url = Column(Text, nullable=True, comment="结果文件URL")
    created_at = Column(DateTime, nullable=False, default=func.now(), comment="创建时间")
    updated_at = Column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now(), comment="更新时间"
    )
    error_message = Column(Text, nullable=True, comment="错误信息")
    total_records = Column(Integer, nullable=True, comment="总记录数")
    processed_records = Column(Integer, nullable=True, default=0, comment="已处理记录数")

    def to_dict(self) -> dict:
        """将模型转换为字典
        
        Returns:
            dict: 包含任务信息的字典
        """
        return {
            "task_id": self.task_id,
            "user_id": self.user_id,
            "status": self.status.value,
            "context": self.context,
            "categories": self.categories,
            "is_multi_label": self.is_multi_label,
            "source_file_url": self.source_file_url,
            "result_file_url": self.result_file_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "error_message": self.error_message,
            "total_records": self.total_records,
            "processed_records": self.processed_records,
            "progress": f"{(self.processed_records or 0)}/{self.total_records or '?'}",
        }

class TaskCreate(BaseModel):
    """任务创建请求模型"""
    context: str = Field(..., description="分类任务的上下文或主题")
    user_id: str = Field(..., description="用户ID")
    categories: dict = Field(..., description="预定义的分类规则")
    is_multi_label: bool = Field(default=False, description="是否为多标签分类")

class TaskResponse(BaseModel):
    """任务响应模型"""
    task_id: str
    user_id: str
    status: str
    context: str
    categories: dict
    is_multi_label: bool
    source_file_url: str
    result_file_url: str | None
    created_at: datetime
    updated_at: datetime
    error_message: str | None
    total_records: int | None
    processed_records: int | None
    progress: str

    class Config:
        from_attributes = True