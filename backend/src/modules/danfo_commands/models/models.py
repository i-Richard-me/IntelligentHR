from typing import Dict, Any, Literal, Optional, List, TypedDict
from pydantic import BaseModel, Field
from typing_extensions import NotRequired
from langgraph.graph.message import add_messages

class OutputInfo(BaseModel):
    """表示输出变量的信息"""
    var_name: str = Field(..., description="输出变量名称")
    description: str = Field(..., description="变量内容的简短描述")

class DanfoCommand(BaseModel):
    """表示要执行的 Danfo.js 命令"""
    code: str = Field(..., description="要执行的 Danfo.js 代码")
    outputs: List[OutputInfo] = Field(..., description="需要展示的输出变量信息列表")

class AssistantResponse(BaseModel):
    """表示AI助手的响应"""
    next_step: Literal["need_more_info", "execute_command", "out_of_scope"] = Field(
        ..., description="下一步操作: 需要更多信息、执行命令或超出范围"
    )
    command: Optional[DanfoCommand] = Field(
        None, description="当next_step为'execute_command'时，包含要执行的Danfo.js命令"
    )
    message: Optional[str] = Field(
        None,
        description="当next_step为'need_more_info'或'out_of_scope'时，包含给用户的消息",
    )

class GraphState(TypedDict):
    """表示图执行过程中的状态"""
    messages: NotRequired[List[Dict]]  # Langgraph需要的消息历史
    user_input: str  # 用户的原始输入
    dataframe_info: Dict[str, Dict]  # DataFrame的信息
    assistant_response: NotRequired[Optional[AssistantResponse]]  # 助手的响应
    error_message: NotRequired[Optional[str]]  # 如果发生错误，这里包含错误信息
