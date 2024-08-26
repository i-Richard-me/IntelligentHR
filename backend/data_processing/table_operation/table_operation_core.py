import logging
import os
from typing import List, Dict, Any, Optional

import uuid
import json
from langfuse import Langfuse
from langfuse.callback import CallbackHandler

from langchain_core.tools import tool

from backend.data_processing.table_operation.table_operation_models import (
    AssistantResponse,
)
from pymilvus import connections, Collection
from utils.llm_tools import LanguageModelChain, init_language_model, CustomEmbeddings

# 初始化日志记录
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

langfuse_client = Langfuse()

# 初始化语言模型
language_model = init_language_model()

# 系统消息
SYSTEM_MESSAGE = """
你是一个专业的数据分析助手，专门帮助用户进行表格操作。你的任务是理解用户的需求，并使用提供的工具函数来操作表格。你能够处理简单的单步操作，也能处理需要多个步骤才能完成的复杂用户需求。

请仔细分析用户的需求，并遵循以下规则：

1. 当用户提到"表格"时，他们指的是已经加载到环境中的DataFrame变量。对用户而言，这些是他们上传的表格。假设用户可能不懂Python编程。

2. 如果用户的请求不够清晰，或者缺少必要的信息，优先选择返回 "need_more_info" 作为 next_step。用友好、通俗的语言询问更多细节，帮助用户阐明他们的需求。避免使用专业术语，如"DataFrame"、"inner"、"left join"等。相反，使用"表格"、"保留左边表格的所有数据"等更容易理解的表述。

3. 只有在充分理解用户需求，并确定现有工具函数确实无法完成任务的情况下，才返回 "out_of_scope" 作为 next_step。

4. 如果用户的请求清晰且可以使用提供的工具函数完成，返回 "execute_operation" 作为 next_step，并提供完整的操作步骤列表。

5. 根据任务需求判断是否需要多个步骤：
   a. 如果用户的需求可以用单一工具完成，就不要拆分步骤。
   b. 如果需求无法用单一工具完成，但可以通过多个工具组合完成，则将任务分解为必要的操作步骤。
   c. 为每个步骤生成一个 OperationStep，包括 tool_name, tool_args, 和 output_df_names。

6. 在生成 tool_args 时，使用环境中的原始表格名称或前面步骤的输出作为输入。

7. 对于 output_df_names：
   a. output_df_names 应该是能体现任务意图且用户友好的名称，因为它会作为用户下载时的文件名称。
   b. 某些工具（如 compare_dataframes）可能输出多个 DataFrame，因此使用列表来存储输出名称。
   c. 确保根据调用的函数输出是一个还是多个 DataFrame，在 output_df_names 列表中提供相应数目的名称。

8. 在选择操作和提供建议时，充分考虑每个表格的数据类型信息。

9. 智能判断可能存在的字段名称差异。例如，用户提到的"工号"可能对应表格中的"员工ID"，"部门"可能对应"部门名称"，"base地"可能对应"工作地点"等。如果你能够合理推断出用户指代的是哪个字段，就直接在响应中使用正确的字段名。在无法判断的情况下，应询问用户以澄清。

10. 如果用户的请求有一些模糊但可以推测的部分，可以提出你的猜测并询问是否正确。

11. 在回答中，先重述你对用户需求的理解，然后再给出建议或请求更多信息。

请根据这些指导原则，仔细分析用户的输入并提供相应的响应。你的目标是尽可能帮助用户完成他们的表格操作需求，即使这可能需要多次交互来澄清和细化需求。只有在确定无法提供任何有用帮助时，才考虑使用 "out_of_scope"。
"""

# 人类消息模板
HUMAN_MESSAGE_TEMPLATE = """
可用的表格操作的工具函数如下：

{tools_description}

以下是一个示例，你可以参考这个示例来执行用户的需求(但用户的实际需求与示例可能不同，请不要直接使用示例中的操作步骤，而是根据用户的需求重新生成操作步骤):

{example}

当前用户上传的表格及其信息：

{dataframe_info}

用户输入：
{user_input}

请分析用户的需求，并根据系统消息中的指导原则提供相应的响应。
"""


