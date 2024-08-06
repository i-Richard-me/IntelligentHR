import logging
from typing import List, Dict, Any

from langchain_core.tools import tool

from backend.data_processing.table_operation_assistant.table_operation_models import (
    AssistantResponse,
)
from backend.data_processing.table_operation_assistant.table_operations import (
    merge_dataframes,
    reshape_wide_to_long,
    reshape_long_to_wide,
    compare_dataframes,
)
from utils.llm_tools import LanguageModelChain, init_language_model


# 初始化日志记录
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 初始化语言模型
language_model = init_language_model()

# 系统消息
SYSTEM_MESSAGE = """
你是一个专业的数据分析助手，专门帮助用户进行表格操作。你的任务是理解用户的需求，并使用提供的工具函数来操作表格。

请仔细分析用户的需求，并遵循以下规则：

1. 当用户提到"表格"时，他们指的是已经加载到环境中的DataFrame变量。对用户而言，这些是他们上传的表格。假设用户可能不懂Python编程。

2. 如果用户的请求不够清晰，或者缺少必要的信息，优先选择返回 "need_more_info" 作为 next_step。用友好、通俗的语言询问更多细节，帮助用户阐明他们的需求。

3. 只有在充分理解用户需求，并确定现有工具函数确实无法完成任务的情况下，才返回 "out_of_scope" 作为 next_step。

4. 如果用户的请求清晰且可以使用提供的工具函数完成，返回 "tool_use" 作为 next_step，并提供正确的 tool_name 和 tool_args。

5. 在生成 tool_args 时，确保使用环境中可用的表格名称（即DataFrame变量名称）。

6. 始终使用中文与用户交流，保持友好、通俗易懂的语气。避免使用专业术语，如"DataFrame"、"inner"、"left join"等。相反，使用"表格"、"保留左边表格的所有数据"等更容易理解的表述。

7. 在选择操作和提供建议时，充分考虑每个表格的数据类型信息。

8. 如果用户的请求有一些模糊但可以推测的部分，可以提出你的猜测并询问是否正确。

9. 在回答中，先重述你对用户需求的理解，然后再给出建议或请求更多信息。这有助于确保你正确理解了用户的意图。

请根据这些指导原则，仔细分析用户的输入并提供相应的响应。你的目标是尽可能帮助用户完成他们的表格操作需求，即使这可能需要多次交互来澄清和细化需求。只有在确定无法提供任何有用帮助时，才考虑使用 "out_of_scope"。
"""

# 人类消息模板
HUMAN_MESSAGE_TEMPLATE = """
可用的表格操作的工具函数如下：

{tools_description}

当前环境中可用的 DataFrame 变量及其信息：
{dataframe_info}

用户输入：
{user_input}

请分析用户的需求，并根据系统消息中的指导原则提供相应的响应。
"""


def get_tools_description(tools: List[tool]) -> str:
    """
    获取工具函数的描述。

    Args:
        tools: 工具函数列表。

    Returns:
        包含所有工具函数描述的字符串。
    """
    descriptions = []
    for tool in tools:
        descriptions.append(
            f"函数名：{tool.name}\n描述：{tool.description}\n参数：{tool.args}\n"
        )
    return "\n".join(descriptions)


def create_dataframe_assistant() -> LanguageModelChain:
    """
    创建 DataFrame 操作助手。

    Returns:
        配置好的语言模型链。
    """
    assistant_chain = LanguageModelChain(
        AssistantResponse, SYSTEM_MESSAGE, HUMAN_MESSAGE_TEMPLATE, language_model
    )()

    return assistant_chain


def process_user_query(
    assistant_chain: LanguageModelChain,
    user_input: str,
    dataframe_info: Dict[str, Dict],
    tools: List[tool],
) -> Dict[str, Any]:
    """
    处理用户查询，生成相应的响应。

    Args:
        assistant_chain: 配置好的语言模型链。
        user_input: 用户输入的查询。
        dataframe_variables: 可用的DataFrame变量名列表。
        dataframe_info: DataFrame信息字典。
        tools: 可用的工具函数列表。

    Returns:
        包含处理结果的字典。

    Raises:
        ValueError: 当处理查询时发生错误。
    """
    try:
        tools_description = get_tools_description(tools)
        dataframe_info_str = format_dataframe_info(dataframe_info)

        input_data = {
            "user_input": user_input,
            "tools_description": tools_description,
            "dataframe_info": dataframe_info_str,
        }

        logger.info(f"Processing user query: {user_input}")
        result = assistant_chain.invoke(input_data)
        logger.info(f"Query processed successfully. Result: {result}")

        return result

    except Exception as e:
        logger.error(f"Error processing user query: {str(e)}")
        raise ValueError(f"处理查询时发生错误: {str(e)}")


def format_dataframe_info(dataframe_info: Dict[str, Dict]) -> str:
    """
    格式化DataFrame信息为字符串。

    Args:
        dataframe_info: DataFrame信息字典。

    Returns:
        格式化后的DataFrame信息字符串。
    """
    info_str = ""
    for name, info in dataframe_info.items():
        info_str += f"{name}:\n"
        info_str += f"  形状: {info['shape']}\n"
        info_str += "  列及其数据类型:\n"
        for col, dtype in info["dtypes"].items():
            info_str += f"    {col}: {dtype}\n"
        info_str += "\n"
    return info_str
