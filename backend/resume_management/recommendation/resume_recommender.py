import os
from typing import Dict, Optional, List
from backend.resume_management.recommendation.recommendation_requirements import (
    RecommendationRequirements,
)
from backend.resume_management.recommendation.resume_search_strategy import (
    ResumeSearchStrategyGenerator,
    CollectionSearchStrategyGenerator,
)
from backend.resume_management.recommendation.resume_scorer import ResumeScorer
from backend.resume_management.recommendation.recommendation_reason_generator import (
    RecommendationReasonGenerator,
)
from backend.resume_management.recommendation.recommendation_output_generator import (
    RecommendationOutputGenerator,
)
from langfuse.callback import CallbackHandler
import uuid


class ResumeRecommender:
    """
    简历推荐系统的主类，整合了整个推荐流程的各个组件。
    """

    def __init__(self):
        self.requirements = RecommendationRequirements()
        self.strategy_generator = ResumeSearchStrategyGenerator()
        self.collection_strategy_generator = CollectionSearchStrategyGenerator()
        self.scorer = ResumeScorer()
        self.output_generator = RecommendationOutputGenerator()
        self.reason_generator = RecommendationReasonGenerator()
        self.overall_search_strategy = None
        self.detailed_search_strategy = None
        self.ranked_resume_scores = None
        self.resume_details = None
        self.recommendation_reasons = None
        self.final_recommendations = None
        self.session_id: str = str(uuid.uuid4())

    def create_langfuse_handler(self, session_id: str, step: str) -> CallbackHandler:
        """创建 Langfuse 回调处理器"""
        return CallbackHandler(
            tags=["resume_search_strategy"],
            session_id=session_id,
            metadata={"step": step},
        )

    def process_query(self, query: str, session_id: Optional[str] = None) -> str:
        """
        处理用户的初始查询，启动推荐过程。

        Args:
            query (str): 用户的初始查询
            session_id (Optional[str]): 会话ID

        Returns:
            str: 处理状态，可能是 'need_more_info' 或 'ready'
        """
        return self.requirements.confirm_requirements(query, session_id)

    def get_next_question(self) -> Optional[str]:
        """
        获取下一个需要用户回答的问题（如果有的话）。

        Returns:
            Optional[str]: 下一个问题，如果没有则返回 None
        """
        return self.requirements.get_current_question()

    def process_answer(self, answer: str, session_id: Optional[str] = None) -> str:
        """
        处理用户对问题的回答，继续推荐过程。

        Args:
            answer (str): 用户的回答
            session_id (Optional[str]): 会话ID

        Returns:
            str: 处理状态，可能是 'need_more_info' 或 'ready'
        """
        return self.requirements.confirm_requirements(answer, session_id)

    def generate_overall_search_strategy(
        self, session_id: Optional[str] = None
    ) -> None:
        """
        生成整体简历搜索策略。

        Args:
            session_id (Optional[str]): 会话ID
        """
        if session_id is None:
            session_id = self.session_id

        refined_query = self.requirements.get_refined_query()
        if not refined_query:
            raise ValueError("未找到精炼后的查询。无法生成搜索策略。")

        self.overall_search_strategy = (
            self.strategy_generator.generate_resume_search_strategy(
                refined_query, session_id
            )
        )

    def generate_detailed_search_strategy(
        self, session_id: Optional[str] = None
    ) -> None:
        """
        生成详细的检索策略。

        Args:
            session_id (Optional[str]): 会话ID
        """
        if session_id is None:
            session_id = self.session_id

        if not self.overall_search_strategy:
            raise ValueError("缺少生成详细检索策略所需的信息。")

        self.detailed_search_strategy = (
            self.collection_strategy_generator.generate_collection_search_strategy(
                self.requirements.get_refined_query(),
                self.overall_search_strategy,
                session_id,
            )
        )

    def get_overall_search_strategy(self) -> Optional[List[Dict[str, float]]]:
        """
        获取整体搜索策略。

        Returns:
            Optional[List[Dict[str, float]]]: 整体搜索策略，如果尚未生成则返回 None
        """
        return self.overall_search_strategy

    def calculate_resume_scores(self, top_n: int = 3):
        """
        计算简历得分。

        Args:
            top_n (int): 要返回的最佳匹配简历数量
        """
        if not self.overall_search_strategy or not self.detailed_search_strategy:
            raise ValueError("搜索策略尚未生成。无法计算简历得分。")

        self.ranked_resume_scores = self.scorer.calculate_overall_resume_scores(
            self.requirements.get_refined_query(),
            self.overall_search_strategy,
            self.detailed_search_strategy,
            top_n,
        )

    def generate_recommendation_reasons(self, session_id: Optional[str] = None):
        """
        生成推荐理由。

        Args:
            session_id (Optional[str]): 会话ID
        """
        if self.resume_details is None:
            self.resume_details = self.output_generator.fetch_resume_details(
                self.ranked_resume_scores
            )

        self.recommendation_reasons = (
            self.reason_generator.generate_recommendation_reasons(
                self.requirements.get_refined_query(),
                self.resume_details,
                session_id or self.session_id,
            )
        )

    def prepare_final_recommendations(self):
        """准备最终推荐结果。"""
        if self.resume_details is None or self.recommendation_reasons is None:
            raise ValueError("简历详情或推荐理由尚未生成。无法准备最终推荐结果。")

        self.final_recommendations = self.output_generator.prepare_final_output(
            self.resume_details, self.recommendation_reasons
        )

    def get_recommendations(self) -> Optional[List[Dict]]:
        """
        获取最终的推荐结果。

        Returns:
            Optional[List[Dict]]: 推荐结果列表，如果尚未生成则返回 None
        """
        return (
            self.final_recommendations.to_dict("records")
            if self.final_recommendations is not None
            else None
        )

    def run_full_process(
        self, initial_query: str, top_n: int = 3
    ) -> Optional[List[Dict]]:
        """
        运行完整的推荐过程。

        Args:
            initial_query (str): 用户的初始查询
            top_n (int): 要推荐的简历数量

        Returns:
            Optional[List[Dict]]: 推荐结果列表，如果过程中出错则返回 None
        """
        try:
            status = self.process_query(initial_query)
            while status == "need_more_info":
                next_question = self.get_next_question()
                if next_question:
                    answer = input(f"{next_question}\n请回答: ")
                    status = self.process_answer(answer)
                else:
                    raise ValueError("需要更多信息，但没有下一个问题。")

            self.generate_overall_search_strategy()
            self.calculate_resume_scores(top_n)
            self.resume_details = self.output_generator.fetch_resume_details(
                self.ranked_resume_scores
            )
            self.generate_recommendation_reasons()
            self.prepare_final_recommendations()

            return self.get_recommendations()
        except Exception as e:
            print(f"推荐过程中发生错误: {str(e)}")
            return None

    def get_refined_query(self) -> Optional[str]:
        """
        获取精炼后的查询。

        Returns:
            Optional[str]: 精炼后的查询，如果尚未生成则返回 None
        """
        return self.requirements.get_refined_query()


