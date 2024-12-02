# modules/text_classification/workflows/text_classification_workflow.py

import os
import uuid
import asyncio
from typing import Union, List, Callable
from common.utils.llm_tools import init_language_model, LanguageModelChain
from .workflow_constants import (
    SINGLE_LABEL_CLASSIFICATION_SYSTEM_PROMPT,
    MULTI_LABEL_CLASSIFICATION_SYSTEM_PROMPT,
    TEXT_CLASSIFICATION_HUMAN_PROMPT,
)
from .text_classification_result import (
    TextClassificationResult,
    MultiLabelTextClassificationResult,
    TextClassificationInput,
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
        self.single_label_chain = LanguageModelChain(
            TextClassificationResult,
            SINGLE_LABEL_CLASSIFICATION_SYSTEM_PROMPT,
            TEXT_CLASSIFICATION_HUMAN_PROMPT,
            self.language_model,
        )()
        self.multi_label_chain = LanguageModelChain(
            MultiLabelTextClassificationResult,
            MULTI_LABEL_CLASSIFICATION_SYSTEM_PROMPT,
            TEXT_CLASSIFICATION_HUMAN_PROMPT,
            self.language_model,
        )()

    async def async_classify_text(
            self, input_data: TextClassificationInput, session_id: str = None
    ) -> Union[TextClassificationResult, MultiLabelTextClassificationResult]:
        """异步执行单个文本分类任务

        Args:
            input_data: 包含待分类文本、上下文和分类规则的输入数据
            session_id: 可选的会话ID

        Returns:
            分类结果，包含对应的类别（单标签或多标签）
        """
        session_id = session_id or str(uuid.uuid4())
        langfuse_handler = create_langfuse_handler(
            session_id, "text_classification")

        chain = self.multi_label_chain if input_data.is_multi_label else self.single_label_chain

        result = await chain.ainvoke(
            {
                "text": input_data.text,
                "context": input_data.context,
                "categories": input_data.categories,
            },
            config={"callbacks": [langfuse_handler]},
        )

        if input_data.is_multi_label:
            if isinstance(result, dict) and 'categories' in result:
                categories = result['categories']
                if isinstance(categories, str):
                    categories = [categories]
                return MultiLabelTextClassificationResult(categories=categories)
            return MultiLabelTextClassificationResult(categories=[])
        else:
            if isinstance(result, dict) and 'category' in result:
                return TextClassificationResult(category=result['category'])
            return TextClassificationResult(category="其他")

    async def async_batch_classify(
            self,
            texts: List[str],
            context: str,
            categories: dict,
            is_multi_label: bool,
            session_id: str,
            max_concurrency: int = 3,
            progress_callback: Callable[[int], None] = None,
    ) -> List[Union[TextClassificationResult, MultiLabelTextClassificationResult]]:
        """异步批量执行文本分类任务

        Args:
            texts: 待分类的文本列表
            context: 文本的上下文或主题
            categories: 预定义的分类规则
            is_multi_label: 是否为多标签分类
            session_id: 批量任务的会话ID
            max_concurrency: 最大并发数
            progress_callback: 进度回调函数，接收已完成的任务数量作为参数

        Returns:
            分类结果列表
        """
        semaphore = asyncio.Semaphore(max_concurrency)
        results = [None] * len(texts)  # 预分配结果列表
        completed_count = 0

        async def classify_with_semaphore(text: str, index: int):
            async with semaphore:
                input_data = TextClassificationInput(
                    text=text,
                    context=context,
                    categories=categories,
                    is_multi_label=is_multi_label
                )
                result = await self.async_classify_text(input_data, session_id)
                results[index] = result  # 保持原始顺序

                nonlocal completed_count
                completed_count += 1
                if progress_callback:
                    progress_callback(completed_count)

                return result

        # 创建所有任务
        tasks = [
            classify_with_semaphore(text, i)
            for i, text in enumerate(texts)
        ]

        # 使用 as_completed 处理任务
        for task in asyncio.as_completed(tasks):
            await task  # 等待每个任务完成，但不需要其结果，因为已经存储在results中

        return results


def create_langfuse_handler(session_id: str, step: str) -> CallbackHandler:
    """创建Langfuse回调处理器

    Args:
        session_id: 会话ID
        step: 处理步骤

    Returns:
        Langfuse回调处理器
    """
    return CallbackHandler(
        tags=["text_classification"],
        session_id=session_id,
        metadata={"step": step},
    )