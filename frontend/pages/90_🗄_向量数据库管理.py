import io
import os
import sys
import json
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

# 加载配置文件
with open("data/config/collections_config.json", "r", encoding="utf-8") as f:
    CONFIG = json.load(f)


def connect_to_milvus():
    """连接到Milvus数据库"""
    connections.connect(
        alias="default", host=MILVUS_HOST, port=MILVUS_PORT, db_name=MILVUS_DB
    )


def create_milvus_collection(collection_config: Dict, dim: int):
    """创建Milvus集合"""
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    ]
    for field in collection_config["fields"]:
        fields.append(
            FieldSchema(name=field["name"], dtype=DataType.VARCHAR, max_length=65535)
        )
    fields.append(FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim))

    schema = CollectionSchema(fields, collection_config["description"])
    collection = Collection(collection_config["name"], schema)
    return collection


def insert_examples_to_milvus(examples: List[Dict], collection_config: Dict):
    """将示例插入到Milvus数据库"""
    connect_to_milvus()

    embeddings = CustomEmbeddings(api_key=os.getenv("OPENAI_API_KEY_SILICONCLOUD"))

    data = {field["name"]: [] for field in collection_config["fields"]}
    vectors = []

    for example in examples:
        for field in collection_config["fields"]:
            data[field["name"]].append(example[field["name"]])
        vector = embeddings.embed_query(example[collection_config["embedding_field"]])
        vectors.append(vector)

    if not utility.has_collection(collection_config["name"]):
        collection = create_milvus_collection(collection_config, len(vectors[0]))
    else:
        collection = Collection(collection_config["name"])

    insert_data = list(data.values()) + [vectors]
    collection.insert(insert_data)

    index_params = {
        "metric_type": "L2",
        "index_type": "IVF_FLAT",
        "params": {"nlist": 1024},
    }
    collection.create_index("embedding", index_params)
    collection.load()

    connections.disconnect("default")
    return len(examples)


def process_csv_file(file, collection_config: Dict):
    """处理上传的CSV文件"""
    examples = []
    csv_file = io.StringIO(file.getvalue().decode("utf-8"))
    df = pd.read_csv(csv_file)

    required_columns = [field["name"] for field in collection_config["fields"]]

    # 检查是否包含所有必需的列
    missing_columns = set(required_columns) - set(df.columns)
    if missing_columns:
        raise ValueError(f"CSV文件缺少以下列: {', '.join(missing_columns)}")

    for _, row in df.iterrows():
        example = {col: row[col] for col in required_columns}
        examples.append(example)

    return examples


def main():
    st.title("🗄️ Milvus数据库管理")
    st.markdown("---")

    # Collection 选择
    collection_names = list(CONFIG["collections"].keys())
    selected_collection = st.selectbox("选择要操作的Collection", collection_names)
    collection_config = CONFIG["collections"][selected_collection]

    st.info(
        f"""
    当前选择的Collection: {collection_config['name']}
    描述: {collection_config['description']}
    这个工具允许您上传CSV文件来更新Milvus数据库中的examples。
    CSV文件必须包含以下列：{', '.join([field['name'] for field in collection_config['fields']])}
    """
    )

    # 文件上传
    uploaded_file = st.file_uploader("上传CSV文件", type=["csv"])

    if uploaded_file is not None:
        try:
            examples = process_csv_file(uploaded_file, collection_config)
            st.success(f"成功读取 {len(examples)} 条记录")

            # 显示数据预览
            st.subheader("数据预览")
            preview_df = pd.DataFrame(examples[:5])  # 只显示前5条记录
            st.dataframe(preview_df)

            if st.button("插入到Milvus数据库"):
                with st.spinner("正在插入数据..."):
                    inserted_count = insert_examples_to_milvus(
                        examples, collection_config
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
