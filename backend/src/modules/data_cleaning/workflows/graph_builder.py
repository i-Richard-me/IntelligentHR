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

def should_end_after_validation(state: GraphState) -> Literal["continue", "end"]:
    """验证后的路由条件"""
    return "end" if not state["is_valid"] else "continue"

def should_end_after_analysis(state: GraphState) -> Literal["continue", "end"]:
    """分析后的路由条件"""
    return "end" if not state["is_identified"] else "continue"

def build_graph(
    enable_validation: bool = True,
    enable_search: bool = True,
    enable_retrieval: bool = True
) -> StateGraph:
    """
    构建数据清洗工作流图

    Args:
        enable_validation: 是否启用验证步骤
        enable_search: 是否启用搜索步骤
        enable_retrieval: 是否启用检索步骤

    Returns:
        构建好的状态图
    """
    # 创建状态图构建器
    graph = StateGraph(GraphState)

    # 确定第一个节点
    first_node = (
        "validation" if enable_validation
        else "search" if enable_search
        else "verification"
    )

    # 添加必要的节点
    if enable_validation:
        graph.add_node("validation", validation_node)

    if enable_search:
        graph.add_node("search", search_results_node)
        graph.add_node("analysis", entity_analysis_node)

    if enable_retrieval:
        graph.add_node("retrieval", retrieval_node)

    # 验证节点始终存在
    graph.add_node("verification", verification_node)

    # 设置边
    graph.add_edge(START, first_node)

    # 添加节点之间的连接
    if enable_validation:
        next_node = "search" if enable_search else "verification"
        graph.add_conditional_edges(
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
            graph.add_edge("search", "analysis")
            graph.add_conditional_edges(
                "analysis",
                should_end_after_analysis,
                {
                    "continue": next_node,
                    "end": "verification"
                }
            )
        else:
            graph.add_edge("search", "analysis")
            graph.add_conditional_edges(
                "analysis",
                should_end_after_analysis,
                {
                    "continue": next_node,
                    "end": END
                }
            )

    if enable_retrieval:
        graph.add_edge("retrieval", "verification")

    # 最后一个节点到结束的边
    graph.add_edge("verification", END)
    
    return graph