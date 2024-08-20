import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import sys
import os
import joblib
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(project_root)

from frontend.ui_components import show_sidebar, show_footer, apply_common_styles
from backend.data_processing.analysis.random_forest_trainer import train_random_forest
from backend.data_processing.analysis.decision_tree_trainer import train_decision_tree
from backend.data_processing.analysis.xgboost_trainer import train_xgboost  # 新增导入
from backend.data_processing.analysis.ml_explanations import (
    ML_TOOL_INFO,
    CONFUSION_MATRIX_EXPLANATION,
    CLASSIFICATION_REPORT_EXPLANATION,
    FEATURE_IMPORTANCE_EXPLANATION,
)

# Streamlit 页面配置
st.set_page_config(
    page_title="智能HR助手 - 机器学习建模",
    page_icon="🤖",
)

# 应用自定义样式
apply_common_styles()

# 显示侧边栏
show_sidebar()


# 初始化会话状态
def initialize_session_state():
    default_states = {
        "df": None,
        "model_results": None,
        "target_column": None,
        "feature_columns": None,
        "model_type": "随机森林",
        "param_ranges": {
            "n_estimators": (10, 200),
            "max_depth": (5, 30),
            "min_samples_split": (2, 20),
            "min_samples_leaf": (1, 20),
            "max_features": ["sqrt", "log2"],
        },
        "dt_param_grid": {
            "classifier__max_depth": [2, 4, 5, 6, 7, None],
            "classifier__min_samples_split": [2, 3, 4, 5, 8],
            "classifier__min_samples_leaf": [2, 5, 10, 15, 20, 25],
            "classifier__max_leaf_nodes": [10, 20, 25, 30, 35, 40, 45, None],
        },
        "xgb_param_ranges": {  # 新增 XGBoost 参数范围
            "n_estimators": (50, 500),
            "max_depth": (3, 10),
            "learning_rate": (0.01, 1.0),
            "subsample": (0.5, 1.0),
            "colsample_bytree": (0.5, 1.0),
            "min_child_weight": (1, 10),
            "reg_alpha": (0, 10),
            "reg_lambda": (0, 10),
        },
        "custom_param_ranges": None,
        "model_records": pd.DataFrame(
            columns=[
                "模型ID",
                "模型类型",
                "训练时间",
                "参数",
                "交叉验证分数",
                "测试集分数",
            ]
        ),
    }

    for key, value in default_states.items():
        if key not in st.session_state:
            st.session_state[key] = value


def main():
    st.title("🤖 机器学习建模")
    st.markdown("---")

    display_info_message()

    uploaded_file = upload_file()
    if uploaded_file is None:
        return

    display_data_preview()
    display_column_selection()
    display_model_selection()
    display_model_training_and_advanced_settings()
    display_model_records()
    display_results()
    display_feature_importance()

    show_footer()


def display_info_message():
    st.info(ML_TOOL_INFO)


def upload_file():
    st.markdown('<h2 class="section-title">数据上传</h2>', unsafe_allow_html=True)
    with st.container(border=True):
        uploaded_file = st.file_uploader(
            "上传CSV或Excel文件", type=["csv", "xlsx", "xls"]
        )

        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith(".csv"):
                    st.session_state.df = pd.read_csv(uploaded_file)
                elif uploaded_file.name.endswith((".xls", ".xlsx")):
                    st.session_state.df = pd.read_excel(uploaded_file)
                else:
                    st.error("不支持的文件格式。请上传CSV或Excel文件。")
                    return None

                st.success("文件上传成功！")
                return st.session_state.df

            except Exception as e:
                st.error(f"处理文件时出错：{str(e)}")
                return None

    return None


def display_data_preview():
    if st.session_state.df is not None:
        st.markdown('<h2 class="section-title">数据预览</h2>', unsafe_allow_html=True)
        with st.container(border=True):
            st.write(
                f"数据集包含 {len(st.session_state.df)} 行和 {len(st.session_state.df.columns)} 列"
            )
            st.write(st.session_state.df.head())

            with st.expander("查看数据类型信息", expanded=False):
                st.write(st.session_state.df.dtypes)


