"""
图构建器，负责构建和配置 LangGraph 数据清洗工作流图
"""
from typing import Dict, Literal
from langgraph.graph import StateGraph, START, END
from ..models.state import GraphState, ProcessingStatus
from ..nodes.validation_node import validation_node
from ..nodes.search_results_node import search_results_node
from ..nodes.entity_analysis_node import entity_analysis_node
from ..nodes.retrieval_node import retrieval_node
from ..nodes.verification_node import verification_node
import logging

logger = logging.getLogger(__name__)

def should_end_after_validation(state: GraphState) -> Literal["continue", "end"]:
    """验证后的路由条件"""
    if state.get("status") == ProcessingStatus.ERROR:
        logger.warning(f"验证步骤出错: {state.get('error_message')}")
        return "end"
    return "end" if not state["is_valid"] else "continue"

def should_end_after_analysis(state: GraphState) -> Literal["continue", "end"]:
    """分析后的路由条件"""
    if state.get("status") == ProcessingStatus.ERROR:
        logger.warning(f"分析步骤出错: {state.get('error_message')}")
        return "end"
    return "end" if not state["is_identified"] else "continue"

def build_graph(
    enable_validation: bool = True,
    enable_search: bool = True,
    enable_retrieval: bool = True
) -> StateGraph:
    """构建数据清洗工作流图

    Args:
        enable_validation: 是否启用验证步骤
        enable_search: 是否启用搜索步骤
        enable_retrieval: 是否启用检索步骤

    Returns:
        构建好的状态图
    """
    try:
        # 创建状态图构建器
        workflow_graph = StateGraph(GraphState)
        logger.info(f"开始构建工作流图: validation={enable_validation}, "
                   f"search={enable_search}, retrieval={enable_retrieval}")

        # 确定第一个节点
        first_node = (
            "validation" if enable_validation
            else "search" if enable_search
            else "verification"
        )

        # 添加必要的节点
        if enable_validation:
            workflow_graph.add_node("validation", validation_node)
            logger.debug("添加验证节点")

        if enable_search:
            workflow_graph.add_node("search", search_results_node)
            workflow_graph.add_node("analysis", entity_analysis_node)
            logger.debug("添加搜索和分析节点")

        if enable_retrieval:
            workflow_graph.add_node("retrieval", retrieval_node)
            logger.debug("添加检索节点")

        # 验证节点始终存在
        workflow_graph.add_node("verification", verification_node)
        logger.debug("添加最终验证节点")

        # 设置边
        workflow_graph.add_edge(START, first_node)

        # 添加节点之间的连接
        if enable_validation:
            next_node = "search" if enable_search else "verification"
            workflow_graph.add_conditional_edges(
                "validation",
                should_end_after_validation,
                {
                    "continue": next_node,
                    "end": END
                }
            )

        if enable_search:
            next_node = "retrieval" if enable_retrieval else "verification"
            if enable_retrieval:
                workflow_graph.add_edge("search", "analysis")
                workflow_graph.add_conditional_edges(
                    "analysis",
                    should_end_after_analysis,
                    {
                        "continue": next_node,
                        "end": "verification"
                    }
                )
            else:
                workflow_graph.add_edge("search", "analysis")
                workflow_graph.add_conditional_edges(
                    "analysis",
                    should_end_after_analysis,
                    {
                        "continue": next_node,
                        "end": END
                    }
                )

        if enable_retrieval:
            workflow_graph.add_edge("retrieval", "verification")

        # 最后一个节点到结束的边
        workflow_graph.add_edge("verification", END)

        logger.info("工作流图构建完成")
        return workflow_graph

    except Exception as e:
        logger.error(f"构建工作流图失败: {str(e)}")
        raise