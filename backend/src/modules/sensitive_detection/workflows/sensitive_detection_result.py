from typing import Dict, List
from pydantic import BaseModel, Field

# 系统提示词模板
SENSITIVE_DETECTION_SYSTEM_PROMPT = """
作为一个NLP专家，你需要检测给出的{context}中的文本是否包含敏感信息。请根据提供的敏感信息类型定义进行检测：

{sensitive_types_desc}

检测要求：
1. 对每种敏感类型进行独立判断
2. 只返回确实发现敏感信息的类型及其具体内容
3. 保持客观，只基于文本内容本身进行判断
4. 不要过度解读或推测
5. 如果完全没有发现任何敏感信息，应返回空列表

请保持判断的一致性，避免过度或不足的识别。只返回确实发现敏感信息的类型，准确提取涉及的具体内容。
"""

# 人类提示词模板
SENSITIVE_DETECTION_HUMAN_PROMPT = """
请对以下文本进行敏感信息检测：

文本内容：{text}

需要检测的敏感类型：
{sensitive_types}
"""


class SensitiveTypeConfig(BaseModel):
    """敏感类型配置模型"""
    name: str = Field(..., description="敏感类型名称")
    description: str = Field(..., description="敏感类型的详细描述和判定标准")


class SensitiveTypeResult(BaseModel):
    """敏感信息检测结果"""
    type_name: str = Field(..., description="发现敏感信息的类型名称")
    findings: List[str] = Field(
        ...,
        min_items=1,
        description="发现的具体敏感信息列表"
    )


class SensitiveDetectionResult(BaseModel):
    """敏感信息检测的输出格式类"""
    detections: List[SensitiveTypeResult] = Field(
        default_factory=list,
        description="敏感信息检测结果列表。仅包含发现敏感信息的类型。如果未发现任何敏感信息，则为空列表"
    )


class SensitiveDetectionInput(BaseModel):
    """敏感信息检测的输入格式类"""
    text: str = Field(
        ...,
        description="需要检测的文本内容"
    )
    context: str = Field(
        ...,
        description="文本的上下文或主题"
    )
    sensitive_types: Dict[str, SensitiveTypeConfig] = Field(
        ...,
        description="要检测的敏感信息类型配置"
    )

    def format_prompt_context(self) -> str:
        """格式化提示词中的敏感类型描述"""
        type_descriptions = []
        for key, config in self.sensitive_types.items():
            desc = [f"【{config.name}】", f"{config.description}"]
            type_descriptions.append("\n".join(desc))

        return "\n\n".join(type_descriptions)