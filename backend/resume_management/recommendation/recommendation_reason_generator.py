from typing import Dict, List
import pandas as pd
from utils.llm_tools import LanguageModelChain, init_language_model
from utils.dataset_utils import load_df_from_csv, save_df_to_csv
from backend.resume_management.recommendation.recommendation_state import (
    RecommendationReason,
)

# 初始化语言模型
language_model = init_language_model()

SYSTEM_MESSAGE = """
你是一个企业内部使用的智能简历推荐系统。你的任务是生成客观、简洁的推荐理由，解释为什么某份简历符合用户的查询需求。

请遵循以下指南：
1. 直接回应用户的具体要求，不要添加不必要的修饰。
2. 重点关注简历中与用户需求最相关的经验和技能。
3. 保持简洁，总字数控制在100-150字左右。
4. 使用客观、中立的语言，避免过度赞美或主观评价。
5. 不要使用候选人的姓名，也不要使用"他"或"她"等代词，直接陈述相关经验和技能。
6. 简历评分仅用于比较各方面的相对强度，数值本身不具有意义。
7. 重点说明简历中的具体经验和技能如何匹配用户需求，避免空泛的表述。
8. 使用中文撰写理由。
"""

HUMAN_MESSAGE_TEMPLATE = """
用户查询：
{refined_query}

简历评分：
{resume_score}

简历概述：
{resume_overview}

基于以上信息，请生成一个简洁、客观的推荐理由，解释为什么这份简历适合用户的查询需求。回应应该是一段连贯的文字，包含在RecommendationReason结构的reason字段中。
"""

recommendation_reason_chain = LanguageModelChain(
    RecommendationReason, SYSTEM_MESSAGE, HUMAN_MESSAGE_TEMPLATE, language_model
)()


def generate_recommendation_reasons(state: Dict) -> Dict:
    """
    为每份推荐的简历生成详细的推荐理由。

    Args:
        state (Dict): 当前状态字典，包含必要的信息如简历详情文件路径和优化后的查询。

    Returns:
        Dict: 更新后的状态字典，包含生成的推荐理由文件路径。

    Raises:
        ValueError: 如果缺少简历详情文件或优化后的查询。
    """
    if "resume_details_file" not in state or state.get("refined_query") is None:
        raise ValueError("缺少简历详情文件或优化后的查询。无法生成推荐理由。")

    resume_details_df = load_df_from_csv(state["resume_details_file"])

    reasons = []
    for _, resume in resume_details_df.iterrows():
        resume_score = {
            "resume_id": resume["resume_id"],
            "total_score": resume["total_score"],
        }
        for dimension in ["work_experiences", "skills", "educations", "personal_infos"]:
            if dimension in resume:
                resume_score[dimension] = resume[dimension]

        resume_overview = {
            "characteristics": resume["characteristics"],
            "experience": resume["experience"],
            "skills_overview": resume["skills_overview"],
        }

        reason_result = recommendation_reason_chain.invoke(
            {
                "refined_query": state["refined_query"],
                "resume_score": resume_score,
                "resume_overview": resume_overview,
            }
        )

        reasons.append(
            {"resume_id": resume["resume_id"], "reason": reason_result.reason}
        )

    reasons_df = pd.DataFrame(reasons)

    # 保存推荐理由到CSV文件并更新状态
    state["recommendation_reasons_file"] = save_df_to_csv(
        reasons_df, "recommendation_reasons.csv"
    )

    print("已为每份推荐的简历生成详细的推荐理由")
    return state
