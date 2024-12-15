import uuid
import asyncio
from typing import List, Callable
from config.config import config
from common.utils.llm_tools import init_language_model, LanguageModelChain
from .text_validity_result import (
    TextValidityResult,
    TextValidityInput,
    TEXT_VALIDITY_SYSTEM_PROMPT,
    TEXT_VALIDITY_HUMAN_PROMPT,
)
from langfuse.callback import CallbackHandler


def create_langfuse_handler(session_id: str, step: str) -> CallbackHandler:
    """创建Langfuse回调处理器

    Args:
        session_id: 会话ID
        step: 处理步骤

    Returns:
        Langfuse回调处理器
    """
    return CallbackHandler(
        tags=["text_validity"],
        session_id=session_id,
        metadata={"step": step},
    )


class TextValidityWorkflow:
    """文本有效性检测工作流程类"""

    def __init__(self):
        """初始化文本有效性检测工作流程"""
        self.language_model = init_language_model(
            provider=config.text_validity.llm_provider,
            model_name=config.text_validity.llm_model,
            temperature=config.text_validity.temperature,
        )
        self.validity_chain = LanguageModelChain(
            TextValidityResult,
            TEXT_VALIDITY_SYSTEM_PROMPT,
            TEXT_VALIDITY_HUMAN_PROMPT,
            self.language_model,
        )()

    async def async_check_validity(
            self, input_data: TextValidityInput, session_id: str = None
    ) -> TextValidityResult:
        """异步执行单个文本有效性检测任务

        Args:
            input_data: 包含待检测文本和上下文的输入数据
            session_id: 可选的会话ID

        Returns:
            检测结果，表明文本是否有效
        """
        session_id = session_id or str(uuid.uuid4())
        langfuse_handler = create_langfuse_handler(
            session_id, "text_validity")

        result = await self.validity_chain.ainvoke(
            {
                "text": input_data.text,
                "context": input_data.context,
            },
            config={"callbacks": [langfuse_handler]},
        )

        return TextValidityResult(**result)

    async def async_batch_check(
            self,
            texts: List[str],
            context: str,
            session_id: str,
            max_concurrency: int = 3,
            progress_callback: Callable[[int], None] = None,
    ) -> List[TextValidityResult]:
        """异步批量执行文本有效性检测任务

        Args:
            texts: 待检测的文本列表
            context: 文本的上下文或主题
            session_id: 批量任务的会话ID
            max_concurrency: 最大并发数
            progress_callback: 进度回调函数，接收已完成的任务数量作为参数

        Returns:
            检测结果列表
        """
        semaphore = asyncio.Semaphore(max_concurrency)
        results = [None] * len(texts)  # 预分配结果列表
        completed_count = 0

        async def check_with_semaphore(text: str, index: int):
            async with semaphore:
                input_data = TextValidityInput(
                    text=text,
                    context=context
                )
                result = await self.async_check_validity(input_data, session_id)
                results[index] = result  # 保持原始顺序

                nonlocal completed_count
                completed_count += 1
                if progress_callback:
                    progress_callback(completed_count)

                return result

        # 创建所有任务
        tasks = [
            check_with_semaphore(text, i)
            for i, text in enumerate(texts)
        ]

        # 使用 as_completed 处理任务
        for task in asyncio.as_completed(tasks):
            await task  # 等待每个任务完成，但不需要其结果，因为已经存储在results中

        return results