# sql_generation.py

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from langfuse import Langfuse
from langfuse.callback import CallbackHandler

from utils.llm_tools import LanguageModelChain, init_language_model

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SQLGenerationResponse(BaseModel):
    """SQL生成响应模型"""
    sql: str = Field(..., description="生成的SQL查询语句")


class SQLGenerator:
    """SQL生成器 - 基于增强后的查询生成SQL语句"""

    def __init__(
        self,
        language_model=None,
        top_k: int = 10,
        langfuse_client: Optional[Langfuse] = None
    ):
        """
        初始化SQL生成器

        Args:
            language_model: 语言模型实例，如未提供则初始化默认模型
            top_k: 默认返回的最大结果数
            langfuse_client: Langfuse客户端实例，用于跟踪和反馈
        """
        self.top_k = top_k
        self.language_model = language_model or init_language_model(
            provider=os.getenv("SMART_LLM_PROVIDER"),
            model_name=os.getenv("SMART_LLM_MODEL")
        )
        self.langfuse_client = langfuse_client or Langfuse()

        # 系统提示词
        self.SYSTEM_MESSAGE = """
你是一个SQL专家。给定一个经过优化的查询描述，请生成一个语法正确的SQL查询语句。这个查询描述已经经过了优化，包含了完整的查询意图和必要的上下文信息。

请按照以下要求生成SQL：

1. 除非查询描述中明确指定了要获取的示例数量，否则最多只能查询{top_k}个结果，并使用LIMIT子句。

2. 切勿查询表中的所有列。必须只查询回答问题所需的列。用反斜线 (`) 包住每一列的名称。

3. 注意只使用在下表中可以看到的列名。注意不要查询不存在的列。此外，还要注意哪一列在哪个表中。

4. 今天是{current_date}。

5. 返回结果必须为JSON格式，其仅有一个属性`sql`，值为SQL查询语句。

以下是表结构信息：
{table_schema}
"""

        # 人类消息模板
        self.HUMAN_MESSAGE_TEMPLATE = """
增强后的查询描述：{enhanced_query}

请基于以上优化后的查询描述生成SQL语句。
"""

        # 初始化语言模型链
        self.assistant_chain = LanguageModelChain(
            SQLGenerationResponse,
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
            tags=["sql_generation"],
            session_id=session_id,
            metadata={"step": "generate_sql"}
        )

    def generate_sql(
        self,
        enhanced_query: str,
        table_schema: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        基于增强后的查询生成SQL语句

        Args:
            enhanced_query: 经过增强的查询描述
            table_schema: 表结构信息
            session_id: 会话ID，用于跟踪和反馈

        Returns:
            Dict[str, Any]: 包含生成的SQL和其他相关信息的字典
        """
        try:
            # 创建Langfuse处理器
            langfuse_handler = self._create_langfuse_handler(
                session_id or "default_session"
            )

            # 准备输入数据
            input_data = {
                "enhanced_query": enhanced_query,
                "table_schema": table_schema,
                "top_k": self.top_k,
                "current_date": datetime.now().strftime("%Y-%m-%d")
            }

            logger.info(f"Generating SQL for enhanced query: {enhanced_query}")

            # 调用语言模型生成SQL
            result = self.assistant_chain.invoke(
                input_data,
                config={"callbacks": [langfuse_handler]}
            )

            # 记录跟踪ID
            trace_id = langfuse_handler.get_trace_id()
            result["trace_id"] = trace_id

            logger.info(f"SQL generated successfully")
            return result

        except Exception as e:
            logger.error(f"Error generating SQL: {str(e)}")
            raise ValueError(f"SQL生成过程中发生错误: {str(e)}")

    def record_feedback(self, trace_id: str, is_useful: bool):
        """
        记录用户反馈

        Args:
            trace_id: 跟踪ID
            is_useful: 反馈是否有用
        """
        self.langfuse_client.score(
            trace_id=trace_id,
            name="sql_feedback",
            value=is_useful,
            data_type="BOOLEAN"
        )