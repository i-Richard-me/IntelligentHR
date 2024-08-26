import os
import pandas as pd
import time
import numpy as np
from pymilvus import Collection, connections
from typing import List, Dict, Tuple
from openai import OpenAI
from utils.dataset_utils import save_df_to_csv


class ResumeScorer:
    def __init__(self):
        self.client = OpenAI(
            base_url="https://api.siliconflow.cn/v1",
            api_key=os.getenv("EMBEDDING_API_KEY"),
        )
        self.connection_args = {
            "host": os.getenv("VECTOR_DB_HOST", "localhost"),
            "port": os.getenv("VECTOR_DB_PORT", "19530"),
            "db_name": os.getenv("VECTOR_DB_DATABASE_RESUME", "resume"),
        }

    def get_embedding(self, text: str) -> List[float]:
        """
        获取文本的嵌入向量。

        Args:
            text (str): 输入文本

        Returns:
            List[float]: 嵌入向量
        """
        while True:
            try:
                response = self.client.embeddings.create(
                    model=os.getenv("EMBEDDING_MODEL", ""), input=text
                )
                time.sleep(0.07)
                return response.data[0].embedding
            except Exception as e:
                if len(text) <= 1:
                    return None
                text = text[: int(len(text) * 0.9)]
                time.sleep(0.07)

    def calculate_resume_scores_for_collection(
        self,
        collection: Collection,
        query_contents: List[Dict[str, str]],
        field_relevance_scores: Dict[str, float],
        scoring_method: str = "hybrid",
        max_results: int = 100,
        top_similarities_count: int = 3,
        similarity_threshold: float = 0.3,
        decay_factor: float = 0.3,
    ) -> List[Tuple[str, float]]:
        """
        计算单个集合中简历的得分。

        Args:
            collection (Collection): Milvus集合
            query_contents (List[Dict[str, str]]): 查询内容列表
            field_relevance_scores (Dict[str, float]): 字段相关性得分
            scoring_method (str): 评分方法，默认为'hybrid'
            max_results (int): 最大结果数，默认为100
            top_similarities_count (int): 考虑的最高相似度数量，默认为3
            similarity_threshold (float): 相似度阈值，默认为0.3
            decay_factor (float): 衰减因子，默认为0.3

        Returns:
            List[Tuple[str, float]]: 简历ID和得分的列表
        """
        resume_scores = {}

        for query in query_contents:
            field_name = query["field_name"]
            query_vector = self.get_embedding(query["query_content"])

            search_params = {"metric_type": "IP", "params": {"nprobe": 10}}
            results = collection.search(
                data=[query_vector],
                anns_field=field_name,
                param=search_params,
                limit=collection.num_entities,
                expr=None,
                output_fields=["resume_id"],
            )

            for hits in results:
                for hit in hits:
                    resume_id = hit.entity.get("resume_id")
                    similarity = hit.score

                    if similarity < similarity_threshold:
                        continue

                    if resume_id not in resume_scores:
                        resume_scores[resume_id] = {}
                    if field_name not in resume_scores[resume_id]:
                        resume_scores[resume_id][field_name] = []
                    resume_scores[resume_id][field_name].append(similarity)

        final_scores = {}
        for resume_id, field_scores in resume_scores.items():
            resume_score = 0
            for field_name, similarities in field_scores.items():
                top_similarities = sorted(similarities, reverse=True)[
                    :top_similarities_count
                ]

                if scoring_method == "sum":
                    field_score = sum(top_similarities)
                elif scoring_method == "max":
                    field_score = max(top_similarities)
                elif scoring_method == "hybrid":
                    field_score = max(top_similarities) + decay_factor * sum(
                        top_similarities[1:]
                    )
                else:
                    raise ValueError("无效的计算方法")

                resume_score += field_score * field_relevance_scores[field_name]

            final_scores[resume_id] = resume_score

        sorted_scores = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_scores[:max_results]

    def calculate_overall_resume_scores(
        self,
        refined_query: str,
        collection_relevances: List[Dict],
        collection_search_strategies: Dict,
        top_n: int = 3,
    ) -> str:
        """
        计算所有集合的综合简历得分并返回前N个简历。

        Args:
            refined_query (str): 精炼后的查询
            collection_relevances (List[Dict]): 集合相关性列表
            collection_search_strategies (Dict): 集合搜索策略
            top_n (int): 要返回的最佳匹配简历数量

        Returns:
            str: 存储排名后的简历得分的CSV文件名
        """
        connections.connect(
            host=self.connection_args["host"],
            port=self.connection_args["port"],
            db_name=self.connection_args["db_name"],
        )

        all_scores = {}

        for collection_info in collection_relevances:
            collection_name = collection_info["collection_name"]
            collection_weight = collection_info["relevance_score"]

            if collection_weight == 0:
                continue

            collection = Collection(collection_name)
            collection_strategy = collection_search_strategies[collection_name]

            query_contents = []
            field_relevance_scores = {}
            for query in collection_strategy.vector_field_queries:
                query_contents.append(
                    {
                        "field_name": query.field_name,
                        "query_content": query.query_content,
                    }
                )
                field_relevance_scores[query.field_name] = query.relevance_score

            collection_scores = self.calculate_resume_scores_for_collection(
                collection=collection,
                query_contents=query_contents,
                field_relevance_scores=field_relevance_scores,
                scoring_method="hybrid",
                max_results=collection.num_entities,
                top_similarities_count=3,
                similarity_threshold=0.3,
                decay_factor=0.3,
            )

            for resume_id, score in collection_scores:
                if resume_id not in all_scores:
                    all_scores[resume_id] = {"total_score": 0}
                all_scores[resume_id][collection_name] = score * collection_weight
                all_scores[resume_id]["total_score"] += score * collection_weight

        df = pd.DataFrame.from_dict(all_scores, orient="index")
        df.index.name = "resume_id"
        df.reset_index(inplace=True)

        df = df.sort_values("total_score", ascending=False).head(top_n)

        for collection_info in collection_relevances:
            if collection_info["collection_name"] not in df.columns:
                df[collection_info["collection_name"]] = 0

        column_order = ["resume_id", "total_score"] + [
            info["collection_name"] for info in collection_relevances
        ]
        df = df[column_order]

        # 保存DataFrame为CSV并返回文件名
        filename = save_df_to_csv(df, "ranked_resume_scores.csv")

        print(f"已完成简历评分，正在筛选最佳匹配的 {top_n} 份简历")

        return filename


