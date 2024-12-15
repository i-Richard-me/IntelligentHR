from typing import Literal
from pydantic import BaseModel, Field

# 系统提示词，专注于文本有效性判断
TEXT_VALIDITY_SYSTEM_PROMPT = """
作为一个NLP专家，你需要判断给出的{context}中的回复文本是否有效。请按照以下标准进行判断：

1. 回复有效性判断标准：
   - 若回复非常短（少于10个字），如仅包含一个词、符号或空白，判断为"无效"
   - 若回复长度超过10个字，且包含实质性内容，判断为"有效"
   - 纯表情符号、重复字符等无实际内容的回复判断为"无效"

2. 判断要点：
   - 关注文本的实际内容和长度
   - 不要考虑文本的情感倾向或是否包含敏感信息
   - 即使是负面评价，只要内容完整也视为有效回复
   - 避免对文本内容做任何主观评价，只关注其是否构成有效回复

请基于提供的回复内容做出客观判断，避免任何推测或主观解读。
直接使用"有效"或"无效"来描述判断结果。
"""

# 人类提示词模板
TEXT_VALIDITY_HUMAN_PROMPT = """
请判断以下文本是否有效：

{text}
"""


class TextValidityResult(BaseModel):
    """文本有效性检测的输出格式类

    包含对文本有效性的判断结果
    """
    validity: Literal["有效", "无效"] = Field(
        ...,
        description="文本的有效性判断结果。必须为`有效`或`无效`"
    )


class TextValidityInput(BaseModel):
    """文本有效性检测的输入格式类

    包含需要判断的文本和文本的上下文或主题
    """
    text: str = Field(..., description="需要判断有效性的文本")
    context: str = Field(..., description="文本的上下文或主题")