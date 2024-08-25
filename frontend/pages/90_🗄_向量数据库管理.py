import io
import os
import sys
import json
import time
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
st.set_page_config(page_title="智能HR助手 - Milvus数据库管理", page_icon="🗄️", layout="wide")

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

def get_collection_stats(collection_name: str) -> Dict:
    """获取集合的统计信息"""
    connect_to_milvus()
    collection = Collection(collection_name)
    collection.load()
    
    stats = {
        "实体数量": collection.num_entities,
        "字段数量": len(collection.schema.fields) - 1,  # 减去自动生成的 id 字段
        "索引类型": collection.index().params.get("index_type", "未知"),
    }
    
    connections.disconnect("default")
    return stats

def display_db_management_info():
    st.info("""
    **🗄️ Milvus数据库管理**

    Milvus数据库管理工具用于高效管理和更新向量数据库中的示例数据。
    它支持CSV文件上传、数据预览和批量插入功能，便于维护和扩展向量数据集。
    通过这个工具，您可以轻松地将结构化数据转换为向量表示并存储在Milvus中，
    为后续的相似度搜索和智能匹配提供基础。
    """)

def display_workflow():
    with st.expander("📋 查看Milvus数据库管理工作流程", expanded=False):
        st.markdown("""
        **1. 选择Collection**
        从配置中选择要操作的数据集合。

        **2. 上传CSV文件**
        上传包含示例数据的CSV文件。

        **3. 数据预览**
        预览上传的数据，确保格式正确。

        **4. 向量化处理**
        将文本数据转换为向量表示。

        **5. 数据插入**
        将处理后的数据插入Milvus数据库。

        **6. 索引创建**
        为插入的数据创建索引，优化检索性能。
        """)

def main():
    st.title("🗄️ Milvus数据库管理")
    st.markdown("---")

    # 显示功能介绍
    display_db_management_info()
    st.markdown("---")

    # 显示工作流程
    display_workflow()
    st.markdown("---")

    # Collection 选择
    st.header("选择 Collection")
    with st.container(border=True):
        collection_names = list(CONFIG["collections"].keys())
        selected_collection = st.selectbox("选择要操作的Collection", collection_names)
        collection_config = CONFIG["collections"][selected_collection]

        # 显示Collection信息和统计
        st.subheader("Collection信息")
        st.write(f"名称: {collection_config['name']}")
        st.write(f"描述: {collection_config['description']}")
        st.write("字段:")
        for field in collection_config['fields']:
            st.write(f"- {field['name']}: {field['description']}")
    
        st.subheader("数据统计")
        connect_to_milvus()
        if utility.has_collection(collection_config['name']):
            stats = get_collection_stats(collection_config['name'])
            st.write(f"实体数量: {stats['实体数量']}")
            st.write(f"字段数量: {stats['字段数量']}")
            st.write(f"索引类型: {stats['索引类型']}")
        else:
            st.info("该Collection尚未创建")
        connections.disconnect("default")

    st.header("上传和插入数据")
    with st.container(border=True):
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
                    
                    # 更新统计信息（增加延迟）
                    st.subheader("更新后的数据统计")
                    time.sleep(3)  # 增加3秒延迟
                    connect_to_milvus()
                    if utility.has_collection(collection_config['name']):
                        updated_stats = get_collection_stats(collection_config['name'])
                        st.write(f"实体数量: {updated_stats['实体数量']}")
                        st.write(f"字段数量: {updated_stats['字段数量']}")
                        st.write(f"索引类型: {updated_stats['索引类型']}")
                    connections.disconnect("default")

            except ValueError as ve:
                st.error(f"CSV文件格式错误: {str(ve)}")
            except Exception as e:
                st.error(f"处理文件时出错: {str(e)}")
                st.error("请确保CSV文件格式正确，并且包含所有必需的列。")

    show_footer()

if __name__ == "__main__":
    main()