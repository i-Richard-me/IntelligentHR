from typing import List
from pydantic import BaseModel, Field


class TextClassificationResult(BaseModel):
    """单个文本的分类结果"""
    category: str = Field(..., description="根据预定义分类规则确定的类别")


class MultiLabelTextClassificationResult(BaseModel):
    """单个文本的多标签分类结果"""
    categories: List[str] = Field(..., description="根据预定义分类规则确定的类别列表")


class TextClassificationInput(BaseModel):
    """文本分类的输入格式类"""
    text: str = Field(..., description="需要分类的文本")
    context: str = Field(..., description="文本的上下文或主题")
    categories: dict = Field(..., description="预定义的分类规则")
    is_multi_label: bool = Field(default=False, description="是否为多标签分类")