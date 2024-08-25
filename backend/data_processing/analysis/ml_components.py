import streamlit as st
import numpy as np


def display_info_message():
    st.info(
        """
    **🤖 机器学习建模与预测工具**

    这个工具允许您训练新的机器学习模型或使用已保存的模型进行预测。

    主要功能包括：
    - 数据上传和预览
    - 模型选择和参数设置
    - 模型训练和评估
    - 使用训练好的模型进行预测
    - 结果可视化和下载
    """
    )


def display_data_split_settings():
    with st.expander("数据划分设置", expanded=False):
        st.markdown("#### 训练集和测试集划分")

        # 使用会话状态来存储当前的test_size值和之前确认的值
        if "current_test_size" not in st.session_state:
            st.session_state.current_test_size = 0.3
        if "confirmed_test_size" not in st.session_state:
            st.session_state.confirmed_test_size = 0.3

        # 滑块用于调整test_size
        new_test_size = st.slider(
            "测试集比例",
            min_value=0.1,
            max_value=0.5,
            value=st.session_state.current_test_size,
            step=0.05,
            help="设置用于测试的数据比例。推荐范围：0.2 - 0.3",
        )

        # 更新当前的test_size值
        st.session_state.current_test_size = new_test_size

        # 添加确认按钮
        if st.button("确认数据划分设置"):
            st.session_state.confirmed_test_size = new_test_size
            st.success(f"数据划分设置已更新。测试集比例：{new_test_size:.2f}")

    # 确保其他部分使用确认后的test_size值
    st.session_state.test_size = st.session_state.confirmed_test_size


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

    st.session_state.rf_n_trials = st.slider(
        "优化迭代次数 (n_trials)",
        min_value=50,
        max_value=500,
        value=st.session_state.rf_n_trials,
        step=10,
        help="增加迭代次数可能提高模型性能，但会显著增加训练时间。",
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

    if st.session_state.rf_n_trials > 300:
        st.warning("注意：设置较大的迭代次数可能会显著增加训练时间。")


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

    st.session_state.xgb_n_trials = st.slider(
        "优化迭代次数 (n_trials)",
        min_value=100,
        max_value=2000,
        value=st.session_state.xgb_n_trials,
        step=50,
        help="增加迭代次数可能提高模型性能，但会显著增加训练时间。",
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

    if st.session_state.xgb_n_trials > 500:
        st.warning("注意：设置较大的迭代次数可能会显著增加训练时间。")


def display_linear_regression_settings():
    st.markdown("#### 线性回归设置")

    use_cv = st.checkbox(
        "使用交叉验证",
        value=st.session_state.use_cv_for_linear_regression,
        help="启用交叉验证可以提供更稳定的模型评估，但会增加训练时间。",
    )

    if st.button("确认线性回归设置"):
        st.session_state.use_cv_for_linear_regression = use_cv
        st.success("线性回归设置已更新，将在下次模型训练时使用。")

    st.info("线性回归模型不需要额外的参数设置。它将自动找到最佳的系数值。")


def display_model_selection():
    st.markdown("## 模型选择")
    with st.container(border=True):
        model_options = ["随机森林", "决策树", "XGBoost", "线性回归"]

        if st.session_state.problem_type == "classification":
            model_options.remove("线性回归")

        st.session_state.model_type = st.radio(
            "选择模型类型",
            model_options,
            key="model_type_radio",
        )

        if st.session_state.model_type == "线性回归":
            display_linear_regression_settings()
        elif st.session_state.model_type == "随机森林":
            display_random_forest_settings()
        elif st.session_state.model_type == "决策树":
            display_decision_tree_settings()
        else:  # XGBoost
            display_xgboost_settings()