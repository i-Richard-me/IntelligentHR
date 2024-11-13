"""
节点路由模块。
定义了状态图中各节点间的路由逻辑。
"""

from langgraph.graph import END

from backend.sql_assistant.states.assistant_state import SQLAssistantState


def route_after_intent(state: SQLAssistantState):
    """意图分析后的路由函数

    根据意图分析结果决定下一个处理节点。
    如果意图不明确，结束对话要求澄清；否则继续处理。

    Args:
        state: 当前状态对象

    Returns:
        str: 下一个节点的标识符
    """
    if not state["is_intent_clear"]:
        return END
    return "keyword_extraction"


def route_after_sql_generation(state: SQLAssistantState):
    """SQL生成后的路由函数

    根据SQL生成结果决定下一步操作。
    如果生成成功则执行SQL，否则结束处理。

    Args:
        state: 当前状态对象

    Returns:
        str: 下一个节点的标识符
    """
    generated_sql = state.get("generated_sql", {})
    if not generated_sql or not generated_sql.get('is_feasible'):
        return END
    return "sql_execution"


def route_after_execution(state: SQLAssistantState):
    """SQL执行后的路由函数

    根据SQL执行结果决定下一步操作。
    执行成功则进入结果反馈，失败则进入错误分析。

    Args:
        state: 当前状态对象

    Returns:
        str: 下一个节点的标识符
    """
    execution_result = state.get("execution_result", {})
    if execution_result.get('success', False):
        return "result_generation"  # 执行成功，生成结果反馈
    return "error_analysis"  # 执行失败，进入错误分析


def route_after_error_analysis(state: SQLAssistantState):
    """错误分析后的路由函数

    根据错误分析结果决定下一步操作。
    如果错误可修复，则使用修复后的SQL重新执行；
    否则结束处理流程。

    Args:
        state: 当前状态对象

    Returns:
        str: 下一个节点的标识符
    """
    error_analysis_result = state.get("error_analysis_result", {})
    if error_analysis_result.get("is_sql_fixable", False):
        # 如果是可修复的SQL错误，更新生成的SQL并重新执行
        state["generated_sql"] = {
            "is_feasible": True,
            "sql_query": error_analysis_result["fixed_sql"]
        }
        return "sql_execution"
    return END  # 如果不是SQL问题，结束流程
