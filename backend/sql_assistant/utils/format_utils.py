"""
格式化工具函数模块。
提供各种数据格式化的通用函数。
"""

from typing import List, Dict
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage


def format_conversation_history(messages: List[BaseMessage]) -> str:
    """将对话历史格式化为提示词格式

    将消息列表转换为结构化的对话历史文本，用于LLM输入

    Args:
        messages: 消息历史列表

    Returns:
        str: 格式化后的对话历史
    """
    formatted = []
    for msg in messages:
        role = "用户" if isinstance(msg, HumanMessage) else "助手"
        formatted.append(f"{role}: {msg.content}")
    return "\n".join(formatted)


def format_term_descriptions(term_descriptions: Dict[str, str]) -> str:
    """格式化业务术语解释信息

    Args:
        term_descriptions: 业务术语和解释的映射字典

    Returns:
        str: 格式化后的术语解释文本
    """
    if not term_descriptions:
        return "无标准业务术语解释"

    formatted = []
    for term, desc in term_descriptions.items():
        formatted.append(f"- {term}: {desc}")
    return "\n".join(formatted)


def format_table_structures(schemas: List[Dict]) -> str:
    """格式化表结构信息

    Args:
        schemas: 表结构信息列表

    Returns:
        str: 格式化后的表结构文本
    """
    formatted = []
    for schema in schemas:
        formatted.append(f"表名: {schema['table_name']}")
        formatted.append("字段列表:")
        formatted.append("| 字段名 | 类型 | 说明 |")
        formatted.append("|--------|------|------|")
        for col in schema['columns']:
            formatted.append(
                f"| {col['name']} | {col['type']} | {col['comment']} |"
            )
        formatted.append("")  # 添加空行分隔
    return "\n".join(formatted)


def format_results_preview(execution_result: Dict) -> str:
    """格式化查询结果预览

    将查询结果格式化为易读的表格形式。
    限制预览行数，确保输出简洁。

    Args:
        execution_result: SQL执行结果字典

    Returns:
        str: 格式化后的结果预览文本
    """
    if not execution_result.get('results'):
        return "无数据"

    results = execution_result['results']
    columns = execution_result['columns']

    # 构建表格形式的预览
    lines = []
    # 表头
    lines.append("| " + " | ".join(columns) + " |")
    lines.append("|" + "|".join(["-" * len(col) for col in columns]) + "|")
    # 数据行（最多显示20行）
    for row in results[:20]:
        lines.append("| " + " | ".join(str(row[col])
                     for col in columns) + " |")
    if len(results) > 20:
        lines.append("... (更多结果省略)")

    return "\n".join(lines)