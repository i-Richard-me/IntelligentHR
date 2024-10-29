# result_interpreter.py

import os
from typing import List, Dict, Any, Optional
import logging
from dataclasses import dataclass
from pydantic import BaseModel, Field
import json
from datetime import datetime
from langfuse import Langfuse
from langfuse.callback import CallbackHandler

from utils.llm_tools import LanguageModelChain, init_language_model

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class InterpretationResponse(BaseModel):
    """结果解释响应模型"""

    answer: str = Field(..., description="基于查询结果生成的回答")


class ResultInterpreter:
    """查询结果解释器"""

    def __init__(self, language_model=None, langfuse_client: Optional[Langfuse] = None):
        self.language_model = language_model or init_language_model(
            provider=os.getenv("SMART_LLM_PROVIDER"),
            model_name=os.getenv("SMART_LLM_MODEL"),
        )
        self.langfuse_client = langfuse_client or Langfuse()

        self.SYSTEM_MESSAGE = """
你是一个专业的数据分析师，你的任务是根据SQL查询结果为用户提供清晰、准确的答案。请遵循以下规则：

1. 直接回答用户的问题，使用自然、友好的语言。
2. 突出关键信息，但要确保答案的完整性。
3. 如果结果集为空，说明未找到相关数据。
4. 如果发现结果中的有趣模式或特殊情况，可以主动指出。
5. 必要时提供数字的上下文（例如，百分比、比较、趋势等）。
6. 确保回答与用户的原始问题紧密相关。

今天是{current_date}。

表结构信息：
{table_schema}

请生成一个JSON响应，仅包含一个属性answer，值为对用户问题的直接回答。请确保回答简洁明了，直接针对用户的问题提供信息。
"""

        self.HUMAN_MESSAGE_TEMPLATE = """
用户原始问题：
{user_query}

执行的SQL查询：
{sql_query}

查询结果：
{query_results}

请根据以上信息生成回答。
"""

        self.assistant_chain = LanguageModelChain(
            InterpretationResponse,
            self.SYSTEM_MESSAGE,
            self.HUMAN_MESSAGE_TEMPLATE,
            self.language_model
        )()

    def _create_langfuse_handler(self, session_id: str) -> CallbackHandler:
        """
        创建Langfuse回调处理器

        Args:
            session_id: 会话ID

        Returns:
            CallbackHandler: 配置好的回调处理器
        """
        return CallbackHandler(
            tags=["result_interpretation"],
            session_id=session_id,
            metadata={"step": "interpret_results"},
        )

    def interpret_results(
        self,
        user_query: str,
        sql_query: str,
        query_results: List[Dict[str, Any]],
        table_schema: str,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        解释查询结果并生成回答

        Args:
            user_query: 用户的原始问题
            sql_query: 执行的SQL查询
            query_results: 查询结果
            table_schema: 表结构信息
            session_id: 会话ID

        Returns:
            Dict[str, Any]: 包含回答的字典
        """
        try:
            langfuse_handler = self._create_langfuse_handler(
                session_id or "default_session"
            )

            input_data = {
                "user_query": user_query,
                "sql_query": sql_query,
                "query_results": json.dumps(query_results, ensure_ascii=False),
                "table_schema": table_schema,
                "current_date": datetime.now().strftime("%Y-%m-%d"),
            }

            logger.info(f"Interpreting results for query: {user_query}")

            result = self.assistant_chain.invoke(
                input_data, config={"callbacks": [langfuse_handler]}
            )

            result["trace_id"] = langfuse_handler.get_trace_id()
            logger.info(f"Results interpreted successfully")

            return result

        except Exception as e:
            import traceback
            logger.error(f"Error interpreting results: {str(e)}")
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            raise ValueError(f"结果解释过程中发生错误: {str(e)}")

    def record_feedback(self, trace_id: str, is_useful: bool):
        """
        记录用户反馈

        Args:
            trace_id: 跟踪ID
            is_useful: 反馈是否有用
        """
        self.langfuse_client.score(
            trace_id=trace_id,
            name="feedback",
            value=is_useful,
            data_type="BOOLEAN",
        )


def create_result_interpreter(
    language_model=None,
    langfuse_client=None
) -> ResultInterpreter:
    """
    创建ResultInterpreter实例的工厂函数

    Args:
        language_model: 可选的语言模型实例
        langfuse_client: 可选的Langfuse客户端实例

    Returns:
        ResultInterpreter: 配置好的ResultInterpreter实例
    """
    return ResultInterpreter(
        language_model=language_model,
        langfuse_client=langfuse_client
    )
