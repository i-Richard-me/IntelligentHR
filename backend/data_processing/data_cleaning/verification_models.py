from typing import Literal

from pydantic import BaseModel, Field

from utils.llm_tools import init_language_model, LanguageModelChain

# 初始化语言模型
language_model = init_language_model()


class InputValidation(BaseModel):
    """用户输入的验证结果。"""

    is_valid: bool = Field(
        ..., description="指示用户输入是否为有效的公司名称（'True'）或不是（'False'）。"
    )


class CompanyNameRecognition(BaseModel):
    """从网络搜索结果中识别公司名称的结果。"""

    identified_company_name: str = Field(
        ..., description="从搜索结果中提取的公司名称，如果它是已知公司的变体或子公司。"
    )
    recognition_status: Literal["known", "unknown"] = Field(
        ..., description="指示公司名称是否成功识别（'known'）或未识别（'unknown'）。"
    )


class CompanyNameVerification(BaseModel):
    """检索到的公司名称与用户查询匹配的验证结果。"""

    verification_status: Literal["verified", "unverified"] = Field(
        ...,
        description="指示检索到的公司名称是否与用户的查询相匹配（'verified'）或不匹配（'unverified'）。",
    )


# 定义系统消息
system_message_validation = """
你的任务是判断用户输入的查询公司名称是否是一个具体的、有效的公司名称。
你将收到一个用户查询的公司名称。
请判断该名称是否足以识别一个特定的公司。
如果名称具体且明确，足以识别一个特定的公司，则将其标记为'True'。
如果名称模糊，或者不是指一个特定的公司，则标记为'False'。
"""

system_message_search_analysis = """
你的工作是根据提供的网络搜索结果来判断搜索结果是否与查询的公司名称相关。
如果搜索结果与查询的公司名称相关，你需要进一步推断该公司是否是某家知名公司的合同主体变体或其子公司。
如果能够推断出该公司是某家知名公司的变体或子公司，请提供这家更普遍和知名的公司名称，并标记状态为'known'。
如果无法推断出相关信息，或者搜索结果与查询的公司名称不相关，请标记状态为'unknown'，并省略公司名称。
在进行判断时，请考虑公司名称的相似性、搜索结果中提及的母公司或集团信息、以及提及的公司简称等。
"""

system_message_verification = """
你的任务是验证从向量数据库检索到的公司名称是否与用户提供的查询公司名称指向同一个母公司。
你将收到一个用户查询的公司名称、从数据库检索到的最相似的公司名称以及相关的搜索结果。
请结合搜索结果来判断检索到的公司名称是否确实是指向用户查询的公司的同一个母公司。
如果检索到的公司名称与搜索结果一致，并且可以确认是指向同一个母公司，则将其标记为'verified'。
如果无法确认是同一母公司，或者搜索结果与查询不相关，则标记为'unverified'。
在判断时，请考虑公司名称的正式表述、可能的简称或全称差异，以及搜索结果中的相关信息。
即使名称表述不同，只要指向同一个母公司，也应视为匹配。"""

# 定义人类消息
human_message_validation = "用户查询的公司名称：{user_query}"

human_message_search_analysis = """
针对特定查询'{user_query}'，请仔细评估以下网络搜索片段：{snippets}。
如果搜索结果明确指向查询中的公司，并且您能够推断出该公司是某家知名公司的变体或子公司，
请提供该知名公司的名称并标注状态为'known'。
如果搜索结果不明确或无法推断出相关信息，请标注状态为'unknown'，并省略公司名称。"""

human_message_verification = "用户查询的公司名称：{user_query} \n检索到的公司名称：{retrieved_name} \n搜索结果：{search_results}"

# 创建处理链
input_validator = LanguageModelChain(
    InputValidation, system_message_validation, human_message_validation, language_model
)()

search_analysis = LanguageModelChain(
    CompanyNameRecognition,
    system_message_search_analysis,
    human_message_search_analysis,
    language_model,
)()

name_verifier = LanguageModelChain(
    CompanyNameVerification,
    system_message_verification,
    human_message_verification,
    language_model,
)()
