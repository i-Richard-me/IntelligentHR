import logging
from typing import List, Dict, Any, Tuple
import pandas as pd

from backend.data_processing.table_operation_assistant.table_operation_core import (
    create_dataframe_assistant,
    process_user_query,
)
from backend.data_processing.table_operation_assistant.table_operations import (
    merge_dataframes,
    reshape_wide_to_long,
    reshape_long_to_wide,
    compare_dataframes,
)

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DataFrameWorkflow:
    """
    管理数据框操作工作流程的类。
    """

    def __init__(self):
        """
        初始化 DataFrameWorkflow 实例。
        """
        self.assistant_chain = create_dataframe_assistant()
        self.dataframes: Dict[str, pd.DataFrame] = {}
        self.available_tools = [
            merge_dataframes,
            reshape_wide_to_long,
            reshape_long_to_wide,
            compare_dataframes,
        ]
        self.conversation_history: List[Dict[str, str]] = []
        self.current_state: str = "initial"

    def load_dataframe(self, name: str, df: pd.DataFrame) -> None:
        """
        将 DataFrame 加载到工作流中。

        Args:
            name: DataFrame 的名称。
            df: 要加载的 DataFrame。
        """
        self.dataframes[name] = df
        logger.info(f"Loaded DataFrame '{name}' with shape {df.shape}")

    def process_query(self, query: str) -> Dict[str, Any]:
        """
        处理用户查询并执行相应的操作。

        Args:
            query: 用户的查询字符串。

        Returns:
            包含操作结果的字典。
        """
        logger.info(f"Processing query: {query}")
        self.conversation_history.append({"role": "user", "content": query})

        dataframe_info = self.get_dataframe_info()

        full_context = "\n".join(
            [f"{msg['role']}: {msg['content']}" for msg in self.conversation_history]
        )

        result = process_user_query(
            self.assistant_chain, full_context, dataframe_info, self.available_tools
        )
        logger.info(f"AI response: {result}")

        if result["next_step"] == "need_more_info":
            self._handle_need_more_info(result)
        elif result["next_step"] == "tool_use":
            self._handle_tool_use(result)
        else:  # out_of_scope
            self._handle_out_of_scope(result)

        return result

    def _handle_need_more_info(self, result: Dict[str, Any]) -> None:
        """
        处理需要更多信息的情况。

        Args:
            result: AI 助手的响应结果。
        """
        self.current_state = "need_more_info"
        self.conversation_history.append(
            {"role": "assistant", "content": result["message"]}
        )

    def _handle_tool_use(self, result: Dict[str, Any]) -> None:
        """
        处理使用工具的情况。

        Args:
            result: AI 助手的响应结果。
        """
        self.current_state = "ready"
        tool_name = result["operation"]["tool_name"]
        tool_args = result["operation"]["tool_args"]
        logger.info(f"Attempting to use tool: {tool_name} with args: {tool_args}")

        self._replace_dataframe_names_with_objects(tool_args)
        tool_function = self._get_tool_function(tool_name)

        if tool_function:
            try:
                tool_result = tool_function.invoke(tool_args)
                self._process_tool_result(result, tool_result)
            except Exception as e:
                logger.error(f"Error executing tool: {str(e)}")
                result["error"] = str(e)
        else:
            error_msg = f"Unknown tool: {tool_name}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def _handle_out_of_scope(self, result: Dict[str, Any]) -> None:
        """
        处理超出范围的情况。

        Args:
            result: AI 助手的响应结果。
        """
        self.current_state = "out_of_scope"
        self.conversation_history.append(
            {"role": "assistant", "content": result["message"]}
        )

    def _replace_dataframe_names_with_objects(self, tool_args: Dict[str, Any]) -> None:
        """
        将工具参数中的 DataFrame 名称替换为实际的 DataFrame 对象。

        Args:
            tool_args: 工具参数字典。
        """
        for arg, value in tool_args.items():
            if isinstance(value, str) and value in self.dataframes:
                tool_args[arg] = self.dataframes[value]
                logger.info(
                    f"Replaced dataframe name '{value}' with actual dataframe. "
                    f"Shape: {tool_args[arg].shape}, columns: {tool_args[arg].columns.tolist()}"
                )

    def _get_tool_function(self, tool_name: str) -> Any:
        """
        根据工具名称获取对应的工具函数。

        Args:
            tool_name: 工具函数的名称。

        Returns:
            对应的工具函数，如果未找到则返回 None。
        """
        return next(
            (tool for tool in self.available_tools if tool.name == tool_name), None
        )

    def _process_tool_result(self, result: Dict[str, Any], tool_result: Any) -> None:
        """
        处理工具执行的结果。

        Args:
            result: 结果字典，用于存储处理后的结果。
            tool_result: 工具执行的原始结果。
        """
        if isinstance(tool_result, tuple) and len(tool_result) == 2:
            result["result_df1"], result["result_df2"] = tool_result
            logger.info(
                f"Tool execution successful. Result 1 shape: {result['result_df1'].shape}, "
                f"Result 2 shape: {result['result_df2'].shape}"
            )
        else:
            result["result_df"] = tool_result
            logger.info(
                f"Tool execution successful. Result shape: {result['result_df'].shape}"
            )

        logger.info(
            f"First few rows of result:\n"
            f"{result['result_df'].head().to_string() if 'result_df' in result else result['result_df1'].head().to_string()}"
        )

    def get_dataframe(self, name: str) -> pd.DataFrame:
        """
        获取指定名称的 DataFrame。

        Args:
            name: DataFrame 的名称。

        Returns:
            指定名称的 DataFrame。
        """
        return self.dataframes.get(name)

    def get_dataframe_info(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有 DataFrame 的信息，包括形状和数据类型。

        Returns:
            包含所有 DataFrame 信息的字典。
        """
        return {
            name: {"shape": df.shape, "dtypes": df.dtypes.to_dict()}
            for name, df in self.dataframes.items()
        }

    def get_last_message(self) -> str:
        """
        获取最后一条消息。

        Returns:
            最后一条消息的内容，如果没有消息则返回空字符串。
        """
        return (
            self.conversation_history[-1]["content"]
            if self.conversation_history
            else ""
        )

    def reset_conversation(self) -> None:
        """
        重置对话历史和当前状态。
        """
        self.conversation_history = []
        self.current_state = "initial"
        logger.info("Conversation history and state reset")
