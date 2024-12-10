import logging
from typing import Dict, Any
from common.utils.llm_tools import init_language_model, LanguageModelChain
from config.config import config
from ..models.models import GraphState, AssistantResponse

logger = logging.getLogger(__name__)

# 初始化语言模型
language_model = init_language_model(
    provider=config.table_operations.llm_provider,
    model_name=config.table_operations.llm_model
)

# 系统消息
SYSTEM_MESSAGE = """
你是一个专业的数据分析助手，专门帮助用户将表格操作需求转换为 Danfo.js 命令。你的任务是理解用户的需求，并生成对应的 Danfo.js 代码。

请仔细分析用户的需求，并遵循以下规则：

1. 当用户提到"表格"时，这些表格在前端环境中已经被加载为 Danfo.js DataFrame 对象。假设用户可能不懂编程。

2. 如果用户的请求不够清晰，或者缺少必要的信息，返回 "need_more_info" 作为 next_step。用友好、通俗的语言询问更多细节。

3. 只有在充分理解用户需求，并确定 Danfo.js 确实无法完成任务的情况下，才返回 "out_of_scope" 作为 next_step。

4. 如果用户的请求清晰且可以使用 Danfo.js 完成，返回 "execute_command" 作为 next_step，并在 command 中提供完整的代码。

5. 生成的 Danfo.js 命令规范：
   - 使用正确的 API 语法和分号分隔
   - 确保执行顺序和数据类型兼容
   - 为输出 DataFrame 指定合适变量名

6. 输出变量规范：
   - 使用驼峰命名法，如 filteredSales
   - 变量名要反映数据内容
   - 提供简短的中文描述，突出数据含义
   例如：✓ "各地区季度销售额" | ✗ "按地区分组后的数据"

7. 在一个 command 中处理所有相关操作，不要拆分成多个步骤。

8. 必须使用 const 声明变量，使用 await 处理异步操作。

9. 智能判断可能存在的字段名差异，合理处理字段名映射。

10. 如果用户诉求需要多个需要展示的结果，要在 outputs 中列出所有需要展示的变量及其描述。

Output your answer as a JSON object that conforms to the AssistantResponse schema, which includes:
- next_step: "need_more_info" | "execute_command" | "out_of_scope"
- command: 
    - code: The complete Danfo.js code to execute
    - outputs: Array of output information, each containing:
        - var_name: Name of the output variable
        - description: Short description of what the variable contains
- message: Optional string containing response message

根据这些指导原则，仔细分析用户的输入并提供相应的响应。
"""

# 人类消息模板
HUMAN_MESSAGE_TEMPLATE = """
当前用户上传的表格及其信息：

{dataframe_info}

用户输入：
{user_input}

请分析用户的需求，并根据系统消息中的指导原则提供相应的响应。记住输出要符合 AssistantResponse 的格式要求。
"""


async def analysis_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """分析用户需求并生成 Danfo.js 命令"""
    try:
        logger.info("开始分析用户需求")

        # 创建语言模型链
        assistant_chain = LanguageModelChain(
            AssistantResponse,
            SYSTEM_MESSAGE,
            HUMAN_MESSAGE_TEMPLATE,
            language_model
        )()

        # 准备输入数据
        input_data = {
            "user_input": state["user_input"],
            "dataframe_info": state["dataframe_info"]
        }

        # 执行分析
        response_dict = await assistant_chain.ainvoke(input_data)

        # 验证响应格式
        logger.info(f"分析完成，响应: {response_dict}")

        # 验证响应
        if not isinstance(response_dict, dict):
            logger.error(f"响应格式错误，不是字典: {type(response_dict)}")
            raise ValueError("响应格式错误")

        if "next_step" not in response_dict:
            logger.error("响应缺少必要字段 'next_step'")
            raise ValueError("响应格式不完整")

        # 将响应添加到状态
        state_update = {"assistant_response": response_dict}
        logger.info(f"更新状态: {state_update}")
        return state_update

    except Exception as e:
        error_msg = f"分析失败: {str(e)}"
        logger.error(error_msg)
        return {"error_message": error_msg}


def should_continue(state: Dict[str, Any]) -> str:
    """确定是否继续执行工作流

    Args:
        state: 当前状态字典

    Returns:
        str: "end" 因为这是最后一个节点
    """
    return "end"