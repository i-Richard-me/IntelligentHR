"""
检索节点，负责使用检索工具从向量数据库中检索相似实体
"""
from typing import Dict
import logging
from config.config import config
from ..models.state import GraphState, ProcessingStatus
from ..tools.retrieval_tools import RetrievalTools

logger = logging.getLogger(__name__)

async def retrieval_node(state: GraphState) -> Dict:
    """检索节点处理函数"""
    try:
        if not state.get("identified_entity_name"):
            logger.warning("没有可供检索的实体名称")
            return {
                "retrieved_entity_name": None,
                "standard_name": None,
            }
            
        # 确保状态中包含必要的配置信息
        if "entity_config" not in state:
            raise ValueError("缺少实体配置信息")
            
        collection_name = state["entity_config"].get("collection_name")
        if not collection_name:
            raise ValueError("未找到collection配置")

        # 在节点内部初始化 RetrievalTools
        retrieval_tools = RetrievalTools(
            collection_name=collection_name,
            db_name=config.data_cleaning.vector_db_name,
            embedding_config={"model": config.data_cleaning.embedding_model}
        )

        # 执行检索
        results = await retrieval_tools.aretrieve(
            state["identified_entity_name"], 
            top_k=1
        )

        # 处理检索结果
        if results:
            result = results[0]
            logger.debug(f"检索成功: query={state['identified_entity_name']}, "
                      f"result={result.get('standard_name')}")
            return {
                "retrieved_entity_name": result.get("original_name"),
                "standard_name": result.get("standard_name"),
                "status": ProcessingStatus.VERIFIED  # 添加状态更新
            }
        else:
            logger.debug(f"未找到匹配结果: query={state['identified_entity_name']}")
            return {
                "retrieved_entity_name": None,
                "standard_name": None,
                "status": ProcessingStatus.UNVERIFIED  # 添加状态更新
            }

    except Exception as e:
        error_msg = f"检索失败: {str(e)}"
        logger.error(error_msg)
        return {
            "retrieved_entity_name": None,
            "standard_name": None,
            "status": ProcessingStatus.ERROR,
            "error_message": error_msg
        }