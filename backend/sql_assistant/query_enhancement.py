# query_enhancement.py

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


class QueryEnhancementResponse(BaseModel):
    """查询增强响应模型"""
    enhanced_query: str = Field(..., description="增强后的查询描述")
    reasoning: str = Field(..., description="增强过程的推理说明")


class QueryEnhancer:
    """查询增强器 - 将用户的原始查询转化为更明确、结构化的形式"""

    def __init__(
        self,
        language_model=None,
        langfuse_client: Optional[Langfuse] = None
    ):
        """
        初始化查询增强器

        Args:
            language_model: 语言模型实例，如未提供则初始化默认模型
            langfuse_client: Langfuse客户端实例，用于跟踪和反馈
        """
        self.language_model = language_model or init_language_model(
            provider=os.getenv("SMART_LLM_PROVIDER"),
            model_name=os.getenv("SMART_LLM_MODEL")
        )
        self.langfuse_client = langfuse_client or Langfuse()

        # 系统提示词
        self.SYSTEM_MESSAGE = """
你是一位专业的数据分析师，你的任务是理解并优化用户的查询意图。请基于用户的原始问题，生成一个更加明确和结构化的查询描述。

在分析用户查询时，请特别注意以下几点：

1. 查询目标：
   - 明确用户想要获取的具体信息
   - 识别需要返回的字段和指标
   - 确定结果的期望格式（如排序方式、限制条件等）

2. 查询条件：
   - 明确时间范围（如"最近"具体指多长时间）
   - 具体化模糊的数值表述（如"高"、"低"等）
   - 补充必要的业务过滤条件

3. 数据细节：
   - 明确需要的计算方式（如求和、平均、去重等）
   - 指定数值的精度要求
   - 说明是否需要分组或聚合

4. 业务规则：
   - 补充符合业务逻辑的隐含条件
   - 明确数据的有效性条件
   - 处理特殊情况的考虑

请记住：
- 只关注表结构中实际存在的字段
- 不要生成SQL语句
- 使用清晰的自然语言描述
- 保持对原始问题意图的准确理解

参考的表结构信息：
{table_schema}

今天的日期是：{current_date}

你的输出应该是一个JSON对象，包含两个字段：
1. enhanced_query: 优化后的查询描述
2. reasoning: 说明你是如何理解和增强原始查询的，以及做出这些改进的原因
"""

        # 人类消息模板
        self.HUMAN_MESSAGE_TEMPLATE = """
用户原始问题：{user_query}

请基于以上信息生成优化后的查询描述。
"""

        # 初始化语言模型链
        self.assistant_chain = LanguageModelChain(
            QueryEnhancementResponse,
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
            tags=["query_enhancement"],
            session_id=session_id,
            metadata={"step": "enhance_query"}
        )

    def enhance_query(
        self,
        user_query: str,
        table_schema: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        增强用户的原始查询

        Args:
            user_query: 用户的原始查询
            table_schema: 表结构信息
            session_id: 会话ID，用于跟踪和反馈

        Returns:
            Dict[str, Any]: 包含增强后的查询和推理过程的字典
        """
        try:
            # 创建Langfuse处理器
            langfuse_handler = self._create_langfuse_handler(
                session_id or "default_session"
            )

            # 准备输入数据
            input_data = {
                "user_query": user_query,
                "table_schema": table_schema,
                "current_date": datetime.now().strftime("%Y-%m-%d")
            }

            logger.info(f"Enhancing query: {user_query}")

            # 调用语言模型增强查询
            result = self.assistant_chain.invoke(
                input_data,
                config={"callbacks": [langfuse_handler]}
            )

            # 记录跟踪ID
            trace_id = langfuse_handler.get_trace_id()
            result["trace_id"] = trace_id

            logger.info("Query enhanced successfully")
            return result

        except Exception as e:
            logger.error(f"Error enhancing query: {str(e)}")
            raise ValueError(f"查询增强过程中发生错误: {str(e)}")

    def record_feedback(self, trace_id: str, is_useful: bool):
        """
        记录用户反馈

        Args:
            trace_id: 跟踪ID
            is_useful: 反馈是否有用
        """
        self.langfuse_client.score(
            trace_id=trace_id,
            name="enhancement_feedback",
            value=is_useful,
            data_type="BOOLEAN"
        )