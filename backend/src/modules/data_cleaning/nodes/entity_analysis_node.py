"""
实体分析节点，专门负责分析搜索结果并提取实体信息
"""
from typing import Dict
import os
from common.utils.llm_tools import init_language_model, LanguageModelChain
from ..models.state import GraphState, ProcessingStatus
from ..models.schema import EntityRecognition

# 初始化语言模型
language_model = init_language_model(
    provider=os.getenv("SMART_LLM_PROVIDER"),
    model_name=os.getenv("SMART_LLM_MODEL")
)

# 从环境变量获取配置
ENTITY_TYPE = os.getenv("ENTITY_TYPE", "实体")
ANALYSIS_INSTRUCTIONS = os.getenv("ANALYSIS_INSTRUCTIONS", "")

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
    """
    实体分析节点处理函数

    Args:
        state: 当前图状态

    Returns:
        更新状态的字典
    """
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
        "entity_type": ENTITY_TYPE,
        "analysis_instructions": ANALYSIS_INSTRUCTIONS
    }

    # 执行分析
    analysis_result = await analyzer.ainvoke(analysis_params)

    # 处理结果
    is_identified = analysis_result["recognition_status"] == "known"

    # 返回结果
    return {
        "is_identified": is_identified,
        "identified_entity_name": analysis_result["identified_entity"] if is_identified else None,
        "status": ProcessingStatus.IDENTIFIED if is_identified else ProcessingStatus.UNIDENTIFIED
    }