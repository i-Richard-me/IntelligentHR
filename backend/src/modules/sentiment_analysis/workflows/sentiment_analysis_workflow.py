import uuid
import asyncio
from typing import List, Callable
from config.config import config
from common.utils.llm_tools import init_language_model, LanguageModelChain
from .sentiment_analysis_result import (
    SentimentAnalysisResult,
    SentimentAnalysisInput,
    SENTIMENT_ANALYSIS_SYSTEM_PROMPT,
    SENTIMENT_ANALYSIS_HUMAN_PROMPT,
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
        tags=["sentiment_analysis"],
        session_id=session_id,
        metadata={"step": step},
    )


class SentimentAnalysisWorkflow:
    """情感分析工作流程类"""

    def __init__(self):
        """初始化情感分析工作流程"""
        self.language_model = init_language_model(
            provider=config.sentiment_analysis.llm_provider,
            model_name=config.sentiment_analysis.llm_model,
            temperature=config.sentiment_analysis.temperature,
        )
        self.analysis_chain = LanguageModelChain(
            SentimentAnalysisResult,
            SENTIMENT_ANALYSIS_SYSTEM_PROMPT,
            SENTIMENT_ANALYSIS_HUMAN_PROMPT,
            self.language_model,
        )()

    async def async_analyze_sentiment(
            self, input_data: SentimentAnalysisInput, session_id: str = None
    ) -> SentimentAnalysisResult:
        """异步执行单个文本情感分析任务

        Args:
            input_data: 包含待分析文本和上下文的输入数据
            session_id: 可选的会话ID

        Returns:
            情感分析结果
        """
        session_id = session_id or str(uuid.uuid4())
        langfuse_handler = create_langfuse_handler(
            session_id, "sentiment_analysis")

        result = await self.analysis_chain.ainvoke(
            {
                "text": input_data.text,
                "context": input_data.context,
            },
            config={"callbacks": [langfuse_handler]},
        )

        return SentimentAnalysisResult(**result)

    async def async_batch_analyze(
            self,
            texts: List[str],
            context: str,
            session_id: str,
            max_concurrency: int = 3,
            progress_callback: Callable[[int], None] = None,
    ) -> List[SentimentAnalysisResult]:
        """异步批量执行文本情感分析任务

        Args:
            texts: 待分析的文本列表
            context: 文本的上下文或主题
            session_id: 批量任务的会话ID
            max_concurrency: 最大并发数
            progress_callback: 进度回调函数，接收已完成的任务数量作为参数

        Returns:
            情感分析结果列表
        """
        semaphore = asyncio.Semaphore(max_concurrency)
        results = [None] * len(texts)  # 预分配结果列表
        completed_count = 0

        async def analyze_with_semaphore(text: str, index: int):
            async with semaphore:
                input_data = SentimentAnalysisInput(
                    text=text,
                    context=context
                )
                result = await self.async_analyze_sentiment(input_data, session_id)
                results[index] = result  # 保持原始顺序

                nonlocal completed_count
                completed_count += 1
                if progress_callback:
                    progress_callback(completed_count)

                return result

        # 创建所有任务
        tasks = [
            analyze_with_semaphore(text, i)
            for i, text in enumerate(texts)
        ]

        # 使用 as_completed 处理任务
        for task in asyncio.as_completed(tasks):
            await task  # 等待每个任务完成，但不需要其结果，因为已经存储在results中

        return results