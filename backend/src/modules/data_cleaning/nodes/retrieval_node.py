"""
检索节点，负责从向量数据库中检索相似实体
"""
from typing import Dict
import os
from ..models.state import GraphState, ProcessingStatus
from ..tools.retrieval_tools import RetrievalTools

# 从环境变量获取检索配置
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "")
DB_NAME = os.getenv("DB_NAME", "default")
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "")
EMBEDDING_API_BASE = os.getenv("EMBEDDING_API_BASE", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "")
TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "1"))

# 初始化检索工具
embedding_config = {
    "api_key": EMBEDDING_API_KEY,
    "api_url": EMBEDDING_API_BASE,
    "model": EMBEDDING_MODEL,
}
retrieval_tools = RetrievalTools(
    collection_name=COLLECTION_NAME,
    db_name=DB_NAME,
    embedding_config=embedding_config
)

async def retrieval_node(state: GraphState) -> Dict:
    """
    检索节点处理函数

    Args:
        state: 当前图状态

    Returns:
        更新状态的字典
    """
    # 执行检索
    results = await retrieval_tools.aretrieve(
        state["identified_entity_name"],
        top_k=TOP_K
    )

    # 处理检索结果
    if results:
        result = results[0]  # 取第一个最相似的结果
        updates = {
            "retrieved_entity_name": result.get("original_name"),
            "standard_name": result.get("standard_name"),
        }
    else:
        updates = {
            "retrieved_entity_name": None,
            "standard_name": None,
        }

    return updates
