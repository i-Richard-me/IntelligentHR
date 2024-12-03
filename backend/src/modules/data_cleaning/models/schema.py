from pydantic import BaseModel, Field
from typing import Literal

class InputValidation(BaseModel):
    """用户输入的验证结果"""
    is_valid: bool = Field(
        ...,
        description="指示用户输入是否为有效的标签（'True'）或不是（'False'）"
    )

class EntityRecognition(BaseModel):
    """从网络搜索结果中识别实体名称的结果"""
    identified_entity: str = Field(
        ...,
        description="从搜索结果中提取的标准化实体名称"
    )
    recognition_status: Literal["known", "unknown"] = Field(
        ...,
        description="指示实体名称是否成功识别（'known'）或未识别（'unknown'）"
    )

class EntityVerification(BaseModel):
    """检索到的实体名称与用户查询匹配的验证结果"""
    verification_status: Literal["verified", "unverified"] = Field(
        ...,
        description="指示检索到的实体名称是否与用户的查询相匹配（'verified'）或不匹配（'unverified'）"
    )