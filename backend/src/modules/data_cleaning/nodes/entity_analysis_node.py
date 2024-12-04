"""
实体分析节点，专门负责分析搜索结果并提取实体信息
"""
from typing import Dict
from common.utils.llm_tools import init_language_model, LanguageModelChain
from ..models.state import GraphState, ProcessingStatus
from ..models.schema import EntityRecognition
import logging

logger = logging.getLogger(__name__)

# 初始化语言模型
language_model = init_language_model()

# 定义系统消息模板
SYSTEM_MESSAGE = """
你的工作是根据提供的网络搜索结果来判断搜索结果是否与查询的{entity_type}相关。
如果搜索结果与查询的{entity_type}相关，你需要进一步分析并提取标准化的{entity_type}。
{analysis_instructions}
如果能够提取出标准化的{entity_type}，请提供该标准化名称，并标记状态为'known'。
如果无法提取出相关信息，或者搜索结果与查询的{entity_type}不相关，请标记状态为'unknown'，并省略{entity_type}名称。
在进行判断时，请考虑{entity_type}名称的相似性、搜索结果中提及的相关信息等。
"""

# 定义人类消息模板
HUMAN_MESSAGE = """
针对特定查询'{user_query}'，请仔细评估以下网络搜索片段：

{snippets}

如果搜索结果明确指向查询中的{entity_type}，并且您能够提取出标准化的{entity_type}名称，
请提供该标准化名称并标注状态为'known'。
如果搜索结果不明确或无法提取出相关信息，请标注状态为'unknown'，并省略{entity_type}名称。
"""

async def entity_analysis_node(state: GraphState) -> Dict:
    """实体分析节点处理函数

    Args:
        state: 当前图状态，必须包含 entity_config 和 search_results

    Returns:
        更新状态的字典

    Raises:
        ValueError: 当state中缺少必要的信息时抛出
    """
    try:
        if not state.get("entity_config"):
            raise ValueError("实体配置信息缺失")

        if not state.get("search_results"):
            raise ValueError("搜索结果缺失")

        # 创建分析链
        analyzer = LanguageModelChain(
            EntityRecognition,
            SYSTEM_MESSAGE,
            HUMAN_MESSAGE,
            language_model
        )()

        # 准备分析参数
        analysis_params = {
            "user_query": state["original_input"],
            "snippets": state["search_results"],
            "entity_type": state["entity_config"]["display_name"],
            "analysis_instructions": state["entity_config"]["analysis_instructions"]
        }

        # 执行分析
        analysis_result = await analyzer.ainvoke(analysis_params)

        # 处理结果
        is_identified = analysis_result["recognition_status"] == "known"

        logger.debug(f"分析结果: query={state['original_input']}, "
                    f"is_identified={is_identified}, "
                    f"entity={analysis_result.get('identified_entity')}")

        # 返回结果
        return {
            "is_identified": is_identified,
            "identified_entity_name": analysis_result["identified_entity"] if is_identified else None,
            "status": ProcessingStatus.IDENTIFIED if is_identified else ProcessingStatus.UNIDENTIFIED
        }

    except Exception as e:
        logger.error(f"实体分析节点处理失败: {str(e)}")
        return {
            "is_identified": False,
            "status": ProcessingStatus.ERROR,
            "error_message": f"实体分析失败: {str(e)}"
        }