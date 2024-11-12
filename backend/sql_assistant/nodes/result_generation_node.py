"""
结果生成节点模块。
负责将SQL查询结果转化为用户友好的描述。
"""

import logging
from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage

from backend.sql_assistant.states.assistant_state import SQLAssistantState
from backend.sql_assistant.utils.format_utils import (
    format_results_preview,
    format_term_descriptions
)
from utils.llm_tools import init_language_model, LanguageModelChain

logger = logging.getLogger(__name__)


class ResultGenerationOutput(BaseModel):
    """查询结果生成输出模型"""
    result_description: str = Field(
        ...,
        description="面向用户的查询结果描述"
    )


# 系统提示词，保持原有定义
RESULT_GENERATION_SYSTEM_PROMPT = """你是一个专业的数据分析师，负责将SQL查询结果转化为用户友好的自然语言描述。
请遵循以下规则生成反馈：

1. 反馈内容要求：
   - 清晰描述查询结果的主要发现
   - 突出重要的数据指标和趋势
   - 使用简洁、专业的语言
   - 需要说明数据的时间范围
   - 适当解释异常或特殊数据

2. 格式规范：
   - 使用自然语言描述
   - 先总体概述，再说明细节
   - 适当使用数字和百分比
   - 保持专业性和可读性的平衡

3. 注意事项：
   - 如果结果被截断，需要说明仅展示部分数据
   - 确保使用正确的业务术语
   - 避免过度解读数据
   - 保持客观中立的语气"""

RESULT_GENERATION_USER_PROMPT = """请根据以下信息生成查询结果描述：

1. 用户的原始查询：
{normalized_query}

2. 查询结果：
总行数：{row_count}
是否截断：{truncated}
数据预览：
{results_preview}

3. 业务术语说明：
{term_descriptions}

请生成一段清晰、专业的描述，向用户说明查询结果。"""


def create_result_generation_chain(temperature: float = 0.0) -> LanguageModelChain:
    """创建结果生成任务链

    Args:
        temperature: 模型温度参数，控制输出的随机性

    Returns:
        LanguageModelChain: 配置好的结果生成任务链
    """
    llm = init_language_model(temperature=temperature)

    return LanguageModelChain(
        model_cls=ResultGenerationOutput,
        sys_msg=RESULT_GENERATION_SYSTEM_PROMPT,
        user_msg=RESULT_GENERATION_USER_PROMPT,
        model=llm,
    )()


def result_generation_node(state: SQLAssistantState) -> dict:
    """结果生成节点函数

    将SQL查询结果转化为用户友好的自然语言描述。
    包括数据概述、关键指标和特殊情况说明。

    Args:
        state: 当前状态对象

    Returns:
        dict: 包含结果描述的状态更新
    """
    # 获取必要信息
    execution_result = state.get("execution_result", {})
    if not execution_result or not execution_result.get('success'):
        return {"error": "状态中未找到成功的执行结果"}

    try:
        # 准备输入数据
        input_data = {
            "normalized_query": state["normalized_query"],
            "row_count": execution_result["row_count"],
            "truncated": execution_result["truncated"],
            "results_preview": format_results_preview(execution_result),
            "term_descriptions": format_term_descriptions(
                state.get("domain_term_mappings", {})
            )
        }

        # 创建并执行结果生成链
        generation_chain = create_result_generation_chain()
        result = generation_chain.invoke(input_data)

        # 将结果描述作为助手消息添加到对话历史
        return {
            "result_description": result["result_description"],
            "messages": [AIMessage(content=result["result_description"])]
        }

    except Exception as e:
        error_msg = f"结果生成过程出错: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}