if __name__ == "__main__":

    import unittest
    from unittest.mock import Mock, patch

    class TestResumeScorer(unittest.TestCase):
        def setUp(self):
            self.resume_scorer = ResumeScorer()

        @patch("resume_scorer.Collection")
        @patch("resume_scorer.connections")
        @patch("resume_scorer.ResumeScorer.get_embedding")
        def test_calculate_overall_resume_scores(
            self, mock_get_embedding, mock_connections, mock_collection
        ):
            # 模拟 Milvus Collection
            mock_collection_instance = Mock()
            mock_collection_instance.num_entities = 10
            mock_collection_instance.search.return_value = [
                [
                    Mock(entity={"resume_id": f"resume_{i}"}, score=0.8 - i * 0.05)
                    for i in range(5)
                ]
            ]
            mock_collection.return_value = mock_collection_instance

            # 模拟嵌入向量
            mock_get_embedding.return_value = [0.1] * 10

            # 模拟输入数据
            refined_query = "寻找有5年以上Python开发经验的软件工程师"
            collection_relevances = [
                {"collection_name": "work_experiences", "relevance_score": 0.6},
                {"collection_name": "skills", "relevance_score": 0.4},
            ]
            collection_search_strategies = {
                "work_experiences": Mock(
                    vector_field_queries=[
                        Mock(
                            field_name="position_vector",
                            query_content="Senior Python Developer",
                            relevance_score=0.7,
                        ),
                        Mock(
                            field_name="responsibilities_vector",
                            query_content="Develop and maintain Python applications",
                            relevance_score=0.3,
                        ),
                    ]
                ),
                "skills": Mock(
                    vector_field_queries=[
                        Mock(
                            field_name="skill_vector",
                            query_content="Python, Django, Flask",
                            relevance_score=1.0,
                        )
                    ]
                ),
            }

            # 测试不同的 top_n 值
            for top_n in [3, 5, 10]:
                # 运行方法
                result_filename = self.resume_scorer.calculate_overall_resume_scores(
                    refined_query,
                    collection_relevances,
                    collection_search_strategies,
                    top_n,
                )

                # 验证结果
                self.assertTrue(result_filename.endswith(".csv"))

                # 读取生成的 CSV 文件
                df = pd.read_csv(f"data/temp/{result_filename}")

                # 验证DataFrame的结构
                self.assertIn("resume_id", df.columns)
                self.assertIn("total_score", df.columns)
                self.assertIn("work_experiences", df.columns)
                self.assertIn("skills", df.columns)

                # 验证结果数量
                self.assertEqual(len(df), min(top_n, 10))  # 10 是模拟的总简历数量

                # 验证分数排序
                self.assertTrue(df["total_score"].is_monotonic_decreasing)

                print(f"测试通过！top_n={top_n}，生成的CSV文件内容：")
                print(df)

    unittest.main()
