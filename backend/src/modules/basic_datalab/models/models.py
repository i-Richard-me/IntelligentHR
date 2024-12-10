from typing import Dict, Any, Literal, Optional, List
from typing_extensions import TypedDict, NotRequired
from pydantic import BaseModel, Field

class FileInfo(BaseModel):
    """文件信息模型"""
    dtypes: Dict[str, str]  # 列名到数据类型的映射

class PythonCommand(BaseModel):
    """表示要执行的 Python 命令"""
    code: str = Field(..., description="要执行的 Python/Pandas 代码")
    output_filename: Optional[str] = Field(
        None,
        description="如果分析结果是一个表格，必须保存结果表，并在此指定输出文件名"
    )

class AssistantResponse(BaseModel):
    """表示AI助手的响应"""
    next_step: Literal["need_more_info", "execute_command", "out_of_scope"] = Field(
        ...,
        description="下一步操作: 需要更多信息、执行命令或超出范围"
    )
    command: Optional[PythonCommand] = Field(
        None,
        description="当next_step为'execute_command'时，包含要执行的Python命令"
    )
    message: str = Field(
        ...,
        description="给用户的自然语言反馈信息，解释代码的作用或请求更多信息"
    )

class GraphState(TypedDict):
    """表示图执行过程中的状态"""
    messages: NotRequired[List[Dict]]  # Langgraph需要的消息历史
    user_input: str  # 用户的原始输入
    dataframe_info: Dict[str, Dict[str, Any]]  # DataFrame的信息
    assistant_response: NotRequired[Optional[AssistantResponse]]  # 助手的响应
    error_message: NotRequired[Optional[str]]  # 如果发生错误，这里包含错误信息

class AnalysisRequest(BaseModel):
    """Python分析命令生成请求模型"""
    user_input: str
    table_info: Dict[str, FileInfo]  # 文件名到文件信息的映射