def display_column_selection():
    if st.session_state.df is not None:
        st.markdown('<h2 class="section-title">变量选择</h2>', unsafe_allow_html=True)
        with st.container(border=True):
            st.session_state.target_column = st.selectbox(
                "选择目标变量",
                options=st.session_state.df.columns,
                key="target_column_select",
            )
            with st.expander("选择特征变量", expanded=False):
                st.session_state.feature_columns = st.multiselect(
                    "选择特征变量",
                    options=[
                        col
                        for col in st.session_state.df.columns
                        if col != st.session_state.target_column
                    ],
                    default=[
                        col
                        for col in st.session_state.df.columns
                        if col != st.session_state.target_column
                    ],
                    key="feature_columns_select",
                )


def display_model_selection():
    st.markdown('<h2 class="section-title">模型选择</h2>', unsafe_allow_html=True)
    with st.container(border=True):
        st.session_state.model_type = st.radio(
            "选择模型类型",
            ("随机森林", "决策树", "XGBoost"),  # 添加 XGBoost 选项
            key="model_type_radio",
        )


def display_model_training_and_advanced_settings():
    if (
        st.session_state.df is not None
        and st.session_state.target_column
        and st.session_state.feature_columns
    ):
        st.markdown('<h2 class="section-title">模型训练</h2>', unsafe_allow_html=True)
        with st.container(border=True):
            with st.expander("高级设置"):
                if st.session_state.model_type == "随机森林":
                    display_random_forest_settings()
                elif st.session_state.model_type == "决策树":
                    display_decision_tree_settings()
                else:  # XGBoost
                    display_xgboost_settings()

            if st.button("开始训练模型"):
                with st.spinner("正在训练模型，请稍候..."):
                    try:
                        if st.session_state.model_type == "随机森林":
                            train_random_forest_model()
                        elif st.session_state.model_type == "决策树":
                            train_decision_tree_model()
                        else:  # XGBoost
                            train_xgboost_model()

                        st.success("模型训练完成！")
                    except Exception as e:
                        st.error(f"模型训练过程中出错：{str(e)}")


def display_random_forest_settings():
    col1, col2 = st.columns(2)
    with col1:
        n_estimators_range = st.slider(
            "n_estimators 范围",
            min_value=10,
            max_value=500,
            value=st.session_state.param_ranges["n_estimators"],
            step=10,
        )
        max_depth_range = st.slider(
            "max_depth 范围",
            min_value=1,
            max_value=50,
            value=st.session_state.param_ranges["max_depth"],
        )
    with col2:
        min_samples_split_range = st.slider(
            "min_samples_split 范围",
            min_value=2,
            max_value=30,
            value=st.session_state.param_ranges["min_samples_split"],
        )
        min_samples_leaf_range = st.slider(
            "min_samples_leaf 范围",
            min_value=1,
            max_value=30,
            value=st.session_state.param_ranges["min_samples_leaf"],
        )

    max_features_options = st.multiselect(
        "max_features 选项",
        options=["sqrt", "log2"]
        + list(range(1, len(st.session_state.feature_columns) + 1)),
        default=st.session_state.param_ranges["max_features"],
    )

    if st.button("确认随机森林参数设置"):
        st.session_state.custom_param_ranges = {
            "n_estimators": n_estimators_range,
            "max_depth": max_depth_range,
            "min_samples_split": min_samples_split_range,
            "min_samples_leaf": min_samples_leaf_range,
            "max_features": max_features_options,
        }
        st.success("随机森林参数设置已更新，将在下次模型训练时使用。")


