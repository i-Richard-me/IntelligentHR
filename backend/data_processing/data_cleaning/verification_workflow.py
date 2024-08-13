from typing import Dict, Any, List, Optional

from backend.data_processing.data_cleaning.search_tools import SearchTools
from backend.data_processing.data_cleaning.verification_models import (
    input_validator,
    search_analysis,
    name_verifier,
)


class CompanyVerificationWorkflow:
    """
    公司验证工作流程类，用于处理和验证公司名称。
    """

    def __init__(self, retriever):
        """
        初始化公司验证工作流程。

        Args:
            retriever: 用于检索公司信息的检索器。
        """
        self.retriever = retriever
        self.search_tools = SearchTools()

    def run(self, user_query: str) -> Dict[str, Any]:
        """
        执行完整的公司验证工作流程。

        Args:
            user_query (str): 用户输入的公司名称查询。

        Returns:
            Dict[str, Any]: 包含验证结果的字典。
        """
        result = self._initialize_result()

        # 步骤1: 验证输入
        result["is_valid"] = self._validate_input(user_query)
        if not result["is_valid"]:
            return self._generate_output(result, user_query)

        # 步骤2和3: 网络搜索和分析搜索结果
        search_results = self._perform_web_search(user_query)
        identified_company, recognition_status = self._analyze_search_results(
            user_query, search_results
        )
        result["identified_company_name"] = identified_company
        result["recognition_status"] = recognition_status

        if recognition_status == "known":
            # 步骤4和5: 直接检索和评估名称匹配
            retrieval_results = self._direct_retrieve(identified_company or user_query)
            result["retrieved_company_name"] = retrieval_results[0].page_content
            result["verification_status"] = self._evaluate_match(
                user_query, result["retrieved_company_name"], search_results
            )

            if result["verification_status"] == "verified":
                return self._generate_output(result, user_query, retrieval_results)

        # 如果未验证或未知，进行替代搜索
        alternative_results = self._perform_alternative_search(user_query)
        identified_company, recognition_status = self._analyze_search_results(
            user_query, alternative_results
        )
        result["identified_company_name"] = identified_company
        result["recognition_status"] = recognition_status

        if recognition_status == "known":
            retrieval_results = self._direct_retrieve(identified_company or user_query)
            result["retrieved_company_name"] = retrieval_results[0].page_content
            result["verification_status"] = self._evaluate_match(
                user_query, result["retrieved_company_name"], alternative_results
            )

        return self._generate_output(result, user_query, retrieval_results)

    def _initialize_result(self) -> Dict[str, Any]:
        """初始化结果字典"""
        return {
            "is_valid": False,
            "identified_company_name": None,
            "recognition_status": "",
            "retrieved_company_name": "",
            "verification_status": "",
            "final_company_name": "",
        }

    def _validate_input(self, user_query: str) -> bool:
        """验证用户输入"""
        print("---验证用户输入---")
        validation_result = input_validator.invoke({"user_query": user_query})
        return validation_result["is_valid"]

    def _perform_web_search(self, user_query: str) -> str:
        """执行网络搜索"""
        print("---执行网络搜索---")
        return self.search_tools.duckduckgo_search(user_query)

    def _analyze_search_results(
        self, user_query: str, search_results: str
    ) -> tuple[Optional[str], str]:
        """分析搜索结果"""
        print("---分析搜索结果---")
        analysis_result = search_analysis.invoke(
            {"user_query": user_query, "snippets": search_results}
        )
        return (
            (
                analysis_result["identified_company_name"]
                if analysis_result["recognition_status"] == "known"
                else None
            ),
            analysis_result["recognition_status"],
        )

    def _direct_retrieve(self, search_term: str) -> List:
        """直接从检索器中检索公司信息"""
        print("---直接检索---")
        return self.retriever.invoke(search_term)

    def _evaluate_match(
        self, user_query: str, retrieved_name: str, search_results: str
    ) -> str:
        """评估检索到的公司名称与用户查询的匹配度"""
        print("---评估名称匹配---")
        verified_result = name_verifier.invoke(
            {
                "user_query": user_query,
                "retrieved_name": retrieved_name,
                "search_results": search_results,
            }
        )
        return verified_result["verification_status"]

    def _perform_alternative_search(self, user_query: str) -> str:
        """执行替代搜索"""
        print("---执行替代搜索---")
        return self.search_tools.tavily_search(user_query)

    def _generate_output(
        self,
        result: Dict[str, Any],
        user_query: str,
        retrieval_results: Optional[List] = None,
    ) -> Dict[str, Any]:
        """生成最终输出结果"""
        print("---生成最终输出---")
        if (
            result["is_valid"]
            and retrieval_results
            and result["verification_status"] == "verified"
        ):
            result["final_company_name"] = retrieval_results[0].metadata[
                "company_abbreviation"
            ]
        elif not result["is_valid"]:
            result["final_company_name"] = "无效输入"
        else:
            result["final_company_name"] = "未知"
        print(f"---最终公司简称：{result['final_company_name']}---")
        return result
