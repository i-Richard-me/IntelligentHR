"""
SQL生成节点模块。
负责评估查询可行性并生成SQL语句。
"""

import logging
from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage

from backend.sql_assistant.states.assistant_state import SQLAssistantState
from backend.sql_assistant.utils.format_utils import (
    format_table_structures,
    format_term_descriptions
)
from utils.llm_tools import init_language_model, LanguageModelChain

logger = logging.getLogger(__name__)


class SQLGenerationResult(BaseModel):
    """SQL生成结果模型"""
    is_feasible: bool = Field(
        ...,
        description="表示查询是否可行，根据现有数据表是否能够满足用户的查询需求"
    )
    infeasible_reason: Optional[str] = Field(
        None,
        description="当查询不可行时，说明不可行的具体原因"
    )
    sql_query: Optional[str] = Field(
        None,
        description="当查询可行时，生成的SQL查询语句"
    )


# 系统提示词，保持原有定义
SQL_GENERATION_SYSTEM_PROMPT = """你是一个专业的数据分析师，负责评估用户查询是否能通过现有数据表完成，并生成相应的SQL语句。
请遵循以下规则进行判断和生成：

1. 可行性判断要点：
   - 充分理解数据表中的字段含义和真实的数据类型
   - 检查用户需求的数据项是否能从现有表中获取
   - 检查查询所需的每个字段是否在表中精确存在
   - 严格验证字段的业务含义是否与查询需求完全匹配
   - 确认表之间的关联字段存在且语义一致
   - 确认数据粒度是否满足查询需求
   - 如有字段缺失或语义不匹配，应判定为不可行

2. 当查询不可行时：
   - 设置 is_feasible 为 false
   - 在 infeasible_reason 中详细说明原因
   - 不生成SQL语句

3. 当查询可行时：
   - 设置 is_feasible 为 true
   - 生成标准的SQL语句
   - 使用正确的表和字段名
   - 确保SQL语法正确

4. SQL生成规范：
   - 使用MYSQL语法
   - 正确处理表连接和条件筛选
   - 正确处理NULL值
   - 使用适当的聚合函数和分组

5. 优化建议：
   - 只选择必要的字段
   - 对于容易存在表述不精准的字段，使用'%%keyword%%'进行模糊匹配
   - 添加适当的WHERE条件
   - 使用合适的索引
   - 避免使用SELECT *
"""

SQL_GENERATION_USER_PROMPT = """请根据以下信息评估查询可行性并生成SQL：

1. 规范化后的查询需求：
{normalized_query}

2. 可用的表结构：
{table_structures}

请首先评估查询可行性，并按照指定的JSON格式输出结果。如果可行则生成SQL查询，如果不可行则提供详细的原因。"""


def create_sql_generation_chain(temperature: float = 0.0) -> LanguageModelChain:
    """创建SQL生成任务链

    Args:
        temperature: 模型温度参数，控制输出的随机性

    Returns:
        LanguageModelChain: 配置好的SQL生成任务链
    """
    llm = init_language_model(temperature=temperature)

    return LanguageModelChain(
        model_cls=SQLGenerationResult,
        sys_msg=SQL_GENERATION_SYSTEM_PROMPT,
        user_msg=SQL_GENERATION_USER_PROMPT,
        model=llm,
    )()


def sql_generation_node(state: SQLAssistantState) -> dict:
    """SQL生成节点函数

    基于查询需求和表结构信息，评估查询可行性并生成SQL语句。
    包含查询可行性评估和SQL语句生成两个主要步骤。

    Args:
        state: 当前状态对象

    Returns:
        dict: 包含SQL生成结果的状态更新
    """
    # 验证必要的输入
    if not state.get("normalized_query"):
        return {"error": "状态中未找到规范化查询"}
    if not state.get("table_structures"):
        return {"error": "状态中未找到表结构信息"}

    try:
        # 准备输入数据
        normalized_query = state["normalized_query"]
        table_structures = format_table_structures(state["table_structures"])
        term_descriptions = format_term_descriptions(
            state.get("domain_term_mappings", {})
        )

        # 创建并执行SQL生成链
        generation_chain = create_sql_generation_chain()
        result = generation_chain.invoke({
            "normalized_query": normalized_query,
            "table_structures": table_structures,
            "term_descriptions": term_descriptions
        })

        # 更新状态
        response = {
            "generated_sql": {
                "is_feasible": result["is_feasible"],
                "infeasible_reason": result["infeasible_reason"] if not result["is_feasible"] else None,
                "sql_query": result["sql_query"] if result["is_feasible"] else None
            }
        }

        # 如果查询不可行，将原因添加到消息历史
        if not result["is_feasible"] and result.get("infeasible_reason"):
            response["messages"] = [
                AIMessage(content=result["infeasible_reason"])
            ]

        return response

    except Exception as e:
        error_msg = f"SQL生成过程出错: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}
