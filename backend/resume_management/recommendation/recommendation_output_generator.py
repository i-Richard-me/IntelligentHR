import pandas as pd
from typing import Dict
from utils.dataset_utils import load_df_from_csv, save_df_to_csv


class RecommendationOutputGenerator:
    def __init__(self):
        pass

    def fetch_resume_details(self, ranked_resume_scores_file: str) -> str:
        """
        获取候选简历的详细信息。

        Args:
            ranked_resume_scores_file (str): 包含排名后的简历得分的CSV文件名

        Returns:
            str: 包含简历详细信息的CSV文件名

        Raises:
            ValueError: 如果排名后的简历得分文件不存在
        """
        if not ranked_resume_scores_file:
            raise ValueError("排名后的简历得分文件不能为空。无法获取简历详细信息。")

        ranked_resume_scores_df = load_df_from_csv(ranked_resume_scores_file)
        top_resume_ids = ranked_resume_scores_df["resume_id"].tolist()

        df_resume_summary = pd.read_csv("data/datasets/resume_summary.csv")
        resume_details = df_resume_summary[df_resume_summary["id"].isin(top_resume_ids)]
        resume_details = resume_details.rename(columns={"id": "resume_id"})

        merged_df = pd.merge(
            ranked_resume_scores_df, resume_details, on="resume_id", how="left"
        )

        # 保存合并后的DataFrame为CSV并返回文件名
        output_filename = save_df_to_csv(merged_df, "resume_details.csv")

        print("已获取候选简历的详细信息")
        return output_filename

    def prepare_final_output(
        self, resume_details_file: str, recommendation_reasons_file: str
    ) -> str:
        """
        准备最终的推荐输出。

        Args:
            resume_details_file (str): 包含简历详细信息的CSV文件名
            recommendation_reasons_file (str): 包含推荐理由的CSV文件名

        Returns:
            str: 包含最终推荐结果的CSV文件名

        Raises:
            ValueError: 如果简历详细信息文件或推荐理由文件不存在
        """
        if not resume_details_file or not recommendation_reasons_file:
            raise ValueError(
                "简历详细信息文件或推荐理由文件不能为空。无法准备最终输出。"
            )

        resume_details_df = load_df_from_csv(resume_details_file)
        recommendation_reasons = load_df_from_csv(recommendation_reasons_file)

        final_recommendations = pd.merge(
            resume_details_df, recommendation_reasons, on="resume_id", how="left"
        )

        columns_order = [
            "resume_id",
            "total_score",
            "characteristics",
            "experience",
            "skills_overview",
            "reason",
        ]
        final_recommendations = final_recommendations[columns_order]

        final_recommendations = final_recommendations.sort_values(
            "total_score", ascending=False
        )

        final_recommendations = final_recommendations.rename(
            columns={
                "resume_id": "简历ID",
                "total_score": "总分",
                "characteristics": "个人特征",
                "experience": "工作经验",
                "skills_overview": "技能概览",
                "reason": "推荐理由",
            }
        )

        # 保存最终推荐结果为CSV并返回文件名
        output_filename = save_df_to_csv(
            final_recommendations, "final_recommendations.csv"
        )

        print("推荐结果生成完毕，即将为您展示")
        return output_filename
