"""
数据清洗工作流类，提供主要的工作流接口
"""
from typing import Optional, List, Dict, Any
from uuid import uuid4
import logging
from langgraph.checkpoint.memory import MemorySaver
from langfuse.callback import CallbackHandler

from .graph_builder import build_graph
from ..models.state import GraphState, ProcessingStatus
from ..models.entity_config import EntityConfig
from ..tools.retrieval_tools import RetrievalTools

logger = logging.getLogger(__name__)


class DataCleaningWorkflow:
    """数据清洗工作流类，基于 LangGraph 框架实现"""

    def __init__(
            self,
            entity_config: EntityConfig,
            enable_validation: bool = True,
            enable_search: bool = True,
            enable_retrieval: bool = True,
    ):
        """初始化数据清洗工作流

        Args:
            entity_config: 实体配置
            retrieval_tools: 检索工具实例
            enable_validation: 是否启用验证步骤
            enable_search: 是否启用搜索步骤
            enable_retrieval: 是否启用检索步骤
        """
        self.entity_config = entity_config

        # 移除 retrieval_tools 实例化
        self.workflow_graph = build_graph(
            enable_validation=enable_validation,
            enable_search=enable_search,
            enable_retrieval=enable_retrieval
        ).compile()

        logger.info(f"工作流初始化完成: entity_type={entity_config.entity_type}")

    def _initialize_state(self, user_input: str) -> GraphState:
        """初始化工作流状态

        Args:
            user_input: 用户输入的实体名称

        Returns:
            初始化的图状态
        """
        return {
            "messages": [],
            "entity_config": self.entity_config.to_dict(),
            "collection_name": self.entity_config.collection_name,
            "original_input": user_input,
            "is_valid": False,
            "is_identified": False,
            "identified_entity_name": None,
            "retrieved_entity_name": None,
            "standard_name": None,
            "final_entity_name": None,
            "search_results": None,
            "status": None,
            "error_message": None,
        }

    def _create_langfuse_handler(
            self,
            session_id: str,
            step: str
    ) -> CallbackHandler:
        """创建 Langfuse 回调处理器

        Args:
            session_id: 会话ID
            step: 处理步骤

        Returns:
            Langfuse 回调处理器
        """
        return CallbackHandler(
            tags=["data_cleaning"],
            session_id=session_id,
            metadata={
                "step": step,
                "entity_type": self.entity_config.entity_type
            },
        )

    async def async_clean_entity(
            self,
            input_text: str,
            session_id: str = None
    ) -> Dict[str, Any]:
        """异步执行单个实体的数据清洗任务

        Args:
            input_text: 输入的实体文本
            session_id: 可选的会话ID

        Returns:
            清洗结果
        """
        try:
            # 准备会话ID和回调处理器
            session_id = session_id or str(uuid4())
            langfuse_handler = self._create_langfuse_handler(
                session_id, "data_cleaning")

            # 初始化状态
            initial_state = self._initialize_state(input_text)

            # 执行工作流
            result = await self.workflow_graph.ainvoke(
                initial_state,
                {
                    "configurable": {
                        "thread_id": session_id,
                        "callbacks": [langfuse_handler]
                    }
                }
            )

            logger.debug(f"实体清洗完成: input={input_text}, "
                         f"result={result.get('final_entity_name')}")
            return result

        except Exception as e:
            error_msg = f"实体清洗过程发生错误: {str(e)}"
            logger.error(error_msg)
            return {
                "status": ProcessingStatus.ERROR,
                "error_message": error_msg,
                "final_entity_name": input_text
            }

    async def async_batch_clean(
            self,
            input_texts: List[str],
            session_id: str,
            max_concurrency: int = 3,
            progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """异步批量执行实体清洗任务

        Args:
            input_texts: 待清洗的实体文本列表
            session_id: 批量任务的会话ID
            max_concurrency: 最大并发数
            progress_callback: 进度回调函数

        Returns:
            清洗结果列表
        """
        import asyncio
        semaphore = asyncio.Semaphore(max_concurrency)
        results = [None] * len(input_texts)
        completed_count = 0

        async def clean_with_semaphore(text: str, index: int):
            async with semaphore:
                result = await self.async_clean_entity(text, f"{session_id}_{index}")
                results[index] = result

                nonlocal completed_count
                completed_count += 1
                if progress_callback:
                    progress_callback(completed_count)

                return result

        try:
            # 创建所有任务
            tasks = [
                clean_with_semaphore(text, i)
                for i, text in enumerate(input_texts)
            ]

            # 使用 as_completed 处理任务
            for task in asyncio.as_completed(tasks):
                await task

            logger.info(f"批量清洗完成: total={len(input_texts)}")
            return results

        except Exception as e:
            logger.error(f"批量清洗失败: {str(e)}")
            # 返回已完成的结果和错误结果
            return [
                result if result is not None else {
                    "status": ProcessingStatus.ERROR,
                    "error_message": "批量处理过程中断",
                    "final_entity_name": input_texts[i]
                }
                for i, result in enumerate(results)
            ]
