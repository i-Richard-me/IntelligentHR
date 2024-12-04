"""
验证节点，负责验证检索到的实体是否与用户查询匹配
"""
from typing import Dict
from common.utils.llm_tools import init_language_model, LanguageModelChain
from ..models.state import GraphState, ProcessingStatus
from ..models.schema import EntityVerification
import logging

logger = logging.getLogger(__name__)

# 初始化语言模型
language_model = init_language_model()

# 定义系统消息模板
SYSTEM_MESSAGE = """
你的任务是验证从向量数据库检索到的{entity_type}是否与用户提供的查询{entity_type}指向同一个标准化{entity_type}。
你将收到一个用户查询的{entity_type}、从数据库检索到的最相似的{entity_type}以及相关的搜索结果。
请结合搜索结果来判断检索到的{entity_type}是否确实是指向用户查询的同一个标准化{entity_type}。
{verification_instructions}
如果检索到的{entity_type}与搜索结果一致，并且可以确认是指向同一个标准化{entity_type}，则将其标记为'verified'。
如果无法确认是同一标准化{entity_type}，或者搜索结果与查询不相关，则标记为'unverified'。
在判断时，请考虑{entity_type}名称的正式表述、可能的简称或全称差异，以及搜索结果中的相关信息。
"""

# 定义人类消息模板
HUMAN_MESSAGE = """
用户查询的{entity_type}：{user_query}
检索到的{entity_type}：{retrieved_name}
搜索结果：
{search_results}
"""

async def verification_node(state: GraphState) -> Dict:
    """验证节点处理函数

    Args:
        state: 当前图状态，必须包含 entity_config

    Returns:
        更新状态的字典

    Raises:
        ValueError: 当state中缺少必要的信息时抛出
    """
    try:
        if not state.get("entity_config"):
            raise ValueError("实体配置信息缺失")

        # 确定需要验证的实体名称
        entity_to_verify = state.get("retrieved_entity_name") or state.get("identified_entity_name")
        if not entity_to_verify:
            logger.warning("没有可供验证的实体名称")
            return {
                "status": ProcessingStatus.UNVERIFIED,
                "final_entity_name": state.get("original_input")
            }

        # 创建验证链
        verifier = LanguageModelChain(
            EntityVerification,
            SYSTEM_MESSAGE,
            HUMAN_MESSAGE,
            language_model
        )()

        # 准备验证参数
        verification_params = {
            "user_query": state["original_input"],
            "retrieved_name": entity_to_verify,
            "search_results": state.get("search_results", ""),
            "entity_type": state["entity_config"]["display_name"],
            "verification_instructions": state["entity_config"]["verification_instructions"]
        }

        # 执行验证
        verification_result = await verifier.ainvoke(verification_params)

        # 处理验证结果
        is_verified = verification_result["verification_status"] == "verified"

        # 确定最终实体名称
        final_name = (
            state.get("standard_name")  # 首选标准名称
            or state.get("retrieved_entity_name")  # 其次是检索到的名称
            or state.get("identified_entity_name")  # 最后是识别出的名称
            or state.get("original_input")  # 兜底使用原始输入
        )

        logger.debug(f"验证结果: query={state['original_input']}, "
                    f"is_verified={is_verified}, "
                    f"final_name={final_name}")

        # 返回结果
        return {
            "status": ProcessingStatus.VERIFIED if is_verified else ProcessingStatus.UNVERIFIED,
            "final_entity_name": final_name
        }

    except Exception as e:
        logger.error(f"验证节点处理失败: {str(e)}")
        return {
            "status": ProcessingStatus.ERROR,
            "error_message": f"验证失败: {str(e)}",
            "final_entity_name": state.get("original_input")
        }