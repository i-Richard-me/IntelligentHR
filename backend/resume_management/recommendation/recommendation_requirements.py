from typing import Dict
from backend.resume_management.recommendation.recommendation_state import (
    QueryRefinement,
)
from utils.llm_tools import LanguageModelChain, init_language_model

# 初始化语言模型
language_model = init_language_model()

SYSTEM_MESSAGE = """
你是一个智能简历推荐系统的预处理助手。你的任务是评估并完善用户的查询，以生成精确的简历检索策略。请遵循以下指南：

1. 分析用户的查询，关注以下关键方面（无需涵盖所有方面）：
   - 工作经历：对职位、工作职责、工作经验的要求
   - 项目经历: 对过往特定项目和工作的要求
   - 技能：对必要的专业技能、工具使用能力的要求
   - 教育背景：对学历、专业的要求
   - 个人特质：对个人特点或其他方面的要求

2. 评估查询的完整性：
   - 如果查询已经包含足够的信息（至少涵盖2-3个关键方面），直接完善并总结查询。
   - 如果信息不足（只提到1-2个方面）或不明确，生成简洁的问题以获取必要信息。

3. 当需要更多信息时：
   - 提出简洁、有针对性的问题，一次性列出所有需要澄清的点。
   - 将输出状态设置为 "need_more_info"。

4. 当信息充足时：
   - 总结并完善查询，确保它是一个流畅、自然的句子或段落，类似于用户的原始输入方式。
   - 将输出状态设置为 "ready"。

请记住，目标是在最少的交互中获得有效信息，生成自然、流畅的查询描述，而不是格式化的列表。
"""

HUMAN_MESSAGE_TEMPLATE = """
用户查询历史：
{query_history}

用户最新回答：
{latest_response}

请评估当前信息，并按照指示生成适当的响应。如果需要更多信息，请简明扼要地提出所有必要的问题。如果信息充足，请生成一个自然、流畅的查询描述。
"""

query_refiner = LanguageModelChain(
    QueryRefinement, SYSTEM_MESSAGE, HUMAN_MESSAGE_TEMPLATE, language_model
)()


def confirm_requirements(state: Dict) -> Dict:
    """
    确认并完善用户的查询需求。

    Args:
        state (Dict): 当前状态字典。

    Returns:
        Dict: 更新后的状态字典。
    """
    if state["user_input"]:
        state["query_history"].append(state["user_input"])
        latest_response = state["user_input"]
    else:
        latest_response = state["query_history"][-1]

    query_history_for_model = state["query_history"][:-1]

    refinement_result = query_refiner.invoke(
        {
            "query_history": "\n".join(query_history_for_model),
            "latest_response": latest_response,
        },
    )

    refined_query = QueryRefinement(**refinement_result)

    state["status"] = refined_query.status
    state["query_history"].append(refined_query.content)
    state["user_input"] = None  # 重置用户输入

    if refined_query.status == "ready":
        state["refined_query"] = refined_query.content
        state["current_question"] = None
        print("需求分析完成，准备开始搜索合适的简历")
    else:
        state["current_question"] = refined_query.content
        print("正在进一步确认您的需求")

    return state


def get_user_input(state: Dict) -> Dict:
    """
    获取用户输入并更新查询历史。

    Args:
        state (Dict): 当前状态字典。

    Returns:
        Dict: 更新后的状态字典。

    Note:
        这个函数是一个占位符，实际实现可能在其他地方。
    """
    # 这个函数不会被直接调用，而是作为一个占位符
    return state


def determine_next_step(state: Dict) -> str:
    """
    根据查询完善结果确定下一步操作。

    Args:
        state (Dict): 当前状态字典。

    Returns:
        str: 下一步操作的指示，可能是 "ready" 或 "need_more_info"。
    """
    if state["status"] == "ready":
        return "ready"
    else:
        return "need_more_info"
