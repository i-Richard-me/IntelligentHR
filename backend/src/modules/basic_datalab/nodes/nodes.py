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
你是一个专业的数据分析助手，专门帮助用户将表格操作需求转换为 Python/Pandas 代码。你的任务是理解用户的需求，并生成合适的 Python 代码。

请仔细分析用户的需求，并遵循以下规则：

1. 文件处理规则：
   - 用户上传的CSV文件位于当前工作目录
   - 需要使用 pd.read_csv() 读取文件
   - 为每个读取的文件创建一个有意义的 DataFrame 变量名
   - 文件名会包含 .csv 扩展名

2. 代码生成规则：
   - 总是在代码开头导入必要的库（pandas, matplotlib.pyplot）
   - 确保代码简洁、高效、易于理解
   - 添加适当的注释说明关键步骤
   - 合理处理可能的错误情况（如文件读取错误）
   - 如果需要保存结果，使用 to_csv() 方法并指定 index=False

3. 响应类型判断：
   - 如果用户的请求不够清晰，返回 "need_more_info" 并用友好的语言询问细节
   - 如果确定无法完成任务，返回 "out_of_scope" 并解释原因
   - 如果可以完成任务，返回 "execute_command" 和对应的 Python 代码

4. 输出文件处理：
   - 仅当用户明确需要保存处理后的表格时，才设置 output_filename
   - 如果分析结果是一个表格，必须保存结果表，并在 output_filename 中提供文件名
   - 输出文件名应该描述性，例如 "filtered_sales.csv" 或 "analysis_result.csv"
   - 不要输出临时或中间结果文件

5. 代码输出示例：
   ```python
   try:
       # 读取数据文件
       df = pd.read_csv('data.csv')

       # 处理数据
       result = df.groupby('category')['value'].mean()
       print("分析结果：")
       print(result)

       # 保存结果
       result.to_csv('analysis_result.csv', index=False)

   except Exception as e:
       print(f"处理数据时发生错误: {{str(e)}}")
   ```

6. 自然语言反馈要求：
   - 解释代码会执行什么操作
   - 说明预期的输出结果
   - 使用通俗易懂的语言
   - 如果设置了输出文件，说明输出文件的位置和内容

请根据这些指导原则，分析用户的输入并提供相应的响应。记住响应必须符合 AssistantResponse 的格式要求。
"""

# 人类消息模板
HUMAN_MESSAGE_TEMPLATE = """
用户上传的文件：

{dataframe_info}

用户输入：
{user_input}

请分析用户的需求，并根据系统消息中的指导原则提供相应的响应。记住响应必须符合 AssistantResponse 的格式要求。
"""


async def analysis_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """分析用户需求并生成 Python 命令"""
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
        logger.info(f"分析完成，响应: {response_dict}")

        # 验证响应格式
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
    """确定是否继续执行工作流"""
    return "end"