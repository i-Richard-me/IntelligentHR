from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum as SQLEnum, JSON
from sqlalchemy.sql import func
import enum
from common.database.base import TaskBase
from pydantic import BaseModel, Field
from typing import Dict, Optional

class TaskStatus(enum.Enum):
    """任务状态枚举类"""
    WAITING = "waiting"  # 等待处理
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消


class SensitiveDetectionTask(TaskBase):
    """敏感信息检测任务数据库模型"""
    __tablename__ = "sensitive_detection_tasks"

    task_id = Column(String(36), primary_key=True, comment="任务ID")
    user_id = Column(String(36), nullable=False, index=True, comment="用户ID")
    status = Column(SQLEnum(TaskStatus), nullable=False, default=TaskStatus.WAITING, comment="任务状态")
    context = Column(Text, nullable=False, comment="检测上下文")
    sensitive_types = Column(JSON, nullable=False, comment="敏感信息类型配置")
    source_file_url = Column(Text, nullable=False, comment="源文件URL")
    result_file_url = Column(Text, nullable=True, comment="结果文件URL")
    created_at = Column(DateTime, nullable=False, default=func.now(), comment="创建时间")
    updated_at = Column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now(), comment="更新时间"
    )
    error_message = Column(Text, nullable=True, comment="错误信息")
    total_records = Column(Integer, nullable=True, comment="总记录数")
    processed_records = Column(Integer, nullable=True, default=0, comment="已处理记录数")
    cancelled_at = Column(DateTime, nullable=True, comment="取消时间")

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
            "sensitive_types": self.sensitive_types,
            "source_file_url": self.source_file_url,
            "result_file_url": self.result_file_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "error_message": self.error_message,
            "total_records": self.total_records,
            "processed_records": self.processed_records,
            "progress": f"{(self.processed_records or 0)}/{self.total_records or '?'}",
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
        }


class TaskCreate(BaseModel):
    """任务创建请求模型"""
    context: str = Field(..., description="检测上下文")
    sensitive_types: Dict[str, dict] = Field(..., description="敏感信息类型配置")
    user_id: str = Field(..., description="用户ID")


class TaskResponse(BaseModel):
    """任务响应模型"""
    task_id: str
    user_id: str
    status: str
    context: str
    sensitive_types: Dict[str, dict]
    source_file_url: str
    result_file_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None
    total_records: Optional[int] = None
    processed_records: Optional[int] = None
    progress: str
    cancelled_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TaskCancelRequest(BaseModel):
    """任务取消请求模型"""
    reason: Optional[str] = None