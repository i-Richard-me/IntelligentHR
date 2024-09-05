from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import pandas as pd
from utils.llm_tools import LanguageModelChain, init_language_model
from utils.dataset_utils import load_df_from_csv, save_df_to_csv
from langfuse.callback import CallbackHandler
import uuid

# 初始化语言模型
language_model = init_language_model()


class RecommendationReason(BaseModel):
    reason: str = Field(
        ..., description="一段简洁有力的推荐理由，解释为什么这份简历适合用户的需求"
    )


class RecommendationReasonGenerator:
    def __init__(self):
        self.language_model = init_language_model()
        self.system_message = """
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

        self.human_message_template = """
        用户查询：
        {refined_query}

        简历评分：
        {resume_score}

        简历概述：
        {resume_overview}

        基于以上信息，请生成一个简洁、客观的推荐理由，解释为什么这份简历适合用户的查询需求。回应应该是一段连贯的文字，包含在RecommendationReason结构的reason字段中。
        """

        self.recommendation_reason_chain = LanguageModelChain(
            RecommendationReason,
            self.system_message,
            self.human_message_template,
            self.language_model,
        )()

    def create_langfuse_handler(self, session_id, step):
        return CallbackHandler(
            tags=["recommendation_reason"],
            session_id=session_id,
            metadata={"step": step},
        )

    def generate_recommendation_reasons(
        self,
        refined_query: str,
        resume_details: pd.DataFrame,
        session_id: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        为每份推荐的简历生成详细的推荐理由。

        Args:
            refined_query (str): 精炼后的用户查询
            resume_details (pd.DataFrame): 包含简历详细信息的DataFrame

        Returns:
            pd.DataFrame: 包含生成的推荐理由的DataFrame

        Raises:
            ValueError: 如果简历详细信息为空或精炼后的查询为空
        """
        if not refined_query:
            raise ValueError("精炼后的查询不能为空。无法生成推荐理由。")

        if resume_details.empty:
            raise ValueError("简历详细信息不能为空。无法生成推荐理由。")

        reasons = []
        for _, resume in resume_details.iterrows():
            resume_score = {
                "resume_id": resume["resume_id"],
                "total_score": resume["total_score"],
            }
            for dimension in [
                "work_experiences",
                "skills",
                "educations",
                "personal_infos",
            ]:
                if dimension in resume:
                    resume_score[dimension] = resume[dimension]

            resume_overview = {
                "characteristics": resume["characteristics"],
                "experience": resume["experience"],
                "skills_overview": resume["skills_overview"],
            }

            langfuse_handler = self.create_langfuse_handler(
                session_id, "generate_recommendation_reason"
            )
            reason_result = self.recommendation_reason_chain.invoke(
                {
                    "refined_query": refined_query,
                    "resume_score": resume_score,
                    "resume_overview": resume_overview,
                },
                config={"callbacks": [langfuse_handler]},
            )

            reasons.append(
                {"resume_id": resume["resume_id"], "reason": reason_result["reason"]}
            )

        reasons_df = pd.DataFrame(reasons)

        print("已为每份推荐的简历生成详细的推荐理由")
        return reasons_df
