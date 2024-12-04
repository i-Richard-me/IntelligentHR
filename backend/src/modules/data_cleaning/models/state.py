"""
状态模型定义
"""
from typing import Annotated, Dict, List, Optional
from typing_extensions import TypedDict
from enum import Enum
from langgraph.graph.message import add_messages
from .entity_config import EntityConfig

# 处理状态枚举
class ProcessingStatus(str, Enum):
    INVALID_INPUT = "无效输入"
    VALID_INPUT = "有效输入"
    IDENTIFIED = "已识别"
    UNIDENTIFIED = "未识别"
    VERIFIED = "已验证"
    UNVERIFIED = "未验证"
    ERROR = "处理错误"

# 图状态定义
class GraphState(TypedDict):
    # 消息历史,使用 add_messages 确保消息被追加而不是覆盖
    messages: Annotated[List[Dict], add_messages]
    # 实体配置信息
    entity_config: EntityConfig
    # 处理状态和结果
    status: ProcessingStatus
    original_input: str
    is_valid: bool
    is_identified: bool
    identified_entity_name: Optional[str]
    retrieved_entity_name: Optional[str]
    standard_name: Optional[str]
    final_entity_name: Optional[str]
    search_results: Optional[str]
    error_message: Optional[str]