from typing import Dict, Any, Literal, Optional

from pydantic import BaseModel, Field


class OperationRequest(BaseModel):
    """表示对数据操作工具的调用请求。"""

    tool_name: str = Field(..., description="要调用的工具函数名称")
    tool_args: Dict[str, Any] = Field(..., description="调用工具函数的参数")


class AssistantResponse(BaseModel):
    """表示AI助手的响应。"""

    next_step: Literal["need_more_info", "tool_use", "out_of_scope"] = Field(
        ..., description="下一步操作: 需要更多信息、使用工具或超出范围"
    )
    operation: Optional[OperationRequest] = Field(
        None, description="当next_step为'tool_use'时，包含要执行的操作"
    )
    message: Optional[str] = Field(
        None,
        description="当next_step为'need_more_info'或'out_of_scope'时，包含给用户的消息",
    )
