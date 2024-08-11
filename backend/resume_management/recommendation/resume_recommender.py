import os
import shutil
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
from utils.dataset_utils import load_df_from_csv


class ResumeRecommender:
    def __init__(self):
        self.requirements = RecommendationRequirements()
        self.resume_search_strategy_generator = ResumeSearchStrategyGenerator()
        self.collection_search_strategy_generator = CollectionSearchStrategyGenerator()
        self.resume_scorer = ResumeScorer()
        self.reason_generator = RecommendationReasonGenerator()
        self.output_generator = RecommendationOutputGenerator()
        self.refined_query: Optional[str] = None
        self.collection_relevances: Optional[List[Dict[str, float]]] = None
        self.collection_search_strategies: Optional[Dict] = None
        self.ranked_resume_scores_file: Optional[str] = None
        self.resume_details_file: Optional[str] = None
        self.recommendation_reasons_file: Optional[str] = None
        self.final_recommendations_file: Optional[str] = None

    def process_query(self, query: str) -> str:
        """
        处理用户的初始查询，启动推荐过程。

        Args:
            query (str): 用户的初始查询

        Returns:
            str: 处理状态，可能是 'need_more_info' 或 'ready'
        """
        return self.requirements.confirm_requirements(query)

    def get_next_question(self) -> Optional[str]:
        """
        获取下一个需要用户回答的问题（如果有的话）。

        Returns:
            Optional[str]: 下一个问题，如果没有则返回 None
        """
        return self.requirements.get_current_question()

    def process_answer(self, answer: str) -> str:
        """
        处理用户对问题的回答，继续推荐过程。

        Args:
            answer (str): 用户的回答

        Returns:
            str: 处理状态，可能是 'need_more_info' 或 'ready'
        """
        return self.requirements.confirm_requirements(answer)

    def generate_search_strategy(self) -> None:
        """
        生成简历搜索策略。
        """
        self.refined_query = self.requirements.get_refined_query()
        if not self.refined_query:
            raise ValueError("未找到精炼后的查询。无法生成搜索策略。")

        self.collection_relevances = (
            self.resume_search_strategy_generator.generate_resume_search_strategy(
                self.refined_query
            )
        )
        self.search_strategy = self.collection_relevances
        # 将生成详细的检索策略移到单独的方法中
        self.generate_detailed_search_strategy()

    def generate_detailed_search_strategy(self) -> None:
        """
        生成详细的检索策略。
        """
        self.collection_search_strategies = self.collection_search_strategy_generator.generate_collection_search_strategy(
            self.refined_query, self.collection_relevances
        )

    def get_search_strategy(self) -> Optional[List[Dict[str, float]]]:
        """
        获取搜索策略。

        Returns:
            Optional[List[Dict[str, float]]]: 搜索策略，如果尚未生成则返回 None
        """
        return self.search_strategy

    def calculate_resume_scores(self) -> None:
        """
        计算简历得分。
        """
        if (
            not self.refined_query
            or not self.collection_relevances
            or not self.collection_search_strategies
        ):
            raise ValueError("缺少生成简历得分所需的信息。")

        self.ranked_resume_scores_file = (
            self.resume_scorer.calculate_overall_resume_scores(
                self.refined_query,
                self.collection_relevances,
                self.collection_search_strategies,
            )
        )

    def generate_recommendation_reasons(self) -> None:
        """
        生成推荐理由。
        """
        if not self.refined_query or not self.resume_details_file:
            raise ValueError("缺少生成推荐理由所需的信息。")

        self.recommendation_reasons_file = (
            self.reason_generator.generate_recommendation_reasons(
                self.refined_query, self.resume_details_file
            )
        )

    def prepare_final_recommendations(self) -> None:
        """
        准备最终的推荐结果。
        """
        if not self.resume_details_file or not self.recommendation_reasons_file:
            raise ValueError("缺少准备最终推荐所需的信息。")

        self.final_recommendations_file = self.output_generator.prepare_final_output(
            self.resume_details_file, self.recommendation_reasons_file
        )

    def get_recommendations(self) -> Optional[List[Dict]]:
        """
        获取最终的推荐结果。

        Returns:
            Optional[List[Dict]]: 推荐结果列表，如果尚未生成则返回 None
        """
        if self.final_recommendations_file:
            df = load_df_from_csv(self.final_recommendations_file)
            return df.to_dict("records")
        return None

    def run_full_process(self, initial_query: str) -> Optional[List[Dict]]:
        """
        运行完整的推荐过程。

        Args:
            initial_query (str): 用户的初始查询

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

            self.generate_search_strategy()
            self.calculate_resume_scores()
            self.resume_details_file = self.output_generator.fetch_resume_details(
                self.ranked_resume_scores_file
            )
            self.generate_recommendation_reasons()
            self.prepare_final_recommendations()

            return self.get_recommendations()
        except Exception as e:
            print(f"推荐过程中发生错误: {str(e)}")
            return None
        finally:
            self.cleanup_temp_files()

    def cleanup_temp_files(self) -> None:
        """
        清理临时文件。
        """
        temp_dir = os.path.join("data", "temp")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir, exist_ok=True)
        print("临时文件已清理。")

    def get_refined_query(self) -> Optional[str]:
        """
        获取精炼后的查询。

        Returns:
            Optional[str]: 精炼后的查询，如果尚未生成则返回 None
        """
        return self.requirements.get_refined_query()


def main():
    recommender = ResumeRecommender()

    try:
        # 获取用户的初始查询
        query = input("请输入你的招聘需求: ")
        recommendations = recommender.run_full_process(query)

        # 获取并显示精炼后的查询
        refined_query = recommender.get_refined_query()
        if refined_query:
            print(f"\n精炼后的查询:\n{refined_query}")
        else:
            print("无法获取精炼后的查询。")

        # 显示推荐结果
        if recommendations:
            print("\n推荐结果:")
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
