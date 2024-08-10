import os
import shutil
import uuid
from typing import Dict, Optional, List
from backend.resume_management.recommendation.recommendation_workflow import app
from backend.resume_management.recommendation.recommendation_state import (
    ResumeRecommendationState,
)
from utils.dataset_utils import load_df_from_csv
from langfuse.callback import CallbackHandler


class ResumeRecommender:
    """简历推荐系统的主类"""

    def __init__(self):
        """初始化简历推荐器"""
        self.session_id = str(uuid.uuid4())
        self.workflow = app
        self.thread = {"configurable": {"thread_id": self.session_id}}
        self.langfuse_handler = CallbackHandler(
            tags=["resume_demo"], session_id=self.session_id
        )

    def process_query(self, query: str) -> Dict:
        """
        处理用户的初始查询，启动推荐过程。

        Args:
            query (str): 用户的初始查询。

        Returns:
            Dict: 处理结果。
        """
        initial_state: ResumeRecommendationState = {
            "original_query": query,
            "status": "need_more_info",
            "refined_query": "",
            "query_history": [query],
            "current_question": None,
            "user_input": None,
            "collection_relevances": [],
            "collection_search_strategies": {},
            "ranked_resume_scores_file": None,
            "resume_details_file": None,
            "recommendation_reasons_file": None,
            "final_recommendations_file": None,
        }

        return self.workflow.invoke(initial_state, config=self.thread)

    def get_next_question(self) -> Optional[str]:
        """
        获取下一个需要用户回答的问题（如果有的话）。

        Returns:
            Optional[str]: 下一个问题，如果没有则返回 None。
        """
        state = self.workflow.get_state(self.thread).values
        return state.get("current_question")

    def process_answer(self, answer: str) -> Dict:
        """
        处理用户对问题的回答，继续推荐过程。

        Args:
            answer (str): 用户的回答。

        Returns:
            Dict: 处理结果。
        """
        self.workflow.update_state(
            self.thread, {"user_input": answer}, as_node="get_user_input"
        )
        return self.workflow.invoke(None, self.thread)

    def get_next_node(self) -> Optional[str]:
        """
        获取工作流程中的下一个节点。

        Returns:
            Optional[str]: 下一个节点的名称，如果没有则返回 None。
        """
        next_node = self.workflow.get_state(self.thread).next
        return next_node[0] if next_node else None

    def continue_process(self) -> tuple[Dict, Optional[str]]:
        """
        继续执行推荐过程。

        Returns:
            tuple[Dict, Optional[str]]: 处理结果和下一个节点名称。
        """
        next_node = self.get_next_node()
        result = self.workflow.invoke(None, self.thread)
        return result, next_node

    def get_collection_relevances(self) -> List[Dict]:
        """
        获取集合相关性列表。

        Returns:
            List[Dict]: 集合相关性列表。
        """
        state = self.workflow.get_state(self.thread).values
        return state.get("collection_relevances", [])

    def is_process_complete(self) -> bool:
        """
        检查推荐过程是否已完成。

        Returns:
            bool: 如果过程完成则返回 True，否则返回 False。
        """
        state = self.workflow.get_state(self.thread).values
        return state.get("final_recommendations_file") is not None

    def get_refined_query(self) -> Optional[str]:
        """
        获取精炼后的查询。

        Returns:
            Optional[str]: 精炼后的查询，如果没有则返回 None。
        """
        state = self.workflow.get_state(self.thread).values
        return state.get("refined_query")

    def get_recommendations(self) -> Optional[List[Dict]]:
        """
        获取最终的推荐结果。

        Returns:
            Optional[List[Dict]]: 推荐结果列表，如果没有则返回 None。
        """
        state = self.workflow.get_state(self.thread).values
        if state.get("final_recommendations_file"):
            df = load_df_from_csv(state["final_recommendations_file"])
            return df.to_dict("records")
        return None

    def run_full_process(self) -> Optional[List[Dict]]:
        """
        运行完整的推荐过程。

        Returns:
            Optional[List[Dict]]: 推荐结果列表，如果没有则返回 None。
        """
        try:
            while not self.is_process_complete():
                next_question = self.get_next_question()
                if next_question:
                    answer = input(f"{next_question}\n请回答: ")
                    self.process_answer(answer)
                else:
                    self.workflow.invoke(None, self.thread)

            return self.get_recommendations()
        finally:
            self.cleanup_temp_files()

    def get_current_state(self) -> Dict:
        """
        获取当前的状态。

        Returns:
            Dict: 当前状态字典。
        """
        return self.workflow.get_state(self.thread).values

    def cleanup_temp_files(self):
        """清理临时文件"""
        temp_dir = os.path.join("data", "temp")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir, exist_ok=True)
        print("临时文件已清理。")


def main():
    """主函数，用于演示简历推荐系统的使用"""
    recommender = ResumeRecommender()

    try:
        query = input("请输入你的招聘需求: ")
        recommender.process_query(query)

        recommendations = recommender.run_full_process()

        refined_query = recommender.get_refined_query()
        if refined_query:
            print(f"\n精炼后的查询:\n{refined_query}")
        else:
            print("无法获取精炼后的查询。")

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

    finally:
        recommender.cleanup_temp_files()


if __name__ == "__main__":
    main()