def create_langfuse_handler(session_id: str, step: str) -> CallbackHandler:
    """
    创建 Langfuse CallbackHandler。

    Args:
        session_id: 会话ID。
        step: 当前步骤名称。

    Returns:
        配置好的 Langfuse CallbackHandler。
    """
    return CallbackHandler(
        tags=["table_operation"], session_id=session_id, metadata={"step": step}
    )


def record_user_feedback(trace_id: str, is_useful: bool):
    langfuse_client.score(
        trace_id=trace_id, name="feedback", value=is_useful, data_type="BOOLEAN"
    )


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
            f"函数名：{tool.name}\n描述：{tool.description}\n\n参数：{tool.args}\n"
        )
    return "\n".join(descriptions)


def create_dataframe_assistant():
    """
    创建 DataFrame 操作助手。

    Returns:
        配置好的语言模型链。
    """
    assistant_chain = LanguageModelChain(
        AssistantResponse, SYSTEM_MESSAGE, HUMAN_MESSAGE_TEMPLATE, language_model
    )()

    return assistant_chain


def get_similar_example(
    query: str, collection_name: str = "data_operation_examples"
) -> Dict[str, str]:
    """
    从Milvus检索与用户查询最相似的示例
    """
    connections.connect(
        alias="default", host="localhost", port="19530", db_name="examples"
    )

    collection = Collection(collection_name)
    collection.load()

    embeddings = CustomEmbeddings(
        api_key=os.getenv("EMBEDDING_API_KEY"),
        api_url=os.getenv("EMBEDDING_API_BASE"),
        model=os.getenv("EMBEDDING_MODEL"),
    )
    query_vector = embeddings.embed_query(query)

    search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
    results = collection.search(
        data=[query_vector],
        anns_field="embedding",
        param=search_params,
        limit=1,
        output_fields=["user_tables", "user_query", "output"],
    )

    if results[0]:
        similar_example = {
            "用户上传的表格": results[0][0].entity.get("user_tables"),
            "用户查询": results[0][0].entity.get("user_query"),
            "输出": results[0][0].entity.get("output"),
        }
        return similar_example
    else:
        return {}  # 返回空的示例，如果没找到相似的


def format_example(example: Dict[str, str]) -> str:
    """
    将示例格式化为易读的文本格式。
    """
    if not example:
        return "{}"

    formatted = "{\n"
    for key, value in example.items():
        formatted += f"{key}: \n{value}\n\n"
    formatted += "}"
    return formatted


def process_user_query(
    assistant_chain,
    user_input: str,
    dataframe_info: Dict[str, Dict],
    tools: List[tool],
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    处理用户查询并返回结果。
    """
    try:
        if session_id is None:
            session_id = str(uuid.uuid4())

        langfuse_handler = create_langfuse_handler(session_id, "process_user_query")

        tools_description = get_tools_description(tools)
        dataframe_info_str = format_dataframe_info(dataframe_info)

        # 获取相似的示例
        similar_example = get_similar_example(user_input)
        example_str = format_example(similar_example)

        input_data = {
            "user_input": user_input,
            "example": example_str,
            "tools_description": tools_description,
            "dataframe_info": dataframe_info_str,
        }

        logger.info(f"Processing user query: {user_input}")
        result = assistant_chain.invoke(
            input_data, config={"callbacks": [langfuse_handler]}
        )

        trace_id = langfuse_handler.get_trace_id()
        result["trace_id"] = trace_id

        logger.info(f"Query processed successfully. Result: {result}")

        return result

    except Exception as e:
        logger.error(f"Error processing user query: {str(e)}")
        raise ValueError(f"处理查询时发生错误: {str(e)}")


def format_dataframe_info(dataframe_info: Dict[str, Dict]):
    """
    格式化DataFrame信息为字符串。

    Args:
        dataframe_info: DataFrame信息字典。

    Returns:
        格式化后的DataFrame信息字符串。
    """
    return dataframe_info.items()