def display_decision_tree_settings():
    st.markdown("#### 决策树参数设置")

    def create_param_range(param_name, default_values):
        non_none_values = [v for v in default_values if v is not None]
        min_val, max_val = min(non_none_values), max(non_none_values)
        step = min(
            set(
                non_none_values[i + 1] - non_none_values[i]
                for i in range(len(non_none_values) - 1)
            ),
            default=1,
        )

        col1, col2, col3, col4 = st.columns([3, 3, 3, 2])
        with col1:
            start = st.number_input(f"{param_name} 最小值", value=min_val, step=step)
        with col2:
            end = st.number_input(f"{param_name} 最大值", value=max_val, step=step)
        with col3:
            custom_step = st.number_input(
                f"{param_name} 步长", value=step, min_value=step
            )
        with col4:
            include_none = st.checkbox(
                "包含None", key=f"{param_name}_none", value=None in default_values
            )

        values = list(range(int(start), int(end) + int(custom_step), int(custom_step)))
        if include_none:
            values.append(None)

        return values

    default_params = st.session_state.dt_param_grid
    max_depth = create_param_range("max_depth", default_params["classifier__max_depth"])
    min_samples_split = create_param_range(
        "min_samples_split", default_params["classifier__min_samples_split"]
    )
    min_samples_leaf = create_param_range(
        "min_samples_leaf", default_params["classifier__min_samples_leaf"]
    )
    max_leaf_nodes = create_param_range(
        "max_leaf_nodes", default_params["classifier__max_leaf_nodes"]
    )

    if st.button("确认决策树参数设置"):
        new_param_grid = {
            "classifier__max_depth": max_depth,
            "classifier__min_samples_split": min_samples_split,
            "classifier__min_samples_leaf": min_samples_leaf,
            "classifier__max_leaf_nodes": max_leaf_nodes,
        }

        # 计算参数空间大小
        param_space_size = np.prod([len(v) for v in new_param_grid.values()])

        st.session_state.dt_param_grid = new_param_grid
        st.success(
            f"决策树参数设置已更新，将在下次模型训练时使用。参数空间大小：{param_space_size:,} 种组合。"
        )

        # 可选：添加警告信息
        if param_space_size > 1000000:
            st.warning(
                "警告：参数空间非常大，可能会导致训练时间过长。考虑减少某些参数的范围或增加步长。"
            )


def display_xgboost_settings():
    col1, col2 = st.columns(2)
    with col1:
        n_estimators_range = st.slider(
            "n_estimators 范围",
            min_value=50,
            max_value=1000,
            value=st.session_state.xgb_param_ranges["n_estimators"],
            step=50,
        )
        max_depth_range = st.slider(
            "max_depth 范围",
            min_value=1,
            max_value=15,
            value=st.session_state.xgb_param_ranges["max_depth"],
        )
        learning_rate_range = st.slider(
            "learning_rate 范围",
            min_value=0.01,
            max_value=1.0,
            value=st.session_state.xgb_param_ranges["learning_rate"],
            step=0.01,
        )
    with col2:
        subsample_range = st.slider(
            "subsample 范围",
            min_value=0.5,
            max_value=1.0,
            value=st.session_state.xgb_param_ranges["subsample"],
            step=0.1,
        )
        colsample_bytree_range = st.slider(
            "colsample_bytree 范围",
            min_value=0.5,
            max_value=1.0,
            value=st.session_state.xgb_param_ranges["colsample_bytree"],
            step=0.1,
        )
        min_child_weight_range = st.slider(
            "min_child_weight 范围",
            min_value=1,
            max_value=20,
            value=st.session_state.xgb_param_ranges["min_child_weight"],
        )

    if st.button("确认XGBoost参数设置"):
        st.session_state.xgb_param_ranges = {
            "n_estimators": n_estimators_range,
            "max_depth": max_depth_range,
            "learning_rate": learning_rate_range,
            "subsample": subsample_range,
            "colsample_bytree": colsample_bytree_range,
            "min_child_weight": min_child_weight_range,
            "reg_alpha": st.session_state.xgb_param_ranges["reg_alpha"],
            "reg_lambda": st.session_state.xgb_param_ranges["reg_lambda"],
        }
        st.success("XGBoost参数设置已更新，将在下次模型训练时使用。")


