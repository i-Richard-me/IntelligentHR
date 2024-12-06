"""
输入验证节点，负责验证用户输入的实体名称是否有效
"""
from typing import Dict
from common.utils.llm_tools import init_language_model, LanguageModelChain
from config.config import config
from ..models.state import GraphState, ProcessingStatus
from ..models.schema import InputValidation
import logging

logger = logging.getLogger(__name__)

# 初始化语言模型
language_model = init_language_model(
    provider=config.data_cleaning.llm_provider,
    model_name=config.data_cleaning.llm_model,
    temperature=config.data_cleaning.temperature
)

# 定义系统消息模板
SYSTEM_MESSAGE = """
你的任务是判断用户输入的查询{entity_type}是否是一个具体的、有效的{entity_type}。
你将收到一个用户查询的{entity_type}。
请判断该名称是否足以识别一个特定的{entity_type}。
如果名称具体且明确，足以识别一个特定的{entity_type}，则将其标记为'True'。
如果名称模糊，或者不是指一个特定的{entity_type}，则标记为'False'。
{validation_instructions}
"""

# 定义人类消息模板
HUMAN_MESSAGE = "用户查询的{entity_type}：{user_query}"

async def validation_node(state: GraphState) -> Dict:
    """输入验证节点处理函数

    Args:
        state: 当前图状态，必须包含 entity_config

    Returns:
        更新状态的字典

    Raises:
        ValueError: 当state中缺少必要的配置信息时抛出
    """
    try:
        if not state.get("entity_config"):
            raise ValueError("实体配置信息缺失")

        # 创建验证链
        validator = LanguageModelChain(
            InputValidation,
            SYSTEM_MESSAGE,
            HUMAN_MESSAGE,
            language_model
        )()

        # 准备验证参数
        validation_params = {
            "user_query": state["original_input"],
            "entity_type": state["entity_config"]["display_name"],
            "validation_instructions": state["entity_config"]["validation_instructions"]
        }

        # 执行验证调用
        validation_result = await validator.ainvoke(validation_params)

        logger.debug(f"验证结果: query={state['original_input']}, "
                    f"is_valid={validation_result['is_valid']}")

        # 返回验证结果
        return {
            "is_valid": validation_result["is_valid"],
            "status": ProcessingStatus.VALID_INPUT if validation_result["is_valid"]
                     else ProcessingStatus.INVALID_INPUT
        }

    except Exception as e:
        logger.error(f"验证节点处理失败: {str(e)}")
        return {
            "is_valid": False,
            "status": ProcessingStatus.ERROR,
            "error_message": f"验证失败: {str(e)}"
        }