from typing import List, Dict, Optional
from pydantic import BaseModel
from backend.resume_management.recommendation.recommendation_state import (
    QueryRefinement,
)
from utils.llm_tools import LanguageModelChain, init_language_model
from langfuse.callback import CallbackHandler
import uuid

# 初始化语言模型
language_model = init_language_model()


class RecommendationRequirements:
    def __init__(self):
        self.query_history: List[str] = []
        self.refined_query: Optional[str] = None
        self.current_question: Optional[str] = None
        self.session_id: str = str(uuid.uuid4())

    system_message = """
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

    human_message_template = """
    用户查询历史：
    {query_history}

    用户最新回答：
    {latest_response}

    请评估当前信息，并按照指示生成适当的响应。如果需要更多信息，请简明扼要地提出所有必要的问题。如果信息充足，请生成一个自然、流畅的查询描述。
    """

    query_refiner = LanguageModelChain(
        QueryRefinement, system_message, human_message_template, language_model
    )()

    def create_langfuse_handler(self, session_id, step):
        return CallbackHandler(
            tags=["resume_search_strategy"],
            session_id=session_id,
            metadata={"step": step},
        )

    def confirm_requirements(
        self, user_input: Optional[str] = None, session_id: Optional[str] = None
    ) -> str:
        """
        确认并完善用户的查询需求。

        Args:
            user_input (Optional[str]): 用户输入的新查询或回答
            session_id (Optional[str]): 会话ID

        Returns:
            str: 下一步操作的状态，可能是 "ready" 或 "need_more_info"
        """
        if session_id is None:
            session_id = self.session_id

        if user_input:
            self.query_history.append(user_input)
            latest_response = user_input
        else:
            latest_response = self.query_history[-1] if self.query_history else ""

        query_history_for_model = self.query_history[:-1]

        langfuse_handler = self.create_langfuse_handler(session_id, "query_refinement")
        refinement_result = self.query_refiner.invoke(
            {
                "query_history": "\n".join(query_history_for_model),
                "latest_response": latest_response,
            },
            config={"callbacks": [langfuse_handler]},
        )

        refined_query = QueryRefinement(**refinement_result)

        if refined_query.status == "ready":
            self.refined_query = refined_query.content
            self.current_question = None
            print("需求分析完成，准备开始搜索合适的简历")
        else:
            self.current_question = refined_query.content
            print("正在进一步确认您的需求")

        return refined_query.status

    def get_current_question(self) -> Optional[str]:
        """
        获取当前需要用户回答的问题。

        Returns:
            Optional[str]: 当前问题，如果没有则返回 None
        """
        return self.current_question

    def get_refined_query(self) -> Optional[str]:
        """
        获取精炼后的查询。

        Returns:
            Optional[str]: 精炼后的查询，如果尚未生成则返回 None
        """
        return self.refined_query


if __name__ == "__main__":

    def test_recommendation_requirements():
        req = RecommendationRequirements()

        # 测试初始查询
        initial_query = "我想要招一个HR"
        status = req.confirm_requirements(initial_query)
        print(f"初始查询状态: {status}")
        print(f"当前问题: {req.get_current_question()}")
        print(f"精炼后的查询: {req.get_refined_query()}")
        print("---")

        # 测试回答问题
        if status == "need_more_info" and req.get_current_question():
            answer = "5-10年工作经验，具备良好的数据分析技能，最好做过薪酬方案设计和人力成本预算管理，教育背景和行业不限。"
            status = req.confirm_requirements(answer)
            print(f"回答后状态: {status}")
            print(f"当前问题: {req.get_current_question()}")
            print(f"精炼后的查询: {req.get_refined_query()}")
            print("---")

    test_recommendation_requirements()
