import uuid
import asyncio
from typing import List, Callable
from config.config import config
from common.utils.llm_tools import init_language_model, LanguageModelChain
from .sensitive_detection_result import (
    SensitiveDetectionResult,
    SensitiveDetectionInput,
    SENSITIVE_DETECTION_SYSTEM_PROMPT,
    SENSITIVE_DETECTION_HUMAN_PROMPT,
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
        tags=["sensitive_detection"],
        session_id=session_id,
        metadata={"step": step},
    )


class SensitiveDetectionWorkflow:
    """敏感信息检测工作流程类"""

    def __init__(self):
        """初始化敏感信息检测工作流程"""
        self.language_model = init_language_model(
            provider=config.sensitive_detection.llm_provider,
            model_name=config.sensitive_detection.llm_model,
            temperature=config.sensitive_detection.temperature,
        )
        self.detection_chain = LanguageModelChain(
            SensitiveDetectionResult,
            SENSITIVE_DETECTION_SYSTEM_PROMPT,
            SENSITIVE_DETECTION_HUMAN_PROMPT,
            self.language_model,
        )()

    async def async_detect_sensitive(
            self, input_data: SensitiveDetectionInput, session_id: str = None
    ) -> SensitiveDetectionResult:
        """异步执行单个敏感信息检测任务

        Args:
            input_data: 包含待检测文本、上下文和敏感类型配置的输入数据
            session_id: 可选的会话ID

        Returns:
            检测结果，包含发现的敏感信息（如果有）
        """
        session_id = session_id or str(uuid.uuid4())
        langfuse_handler = create_langfuse_handler(
            session_id, "sensitive_detection")

        # 格式化敏感类型描述
        sensitive_types_desc = input_data.format_prompt_context()

        result = await self.detection_chain.ainvoke(
            {
                "text": input_data.text,
                "context": input_data.context,
                "sensitive_types": sensitive_types_desc,
                "sensitive_types_desc": sensitive_types_desc  # 添加这个参数
            },
            config={"callbacks": [langfuse_handler]},
        )

        return SensitiveDetectionResult(**result)

    async def async_batch_detect(
            self,
            texts: List[str],
            context: str,
            sensitive_types: dict,
            session_id: str,
            max_concurrency: int = 3,
            progress_callback: Callable[[int], None] = None,
    ) -> List[SensitiveDetectionResult]:
        """异步批量执行敏感信息检测任务

        Args:
            texts: 待检测的文本列表
            context: 文本的上下文或主题
            sensitive_types: 要检测的敏感信息类型配置
            session_id: 批量任务的会话ID
            max_concurrency: 最大并发数
            progress_callback: 进度回调函数，接收已完成的任务数量作为参数

        Returns:
            检测结果列表
        """
        semaphore = asyncio.Semaphore(max_concurrency)
        results = [None] * len(texts)  # 预分配结果列表
        completed_count = 0

        async def detect_with_semaphore(text: str, index: int):
            async with semaphore:
                input_data = SensitiveDetectionInput(
                    text=text,
                    context=context,
                    sensitive_types=sensitive_types
                )
                result = await self.async_detect_sensitive(input_data, session_id)
                results[index] = result  # 保持原始顺序

                nonlocal completed_count
                completed_count += 1
                if progress_callback:
                    progress_callback(completed_count)

                return result

        # 创建所有任务
        tasks = [
            detect_with_semaphore(text, i)
            for i, text in enumerate(texts)
        ]

        # 使用 as_completed 处理任务
        for task in asyncio.as_completed(tasks):
            await task  # 等待每个任务完成，但不需要其结果，因为已经存储在results中

        return results