import pandas as pd
from typing import Dict
from utils.dataset_utils import load_df_from_csv, save_df_to_csv


def prepare_final_output(state: Dict) -> Dict:
    """
    准备最终的推荐输出。

    Args:
        state (Dict): 当前状态字典，包含简历详情和推荐理由的文件路径。

    Returns:
        Dict: 更新后的状态字典，包含最终推荐结果的文件路径。

    Raises:
        ValueError: 如果缺少简历详情或推荐理由文件。
    """
    if "resume_details_file" not in state or "recommendation_reasons_file" not in state:
        raise ValueError("缺少简历详情或推荐理由文件。无法准备最终输出。")

    resume_details_df = load_df_from_csv(state["resume_details_file"])
    recommendation_reasons = load_df_from_csv(state["recommendation_reasons_file"])

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

    # 保存最终推荐结果到CSV文件并更新状态
    state["final_recommendations_file"] = save_df_to_csv(
        final_recommendations, "final_recommendations.csv"
    )
    print("推荐结果生成完毕，即将为您展示")
    return state


def fetch_resume_details(state: Dict) -> Dict:
    """
    获取简历详细信息。

    Args:
        state (Dict): 当前状态字典，包含排名后的简历分数文件路径。

    Returns:
        Dict: 更新后的状态字典，包含简历详情的文件路径。

    Raises:
        ValueError: 如果缺少排名后的简历分数文件。
    """
    if "ranked_resume_scores_file" not in state:
        raise ValueError("缺少排名后的简历分数文件。无法获取简历详情。")

    ranked_resume_scores_df = load_df_from_csv(state["ranked_resume_scores_file"])
    top_resume_ids = ranked_resume_scores_df["resume_id"].tolist()

    df_resume_summary = pd.read_csv("data/resume_recommender/resume_summary.csv")
    resume_details = df_resume_summary[df_resume_summary["id"].isin(top_resume_ids)]
    resume_details = resume_details.rename(columns={"id": "resume_id"})

    merged_df = pd.merge(
        ranked_resume_scores_df, resume_details, on="resume_id", how="left"
    )

    # 保存简历详情到CSV文件并更新状态
    state["resume_details_file"] = save_df_to_csv(merged_df, "resume_details.csv")

    print("已获取候选简历的详细信息")
    return state
