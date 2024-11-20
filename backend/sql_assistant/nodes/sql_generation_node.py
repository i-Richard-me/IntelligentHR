"""
SQL生成节点模块。
负责生成SQL查询语句。
"""

from pydantic import BaseModel, Field
from typing import Optional

from backend.sql_assistant.states.assistant_state import SQLAssistantState
from backend.sql_assistant.utils.format_utils import (
    format_table_structures,
    format_term_descriptions
)
from utils.llm_tools import init_language_model, LanguageModelChain


class SQLGenerationResult(BaseModel):
    """SQL生成结果模型"""
    sql_query: str = Field(
        ...,
        description="生成的SQL查询语句"
    )


SQL_GENERATION_SYSTEM_PROMPT = """你是一个专业的数据分析师，负责生成SQL查询语句。
请遵循以下规则生成SQL：

1. SQL生成规范：
   - 使用MYSQL语法
   - 正确处理表连接和条件筛选
   - 正确处理NULL值
   - 使用适当的聚合函数和分组
   - 当涉及到日期字段，注意将字符串或文本形式存储的日期字段转换为日期格式

2. 优化建议：
   - 只选择与查询需求相关的必要字段，控制在5个字段以内
   - 避免使用SELECT *
   - 添加适当的WHERE条件
   - 对于容易存在表述不精准的字段，如项目名称等，使用'%%keyword%%'进行模糊匹配"""


SQL_GENERATION_USER_PROMPT = """请根据以下信息生成SQL查询语句：

1. 查询需求：
{rewritten_query}

2. 可用的表结构：
{table_structures}

3. 检索到的业务术语信息(如果存在)：
{term_descriptions}

请生成标准的SQL查询语句，并以指定的JSON格式输出结果。"""


def create_sql_generation_chain(temperature: float = 0.0) -> LanguageModelChain:
    """创建SQL生成任务链"""
    llm = init_language_model(temperature=temperature)
    
    return LanguageModelChain(
        model_cls=SQLGenerationResult,
        sys_msg=SQL_GENERATION_SYSTEM_PROMPT,
        user_msg=SQL_GENERATION_USER_PROMPT,
        model=llm,
    )()


def sql_generation_node(state: SQLAssistantState) -> dict:
    """SQL生成节点函数"""
    if not state.get("rewritten_query"):
        return {"error": "状态中未找到改写后的查询"}
    if not state.get("table_structures"):
        return {"error": "状态中未找到表结构信息"}

    try:
        input_data = {
            "rewritten_query": state["rewritten_query"],
            "table_structures": format_table_structures(state["table_structures"]),
            "term_descriptions": format_term_descriptions(
                state.get("domain_term_mappings", {})
            )
        }

        generation_chain = create_sql_generation_chain()
        result = generation_chain.invoke(input_data)

        return {
            "generated_sql": {
                "sql_query": result["sql_query"]
            }
        }

    except Exception as e:
        error_msg = f"SQL生成过程出错: {str(e)}"
        return {"error": error_msg}
