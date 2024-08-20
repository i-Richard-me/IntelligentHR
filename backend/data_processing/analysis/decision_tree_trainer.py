import pandas as pd
import numpy as np
from sklearn.tree import DecisionTreeClassifier
from sklearn.pipeline import Pipeline
from sklearn.model_selection import GridSearchCV
from typing import List, Dict, Any, Tuple

from backend.data_processing.analysis.model_utils import (
    prepare_data,
    create_preprocessor,
    evaluate_model,
    get_feature_importance,
)


def optimize_decision_tree(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    categorical_cols: List[str],
    numerical_cols: List[str],
    param_grid: Dict[str, Any],
) -> Tuple[Pipeline, Dict[str, Any], float]:
    """
    使用GridSearchCV优化决策树模型的超参数。

    Args:
        X_train: 训练特征
        y_train: 训练目标
        categorical_cols: 分类特征列名列表
        numerical_cols: 数值特征列名列表
        param_grid: 参数网格

    Returns:
        优化后的决策树模型管道、最佳参数字典和最佳交叉验证分数
    """
    preprocessor = create_preprocessor(categorical_cols, numerical_cols)
    dt = DecisionTreeClassifier(random_state=42)
    pipeline = Pipeline(steps=[("preprocessor", preprocessor), ("classifier", dt)])

    grid_search = GridSearchCV(pipeline, param_grid, cv=5, scoring="roc_auc", n_jobs=-1)
    grid_search.fit(X_train, y_train)

    return (
        grid_search.best_estimator_,
        grid_search.best_params_,
        grid_search.best_score_,
    )


def train_decision_tree(
    df: pd.DataFrame,
    target_column: str,
    feature_columns: List[str],
    test_size: float = 0.3,
    param_grid: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    训练决策树模型并进行评估。

    Args:
        df: 输入数据框
        target_column: 目标变量的列名
        feature_columns: 特征列名列表
        test_size: 测试集占总数据的比例
        param_grid: 参数网格，如果为None则使用默认值

    Returns:
        包含模型、特征重要性、评估指标和最佳参数的字典
    """
    X_train, X_test, y_train, y_test, categorical_cols, numerical_cols = prepare_data(
        df, target_column, feature_columns, test_size
    )

    default_param_grid = {
        "classifier__max_depth": [2, 4, 5, 6, 7, None],
        "classifier__min_samples_split": [2, 3, 4, 5, 8],
        "classifier__min_samples_leaf": [2, 5, 10, 15, 20, 25],
        "classifier__max_leaf_nodes": [10, 20, 25, 30, 35, 40, 45, None],
    }
    param_grid = param_grid or default_param_grid

    best_pipeline, best_params, cv_mean_score = optimize_decision_tree(
        X_train, y_train, categorical_cols, numerical_cols, param_grid
    )

    test_metrics = evaluate_model(best_pipeline, X_test, y_test)
    feature_importance = get_feature_importance(
        best_pipeline.named_steps["classifier"],
        best_pipeline.named_steps["preprocessor"],
    )

    return {
        "model": best_pipeline,
        "feature_importance": feature_importance,
        "cv_mean_score": cv_mean_score,
        "best_params": best_params,
        **test_metrics,
    }