def train_random_forest_model():
    param_ranges = (
        st.session_state.custom_param_ranges
        if st.session_state.custom_param_ranges
        else st.session_state.param_ranges
    )

    st.session_state.model_results = train_random_forest(
        st.session_state.df,
        st.session_state.target_column,
        st.session_state.feature_columns,
        param_ranges=param_ranges,
    )

    add_model_record("随机森林")


def train_decision_tree_model():
    st.session_state.model_results = train_decision_tree(
        st.session_state.df,
        st.session_state.target_column,
        st.session_state.feature_columns,
        param_grid=st.session_state.dt_param_grid,
    )

    add_model_record("决策树")


def train_xgboost_model():
    st.session_state.model_results = train_xgboost(
        st.session_state.df,
        st.session_state.target_column,
        st.session_state.feature_columns,
        param_ranges=st.session_state.xgb_param_ranges,
    )

    add_model_record("XGBoost")


def add_model_record(model_type):
    new_record = pd.DataFrame(
        {
            "模型ID": [f"Model_{len(st.session_state.model_records) + 1}"],
            "模型类型": [model_type],
            "训练时间": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            "参数": [str(st.session_state.model_results["best_params"])],
            "交叉验证分数": [st.session_state.model_results["cv_mean_score"]],
            "测试集分数": [st.session_state.model_results["test_roc_auc"]],
        }
    )
    st.session_state.model_records = pd.concat(
        [st.session_state.model_records, new_record],
        ignore_index=True,
    )


