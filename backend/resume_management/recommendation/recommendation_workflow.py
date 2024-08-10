from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from backend.resume_management.recommendation.recommendation_state import ResumeRecommendationState
from backend.resume_management.recommendation.recommendation_requirements import (
    confirm_requirements,
    get_user_input,
    determine_next_step,
)
from backend.resume_management.recommendation.resume_search_strategy import (
    generate_resume_search_strategy,
    generate_collection_search_strategy,
)
from backend.resume_management.recommendation.resume_scorer import calculate_overall_resume_scores
from backend.resume_management.recommendation.recommendation_output_generator import (
    fetch_resume_details,
    prepare_final_output,
)
from backend.resume_management.recommendation.recommendation_reason_generator import (
    generate_recommendation_reasons,
)


def create_workflow() -> StateGraph:
    """
    创建并配置简历推荐工作流程。

    Returns:
        StateGraph: 配置好的工作流程图。
    """
    workflow = StateGraph(ResumeRecommendationState)

    # 添加所有节点
    workflow.add_node("confirm_requirements", confirm_requirements)
    workflow.add_node("get_user_input", get_user_input)
    workflow.add_node(
        "generate_resume_search_strategy", generate_resume_search_strategy
    )
    workflow.add_node(
        "generate_collection_search_strategy", generate_collection_search_strategy
    )
    workflow.add_node(
        "calculate_overall_resume_scores", calculate_overall_resume_scores
    )
    workflow.add_node("fetch_resume_details", fetch_resume_details)
    workflow.add_node(
        "generate_recommendation_reasons", generate_recommendation_reasons
    )
    workflow.add_node("prepare_final_output", prepare_final_output)

    # 设置入口点
    workflow.set_entry_point("confirm_requirements")

    # 添加边
    workflow.add_conditional_edges(
        "confirm_requirements",
        determine_next_step,
        {
            "ready": "generate_resume_search_strategy",
            "need_more_info": "get_user_input",
        },
    )
    workflow.add_edge("get_user_input", "confirm_requirements")
    workflow.add_edge(
        "generate_resume_search_strategy", "generate_collection_search_strategy"
    )
    workflow.add_edge(
        "generate_collection_search_strategy", "calculate_overall_resume_scores"
    )
    workflow.add_edge("calculate_overall_resume_scores", "fetch_resume_details")
    workflow.add_edge("fetch_resume_details", "generate_recommendation_reasons")
    workflow.add_edge("generate_recommendation_reasons", "prepare_final_output")
    workflow.add_edge("prepare_final_output", END)

    # 设置内存保存器
    memory = MemorySaver()

    # 编译工作流，添加断点
    return workflow.compile(
        checkpointer=memory,
        interrupt_before=[
            "get_user_input",
            "generate_resume_search_strategy",
            "generate_collection_search_strategy",
            "calculate_overall_resume_scores",
            "fetch_resume_details",
            "generate_recommendation_reasons",
            "prepare_final_output",
        ],
    )


# 创建工作流实例
app = create_workflow()
