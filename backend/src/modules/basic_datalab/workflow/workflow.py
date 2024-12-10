import logging
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from ..models.models import GraphState, AssistantResponse
from ..nodes.nodes import analysis_node, should_continue

logger = logging.getLogger(__name__)

class BasicDatalabWorkflow:
    """基础数据工坊工作流类"""

    def __init__(self):
        """初始化工作流"""
        self.workflow = self._build_graph()
        logger.info("基础数据工坊工作流初始化完成")

    def _build_graph(self) -> StateGraph:
        """构建工作流图"""
        try:
            logger.info("开始构建工作流图")

            # 创建工作流图
            workflow = StateGraph(GraphState)

            # 添加分析节点
            workflow.add_node("analysis", analysis_node)

            # 设置入口点
            workflow.set_entry_point("analysis")

            # 添加到结束的边
            workflow.add_conditional_edges(
                "analysis",
                should_continue,
                {
                    "end": END
                }
            )

            logger.info("工作流图构建完成")
            return workflow

        except Exception as e:
            error_msg = f"构建工作流图失败: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    async def process_request(
            self,
            user_input: str,
            dataframe_info: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """处理用户请求

        Args:
            user_input: 用户的处理需求
            dataframe_info: 上传文件的信息

        Returns:
            Dict[str, Any]: 包含生成的Python代码或其他响应信息
        """
        try:
            logger.info(f"开始处理用户请求: {user_input}")

            # 验证输入
            if not user_input or not user_input.strip():
                raise ValueError("用户输入不能为空")
            if not dataframe_info:
                raise ValueError("文件信息不能为空")

            # 准备初始状态
            initial_state = {
                "messages": [],
                "user_input": user_input,
                "dataframe_info": dataframe_info,
                "assistant_response": None,
                "error_message": None
            }

            logger.info("初始状态已准备")

            # 编译并执行工作流
            logger.info("开始编译工作流")
            compiled_workflow = self.workflow.compile()

            logger.info("执行工作流")
            result = await compiled_workflow.ainvoke(initial_state)

            logger.info(f"工作流执行完成，结果: {result}")

            # 检查是否有错误
            if result.get("error_message"):
                error_msg = f"处理请求时发生错误: {result['error_message']}"
                logger.error(error_msg)
                return {
                    "next_step": "out_of_scope",
                    "command": None,
                    "message": error_msg
                }

            # 获取助手响应
            assistant_response = result.get("assistant_response")
            logger.info(f"助手响应: {assistant_response}")

            if not assistant_response:
                logger.error("未获取到助手响应")
                return {
                    "next_step": "out_of_scope",
                    "command": None,
                    "message": "未能生成有效的响应"
                }

            # 直接返回响应字典
            return assistant_response

        except Exception as e:
            error_msg = f"处理请求失败: {str(e)}"
            logger.error(error_msg)
            return {
                "next_step": "out_of_scope",
                "command": None,
                "message": error_msg
            }

    @classmethod
    def create(cls) -> 'BasicDatalabWorkflow':
        """创建工作流实例"""
        return cls()