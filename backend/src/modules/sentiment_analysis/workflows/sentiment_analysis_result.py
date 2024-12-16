from typing import Literal
from pydantic import BaseModel, Field

# 系统提示词，专注于情感分析任务
SENTIMENT_ANALYSIS_SYSTEM_PROMPT = """
作为一个NLP专家，你需要分析给出的{context}中的文本情感倾向。请按照以下步骤操作：

1. 仔细阅读文本内容，理解其表达的情感和态度
2. 分析文本中的情感指示词、语气词、标点符号等情感标记
3. 考虑文本的整体语境和表达方式
4. 注意识别反讽、比喻等可能影响情感判断的修辞手法
5. 将情感分类为以下三类之一：
   - "正向"：表达满意、赞同、喜悦、期待等正面情感
   - "中性"：陈述事实，没有明显情感倾向，或正负情感并存
   - "负向"：表达不满、反对、失望、愤怒等负面情感

要点提醒：
- 保持客观，基于文本内容进行判断
- 不要被单个词语或标点误导，要考虑整体表达
- 对于反讽和比喻，要理解其真实表达的情感
- 只输出"正向"、"中性"、"负向"三种结果之一
"""

# 人类提示词模板
SENTIMENT_ANALYSIS_HUMAN_PROMPT = """
请分析以下文本的情感倾向：

{text}
"""


class SentimentAnalysisResult(BaseModel):
    """情感分析的输出格式类

    包含文本的情感分类结果
    """
    sentiment_class: Literal["正向", "中性", "负向"] = Field(
        ...,
        description="文本的情感倾向分类结果。可能的值为`正向`、`中性`或`负向`"
    )


class SentimentAnalysisInput(BaseModel):
    """情感分析的输入格式类

    包含需要分析的文本和文本的上下文或主题
    """
    text: str = Field(..., description="需要分析情感的文本")
    context: str = Field(..., description="文本的上下文或主题")