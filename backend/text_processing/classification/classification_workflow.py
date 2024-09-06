import os
import uuid
import asyncio
from typing import List
from utils.llm_tools import init_language_model, LanguageModelChain
from backend.text_processing.classification.classification_core import (
    ClassificationResult,
    ClassificationInput,
    CLASSIFICATION_SYSTEM_PROMPT,
    CLASSIFICATION_HUMAN_PROMPT,
)
from langfuse.callback import CallbackHandler


class TextClassificationWorkflow:
    """文本分类工作流程类"""

    def __init__(self):
        """初始化文本分类工作流程"""
        self.language_model = init_language_model(
            provider=os.getenv("SMART_LLM_PROVIDER"),
            model_name=os.getenv("SMART_LLM_MODEL"),
        )
        self.classification_chain = LanguageModelChain(
            ClassificationResult,
            CLASSIFICATION_SYSTEM_PROMPT,
            CLASSIFICATION_HUMAN_PROMPT,
            self.language_model,
        )()

    def classify_text(
        self, input_data: ClassificationInput, session_id: str = None
    ) -> ClassificationResult:
        """
        执行单个文本分类任务

        Args:
            input_data: 包含待分类文本和上下文的输入数据
            session_id: 可选的会话ID

        Returns:
            分类结果，包含有效性、情感倾向和敏感信息标识
        """
        session_id = session_id or str(uuid.uuid4())
        langfuse_handler = create_langfuse_handler(
            session_id, "sentiment_analysis_and_labeling"
        )

        result = self.classification_chain.invoke(
            {
                "text": input_data.text,
                "context": input_data.context,
            },
            config={"callbacks": [langfuse_handler]},
        )
        return ClassificationResult(**result)

    def batch_classify(
        self, texts: List[str], context: str, session_id: str
    ) -> List[ClassificationResult]:
        """
        批量执行文本分类任务

        Args:
            texts: 待分类的文本列表
            context: 文本的上下文或主题
            session_id: 批量任务的会话ID

        Returns:
            分类结果列表
        """
        return [
            self.classify_text(
                ClassificationInput(text=text, context=context), session_id
            )
            for text in texts
        ]

    async def async_classify_text(
        self, input_data: ClassificationInput, session_id: str = None
    ) -> ClassificationResult:
        """
        异步执行单个文本分类任务

        Args:
            input_data: 包含待分类文本和上下文的输入数据
            session_id: 可选的会话ID

        Returns:
            分类结果，包含有效性、情感倾向和敏感信息标识
        """
        session_id = session_id or str(uuid.uuid4())
        langfuse_handler = create_langfuse_handler(
            session_id, "sentiment_analysis_and_labeling"
        )

        result = await self.classification_chain.ainvoke(
            {
                "text": input_data.text,
                "context": input_data.context,
            },
            config={"callbacks": [langfuse_handler]},
        )
        return ClassificationResult(**result)

    async def async_batch_classify(
        self, texts: List[str], context: str, session_id: str, max_concurrency: int = 3
    ) -> List[ClassificationResult]:
        """
        异步批量执行文本分类任务

        Args:
            texts: 待分类的文本列表
            context: 文本的上下文或主题
            session_id: 批量任务的会话ID
            max_concurrency: 最大并发数

        Returns:
            分类结果列表
        """
        semaphore = asyncio.Semaphore(max_concurrency)

        async def classify_with_semaphore(text):
            async with semaphore:
                input_data = ClassificationInput(text=text, context=context)
                return await self.async_classify_text(input_data, session_id)

        tasks = [classify_with_semaphore(text) for text in texts]
        return await asyncio.gather(*tasks)


def create_langfuse_handler(session_id: str, step: str) -> CallbackHandler:
    """
    创建Langfuse回调处理器

    Args:
        session_id: 会话ID
        step: 处理步骤

    Returns:
        Langfuse回调处理器
    """
    return CallbackHandler(
        tags=["sentiment_analysis_and_labeling"],
        session_id=session_id,
        metadata={"step": step},
    )