def main():
    """主函数，用于测试 ResumeRecommender 类"""
    recommender = ResumeRecommender()

    try:
        # 获取用户的初始查询
        query = input("请输入你的招聘需求: ")
        top_n = int(input("请输入要推荐的简历数量 (默认为3): ") or "3")
        recommendations = recommender.run_full_process(query, top_n)

        # 获取并显示精炼后的查询
        refined_query = recommender.get_refined_query()
        if refined_query:
            print(f"\n精炼后的查询:\n{refined_query}")
        else:
            print("无法获取精炼后的查询。")

        # 显示推荐结果
        if recommendations is not None and len(recommendations) > 0:
            print(f"\n推荐结果 (共 {len(recommendations)} 份):")
            for rec in recommendations:
                print(f"简历ID: {rec['简历ID']}")
                print(f"总分: {rec['总分']:.2f}")
                print(f"个人特征: {rec['个人特征']}")
                print(f"工作经验: {rec['工作经验']}")
                print(f"技能概览: {rec['技能概览']}")
                print(f"推荐理由: {rec['推荐理由']}")
                print("-" * 50)
        else:
            print("无法获取推荐结果。")

    except Exception as e:
        print(f"程序执行过程中发生错误: {str(e)}")


if __name__ == "__main__":
    main()
