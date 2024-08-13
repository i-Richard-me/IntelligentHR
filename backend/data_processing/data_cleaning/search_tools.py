from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.tools.tavily_search import TavilySearchResults


class SearchTools:
    """
    搜索工具类，提供多种搜索方法。
    """

    def __init__(self):
        """
        初始化搜索工具。
        """
        self.duckduckgo_wrapper = DuckDuckGoSearchAPIWrapper(max_results=5)
        self.duckduckgo_search_tool = DuckDuckGoSearchRun(
            api_wrapper=self.duckduckgo_wrapper
        )
        self.tavily_search_tool = TavilySearchResults(k=2)

    def duckduckgo_search(self, query: str) -> str:
        """
        使用 DuckDuckGo 执行搜索。

        Args:
            query (str): 搜索查询。

        Returns:
            str: 搜索结果。
        """
        return self.duckduckgo_search_tool.invoke(query + " 简称")

    def tavily_search(self, query: str) -> str:
        """
        使用 Tavily 执行搜索。

        Args:
            query (str): 搜索查询。

        Returns:
            str: 搜索结果。
        """
        return self.tavily_search_tool.invoke(query)
