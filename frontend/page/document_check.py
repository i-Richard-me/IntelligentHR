import os
import sys
import streamlit as st
import asyncio
from typing import List, Dict, Any

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(project_root)

from frontend.ui_components import show_sidebar, show_footer, apply_common_styles
from backend.document_check.document_check_core import process_document
from utils.env_loader import load_env

# 加载环境变量
load_env()

# 设置页面配置
st.set_page_config(page_title="文档检查工具", page_icon="📄", layout="wide")

# 应用自定义样式
apply_common_styles()

# 显示侧边栏
show_sidebar()

# Unstructured文档解析客户端初始化
import unstructured_client
from unstructured_client.models import operations, shared

client = unstructured_client.UnstructuredClient(
    api_key_auth="",
    server_url=os.getenv("UNSTRUCTURED_API_URL", "http://localhost:8000"),
)


def parse_document(file):
    """解析上传的文档"""
    filename = file.name
    content = file.read()

    req = operations.PartitionRequest(
        partition_parameters=shared.PartitionParameters(
            files=shared.Files(
                content=content,
                file_name=filename,
            ),
            languages=["chi_sim"],
            extract_image_block_types=["Image", "Table"],
            strategy="hi_res",
        ),
    )

    res = client.general.partition(request=req)
    return res.elements


def display_check_results(results: List[Dict[str, Any]]):
    """显示文档检查结果"""
    for result in results:
        st.subheader(f"页面 {result['page_number']} 的检查结果")
        if result["corrections"]:
            for correction in result["corrections"]:
                with st.expander(f"元素 ID: {correction['element_id']}"):
                    st.markdown("**原始文本:**")
                    st.write(correction["original_text"])
                    st.markdown("**修改建议:**")
                    st.write(correction["suggestion"])
                    st.markdown("**修改理由:**")
                    st.write(correction["correction_reason"])
        else:
            st.info("此页面未发现需要修改的内容。")
        st.markdown("---")


def main():
    st.title("📄 智能文档检查工具")
    st.markdown("---")

    st.info(
        """
    欢迎使用智能文档检查工具！本工具利用先进的自然语言处理技术，帮助您快速检查文档中的错别字和表述不通顺的问题。
    支持多种文档格式，包括PDF、Word、PowerPoint等。上传您的文档，让我们开始检查吧！
    """
    )

    uploaded_file = st.file_uploader("上传文档", type=["pdf", "docx", "pptx"])

    if uploaded_file is not None:
        with st.spinner("正在解析文档..."):
            document_content = parse_document(uploaded_file)

        st.success("文档解析完成！")

        if st.button("开始检查"):
            with st.spinner("正在进行文档检查..."):
                results = asyncio.run(process_document(document_content))

            st.success("文档检查完成！")
            display_check_results(results)

    # 显示页脚
    show_footer()


if __name__ == "__main__":
    main()
