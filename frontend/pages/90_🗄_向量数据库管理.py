import io
import os
import sys
import csv
from typing import List, Dict

import streamlit as st
import pandas as pd
from pymilvus import (
    connections,
    Collection,
    FieldSchema,
    CollectionSchema,
    DataType,
    utility,
)

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(project_root)

from utils.llm_tools import CustomEmbeddings
from frontend.ui_components import show_sidebar, show_footer, apply_common_styles

# 设置页面配置
st.set_page_config(page_title="智能HR助手 - Milvus数据库管理", page_icon="🗄️")

# 应用自定义样式
apply_common_styles()

# 显示侧边栏
show_sidebar()

# Milvus连接配置
MILVUS_HOST = "localhost"
MILVUS_PORT = "19530"
MILVUS_DB = "examples"
COLLECTION_NAME = "data_operation_examples"

# 所需的列名
REQUIRED_COLUMNS = ["用户上传的表格", "用户查询", "输出"]


def connect_to_milvus():
    """连接到Milvus数据库"""
    connections.connect(
        alias="default", host=MILVUS_HOST, port=MILVUS_PORT, db_name=MILVUS_DB
    )


def create_milvus_collection(collection_name: str, dim: int):
    """创建Milvus集合"""
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="user_tables", dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(name="user_query", dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(name="output", dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
    ]
    schema = CollectionSchema(fields, "Example collection")
    collection = Collection(collection_name, schema)
    return collection


def insert_examples_to_milvus(examples: List[Dict], collection_name: str):
    """将示例插入到Milvus数据库"""
    connect_to_milvus()

    embeddings = CustomEmbeddings(api_key=os.getenv("OPENAI_API_KEY_SILICONCLOUD"))

    user_tables = []
    user_queries = []
    outputs = []
    vectors = []

    for example in examples:
        user_tables.append(example["用户上传的表格"])
        user_query = example["用户查询"]
        user_queries.append(user_query)
        outputs.append(example["输出"])
        vector = embeddings.embed_query(user_query)
        vectors.append(vector)

    if not utility.has_collection(collection_name):
        collection = create_milvus_collection(collection_name, len(vectors[0]))
    else:
        collection = Collection(collection_name)

    collection.insert([user_tables, user_queries, outputs, vectors])

    index_params = {
        "metric_type": "L2",
        "index_type": "IVF_FLAT",
        "params": {"nlist": 1024},
    }
    collection.create_index("embedding", index_params)
    collection.load()

    connections.disconnect("default")
    return len(examples)


def process_csv_file(file):
    """处理上传的CSV文件"""
    examples = []
    csv_file = io.StringIO(file.getvalue().decode("utf-8"))
    df = pd.read_csv(csv_file)

    # 检查是否包含所有必需的列
    missing_columns = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing_columns:
        raise ValueError(f"CSV文件缺少以下列: {', '.join(missing_columns)}")

    for _, row in df.iterrows():
        example = {col: row[col] for col in REQUIRED_COLUMNS}
        examples.append(example)

    return examples


def main():
    st.title("🗄️ Milvus数据库管理")
    st.markdown("---")

    st.info(
        f"""
    这个工具允许您上传CSV文件来更新Milvus数据库中的examples。
    CSV文件必须包含以下列：{', '.join(REQUIRED_COLUMNS)}
    """
    )

    # 文件上传
    uploaded_file = st.file_uploader("上传CSV文件", type=["csv"])

    if uploaded_file is not None:
        try:
            examples = process_csv_file(uploaded_file)
            st.success(f"成功读取 {len(examples)} 条记录")

            # 显示数据预览
            st.subheader("数据预览")
            preview_df = pd.DataFrame(examples[:5])  # 只显示前5条记录
            st.dataframe(preview_df)

            if st.button("插入到Milvus数据库"):
                with st.spinner("正在插入数据..."):
                    inserted_count = insert_examples_to_milvus(
                        examples, COLLECTION_NAME
                    )
                st.success(f"成功插入 {inserted_count} 条记录到Milvus数据库")
        except ValueError as ve:
            st.error(f"CSV文件格式错误: {str(ve)}")
        except Exception as e:
            st.error(f"处理文件时出错: {str(e)}")
            st.error("请确保CSV文件格式正确，并且包含所有必需的列。")

    show_footer()


if __name__ == "__main__":
    main()
