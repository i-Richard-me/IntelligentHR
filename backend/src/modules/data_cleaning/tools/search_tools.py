"""
搜索工具模块，提供网络搜索功能
"""
from typing import List, Dict, Union, Optional


class SearchTools:
    """搜索工具类,提供多种网络搜索实现"""

    def __init__(self, max_results: int = 5):
        """初始化搜索工具配置"""
        self.max_results = max_results

    async def asearch(
            self,
            query: str,
            search_type: str = "tavily"
    ) -> Union[str, List[Dict]]:
        """
        执行搜索并返回结果

        Args:
            query: 搜索查询
            search_type: 搜索类型，支持 "tavily" 和 "duckduckgo"

        Returns:
            搜索结果，可能是字符串或字典列表
        """
        if search_type == "tavily":
            results = await self._atavily_search(query)
            # 处理成字符串格式,以便后续处理
            cleaned_results = [item["content"] for item in results if "content" in item]
            return " ".join(cleaned_results)
        else:
            results = await self._aduckduckgo_search(query)
            return results

    async def _atavily_search(self, query: str) -> List[Dict]:
        """使用 Tavily 搜索"""
        from langchain_community.tools.tavily_search import TavilySearchResults
        search_tool = TavilySearchResults(max_results=self.max_results)
        results = await search_tool.ainvoke(query)
        return results

    async def _aduckduckgo_search(self, query: str) -> str:
        """使用 DuckDuckGo 搜索"""
        from langchain_community.tools import DuckDuckGoSearchRun
        from langchain_community.utilities import DuckDuckGoSearchAPIWrapper

        wrapper = DuckDuckGoSearchAPIWrapper(max_results=self.max_results)
        search_tool = DuckDuckGoSearchRun(api_wrapper=wrapper)
        results = await search_tool.ainvoke(query)
        return results