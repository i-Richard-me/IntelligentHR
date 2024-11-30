# content_analysis_result.py
from typing import List, Literal
from pydantic import BaseModel, Field


class ContentAnalysisResult(BaseModel):
    """文本内容分析的输出格式类

    包含回复的有效性、情感倾向和是否包含敏感信息
    """
    validity: Literal["有效", "无效"] = Field(
        ..., description="回复的有效性。必须为`有效`或`无效`"
    )
    sentiment_class: Literal["正向", "中性", "负向"] = Field(
        ..., description="回复的情感倾向。可能的值为`正向`、`中性`或`负向`"
    )
    sensitive_info: Literal["是", "否"] = Field(
        ..., description="是否包含敏感信息。必须为`是`或`否`"
    )


class ContentAnalysisInput(BaseModel):
    """文本内容分析的输入格式类

    包含需要分类的文本和文本的上下文或主题
    """
    text: str = Field(..., description="需要分类的文本")
    context: str = Field(..., description="文本的上下文或主题")
