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

# workflow_constants.py
CONTENT_ANALYSIS_SYSTEM_PROMPT = """
作为一个NLP专家，你需要评估给出的{context}中的回复文本。请按照以下步骤操作：

1. 回复有效性判断：若回复非常短，如一个词、符号或空白，判断为"无效"。超过10个字即为"有效"。
2. 情感分类：根据回复内容，将情绪归类为"正向"、"中性"或"负向"。注意回复的情感色彩、态度和情绪。对于使用反话或反讽的回复，尝试识别实际意图，并据此分类。
3. 是否敏感信息：根据回复内容，判断是否包含敏感信息，并填写"是"或"否"。敏感信息包括：
    - 提到了具体人名或具体部门名称
    - 举报、投诉所在部门的上级管理者的严重管理问题
    - 敏感信息的标准是基于员工回复中的具体内容，特别是涉及具体个人、部门名称或举报投诉管理问题的情况。

请基于提供的回复内容做出判断，避免任何推测或脑补。

要点提醒：
- 直接回答每个任务的问题。
- 使用明确的词汇"有效"或"无效"来描述回复的有效性。
- 确保情感分类结果仅为"正向"、"中性"或"负向"之一。
- 在判断是否包含敏感信息时，使用"是"或"否"来明确回答。
"""

CONTENT_ANALYSIS_HUMAN_PROMPT = """
请对以下文本进行分类：

{text}
"""

# content_analysis_workflow.py
import os
import uuid
import asyncio
from typing import List
from common.utils.llm_tools import init_language_model, LanguageModelChain
from modules.text_analysis.workflows.workflow_constants import (
    CONTENT_ANALYSIS_SYSTEM_PROMPT,
    CONTENT_ANALYSIS_HUMAN_PROMPT,
)
from modules.text_analysis.workflows.content_analysis_result import (
    ContentAnalysisResult,
    ContentAnalysisInput,
)
from langfuse.callback import CallbackHandler

class TextContentAnalysisWorkflow:
    """文本内容分析工作流程类"""

    def __init__(self):
        """初始化文本内容分析工作流程"""
        self.language_model = init_language_model(
            provider=os.getenv("SMART_LLM_PROVIDER"),
            model_name=os.getenv("SMART_LLM_MODEL"),
        )
        self.analysis_chain = LanguageModelChain(
            ContentAnalysisResult,
            CONTENT_ANALYSIS_SYSTEM_PROMPT,
            CONTENT_ANALYSIS_HUMAN_PROMPT,
            self.language_model,
        )()

    def analyze_text(
        self, input_data: ContentAnalysisInput, session_id: str = None
    ) -> ContentAnalysisResult:
        """执行单个文本内容分析任务

        Args:
            input_data: 包含待分析文本和上下文的输入数据
            session_id: 可选的会话ID

        Returns:
            分析结果，包含有效性、情感倾向和敏感信息标识
        """
        session_id = session_id or str(uuid.uuid4())
        langfuse_handler = create_langfuse_handler(session_id, "content_analysis")

        result = self.analysis_chain.invoke(
            {
                "text": input_data.text,
                "context": input_data.context,
            },
            config={"callbacks": [langfuse_handler]},
        )
        return ContentAnalysisResult(**result)

    async def async_analyze_text(
        self, input_data: ContentAnalysisInput, session_id: str = None
    ) -> ContentAnalysisResult:
        """异步执行单个文本内容分析任务

        Args:
            input_data: 包含待分析文本和上下文的输入数据
            session_id: 可选的会话ID

        Returns:
            分析结果，包含有效性、情感倾向和敏感信息标识
        """
        session_id = session_id or str(uuid.uuid4())
        langfuse_handler = create_langfuse_handler(session_id, "content_analysis")

        result = await self.analysis_chain.ainvoke(
            {
                "text": input_data.text,
                "context": input_data.context,
            },
            config={"callbacks": [langfuse_handler]},
        )
        return ContentAnalysisResult(**result)

    async def async_batch_analyze(
        self, texts: List[str], context: str, session_id: str, max_concurrency: int = 3
    ) -> List[ContentAnalysisResult]:
        """异步批量执行文本内容分析任务

        Args:
            texts: 待分析的文本列表
            context: 文本的上下文或主题
            session_id: 批量任务的会话ID
            max_concurrency: 最大并发数

        Returns:
            分析结果列表
        """
        semaphore = asyncio.Semaphore(max_concurrency)

        async def analyze_with_semaphore(text):
            async with semaphore:
                input_data = ContentAnalysisInput(text=text, context=context)
                return await self.async_analyze_text(input_data, session_id)

        tasks = [analyze_with_semaphore(text) for text in texts]
        return await asyncio.gather(*tasks)

def create_langfuse_handler(session_id: str, step: str) -> CallbackHandler:
    """创建Langfuse回调处理器

    Args:
        session_id: 会话ID
        step: 处理步骤

    Returns:
        Langfuse回调处理器
    """
    return CallbackHandler(
        tags=["content_analysis"],
        session_id=session_id,
        metadata={"step": step},
    )