def display_results():
    if st.session_state.model_results:
        st.markdown('<h2 class="section-title">模型结果</h2>', unsafe_allow_html=True)

        st.markdown(
            """
        <style>
        .metric-card {
            border: 1px solid #e1e4e8;
            border-radius: 10px;
            padding: 20px;
            margin: 10px 0;
            background-color: #f6f8fa;
        }
        .metric-value {
            font-size: 24px;
            font-weight: bold;
            color: #0366d6;
        }
        .metric-label {
            font-size: 16px;
            color: #586069;
        }
        </style>
        """,
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            st.markdown("#### 模型性能概览")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-value">{st.session_state.model_results['cv_mean_score']:.4f}</div>
                        <div class="metric-label">交叉验证平均 ROC AUC</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with col2:
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-value">{st.session_state.model_results['test_roc_auc']:.4f}</div>
                        <div class="metric-label">测试集 ROC AUC</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with st.expander("查看最佳模型参数", expanded=False):
                st.json(st.session_state.model_results["best_params"])

            if st.session_state.model_type == "XGBoost":
                label_encoding = st.session_state.model_results.get("label_encoding")
                if label_encoding:
                    st.info("标签编码信息:")
                    for original, encoded in label_encoding.items():
                        st.write(f"  - {original}: {encoded}")
                    st.write("在解释结果时请参考上述标签编码。")

            st.markdown("---")
            st.markdown("#### 混淆矩阵")
            display_confusion_matrix()

            st.markdown("---")
            st.markdown("#### 分类报告")
            st.text(st.session_state.model_results["test_classification_report"])

            with st.expander("分类报告解读", expanded=False):
                st.caption(CLASSIFICATION_REPORT_EXPLANATION)


def display_confusion_matrix():
    cm = st.session_state.model_results["test_confusion_matrix"]
    cm_sum = np.sum(cm)
    cm_percentages = cm / cm_sum * 100

    fig = go.Figure(
        data=go.Heatmap(
            z=cm_percentages,
            x=["预测: 0", "预测: 1"],
            y=["实际: 0", "实际: 1"],
            hoverongaps=False,
            colorscale="Blues",
            text=[
                [f"{v:.1f}%<br>({cm[i][j]})" for j, v in enumerate(row)]
                for i, row in enumerate(cm_percentages)
            ],
            texttemplate="%{text}",
            textfont={"size": 14},
        )
    )
    fig.update_layout(
        title="混淆矩阵 (百分比和实际数量)",
        xaxis_title="预测类别",
        yaxis_title="实际类别",
        width=500,
        height=500,
    )
    st.plotly_chart(fig)

    with st.expander("混淆矩阵解读", expanded=False):
        st.caption(CONFUSION_MATRIX_EXPLANATION)


def display_feature_importance():
    if (
        st.session_state.model_results
        and "feature_importance" in st.session_state.model_results
    ):
        st.markdown('<h2 class="section-title">特征重要性</h2>', unsafe_allow_html=True)

        with st.container(border=True):
            feature_importance = st.session_state.model_results[
                "feature_importance"
            ].sort_values(ascending=True)
            fig = go.Figure(
                data=[
                    go.Bar(
                        x=feature_importance.values,
                        y=feature_importance.index,
                        orientation="h",
                    )
                ]
            )
            fig.update_layout(
                title="特征重要性",
                xaxis_title="重要性得分",
                yaxis_title="特征",
                height=max(500, len(feature_importance) * 20),
                width=800,
            )
            st.plotly_chart(fig)

            with st.expander("特征重要性解释", expanded=False):
                st.caption(FEATURE_IMPORTANCE_EXPLANATION)


def display_model_records():
    if not st.session_state.model_records.empty:
        st.markdown('<h2 class="section-title">模型记录</h2>', unsafe_allow_html=True)
        with st.container(border=True):
            columns_order = [
                "模型ID",
                "模型类型",
                "交叉验证分数",
                "测试集分数",
                "最佳模型",
                "保存",
                "训练时间",
                "参数",
            ]
            temp_df = st.session_state.model_records.reindex(columns=columns_order)
            temp_df["保存"] = False
            temp_df["最佳模型"] = False

            best_model_index = temp_df["交叉验证分数"].idxmax()
            temp_df.loc[best_model_index, "最佳模型"] = True

            edited_df = st.data_editor(
                temp_df,
                column_config={
                    "保存": st.column_config.CheckboxColumn(
                        "保存",
                        help="选择要保存的模型",
                        default=False,
                    ),
                    "最佳模型": st.column_config.CheckboxColumn(
                        "最佳模型",
                        help="交叉验证分数最高的模型",
                        default=False,
                    ),
                    "交叉验证分数": st.column_config.NumberColumn(
                        "交叉验证分数",
                        format="%.4f",
                    ),
                    "测试集分数": st.column_config.NumberColumn(
                        "测试集分数",
                        format="%.4f",
                    ),
                },
                disabled=[
                    "模型ID",
                    "模型类型",
                    "训练时间",
                    "参数",
                    "交叉验证分数",
                    "测试集分数",
                    "最佳模型",
                ],
                hide_index=True,
                column_order=columns_order,
                use_container_width=True,
            )

            save_selected_models(edited_df)


def save_selected_models(edited_df):
    models_to_save = edited_df[edited_df["保存"]]
    if not models_to_save.empty:
        for _, row in models_to_save.iterrows():
            model_id = row["模型ID"]
            model_type = row["模型类型"]
            timestamp = datetime.strptime(row["训练时间"], "%Y-%m-%d %H:%M:%S")
            if (
                st.session_state.model_results
                and st.session_state.model_results["model"]
            ):
                save_model(
                    st.session_state.model_results["model"],
                    model_id,
                    model_type,
                    timestamp,
                )
            else:
                st.warning(f"无法保存模型 {model_id}，模型对象不存在。")


def save_model(model, model_id, model_type, timestamp):
    save_path = os.path.join("data", "ml_models")
    os.makedirs(save_path, exist_ok=True)
    file_name = f"{model_type}_{model_id}_{timestamp.strftime('%Y%m%d_%H%M%S')}.joblib"
    file_path = os.path.join(save_path, file_name)
    joblib.dump(model, file_path)
    st.success(f"模型 {model_id} ({model_type}) 已成功保存到 {file_path}")


if __name__ == "__main__":
    initialize_session_state()
    main()
