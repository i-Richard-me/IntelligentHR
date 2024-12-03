"""
搜索结果节点，专门负责执行网络搜索
"""
from typing import Dict
import os
from ..models.state import GraphState, ProcessingStatus
from ..tools.search_tools import SearchTools

# 从环境变量获取搜索配置
MAX_SEARCH_RESULTS = int(os.getenv("MAX_SEARCH_RESULTS", "5"))
SEARCH_TYPE = os.getenv("SEARCH_TYPE", "tavily")

# 初始化搜索工具
search_tools = SearchTools(max_results=MAX_SEARCH_RESULTS)

async def search_results_node(state: GraphState) -> Dict:
    """
    搜索结果节点处理函数，仅负责执行搜索并返回原始结果

    Args:
        state: 当前图状态

    Returns:
        更新状态的字典,包含搜索结果
    """
    # 执行搜索
    search_results = await search_tools.asearch(
        state["original_input"],
        search_type=SEARCH_TYPE
    )

    # 返回搜索结果
    return {
        "search_results": search_results
    }