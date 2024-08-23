import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import Pipeline
import optuna
from optuna.samplers import TPESampler
from typing import List, Dict, Any, Tuple

from backend.data_processing.analysis.model_utils import (
    prepare_data,
    create_preprocessor,
    evaluate_model,
    get_feature_importance,
)


def optimize_random_forest(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    categorical_cols: List[str],
    numerical_cols: List[str],
    param_ranges: Dict[str, Any],
    problem_type: str,
    n_trials: int = 100,
) -> Tuple[Pipeline, Dict[str, Any], float, int]:
    """
    使用Optuna优化随机森林模型的超参数。

    Args:
        X_train: 训练特征
        y_train: 训练目标
        categorical_cols: 分类特征列名列表
        numerical_cols: 数值特征列名列表
        param_ranges: 超参数搜索范围的字典
        problem_type: 问题类型 ("classification" 或 "regression")
        n_trials: Optuna优化的试验次数

    Returns:
        优化后的随机森林模型管道、最佳参数字典、最佳交叉验证分数和最佳轮次
    """
    preprocessor = create_preprocessor(categorical_cols, numerical_cols)

    def objective(trial):
        params = {
            "n_estimators": trial.suggest_int(
                "n_estimators",
                param_ranges["n_estimators"][0],
                param_ranges["n_estimators"][1],
            ),
            "max_depth": trial.suggest_int(
                "max_depth", param_ranges["max_depth"][0], param_ranges["max_depth"][1]
            ),
            "min_samples_split": trial.suggest_int(
                "min_samples_split",
                param_ranges["min_samples_split"][0],
                param_ranges["min_samples_split"][1],
            ),
            "min_samples_leaf": trial.suggest_int(
                "min_samples_leaf",
                param_ranges["min_samples_leaf"][0],
                param_ranges["min_samples_leaf"][1],
            ),
            "max_features": trial.suggest_categorical(
                "max_features", param_ranges["max_features"]
            ),
        }

        if problem_type == "classification":
            rf = RandomForestClassifier(**params, random_state=42)
            scoring = "roc_auc"
        else:
            rf = RandomForestRegressor(**params, random_state=42)
            scoring = "neg_mean_squared_error"

        pipeline = Pipeline(steps=[("preprocessor", preprocessor), ("classifier", rf)])
        scores = cross_val_score(
            pipeline, X_train, y_train, cv=5, scoring=scoring, n_jobs=-1
        )
        return np.mean(scores)

    study = optuna.create_study(direction="maximize", sampler=TPESampler())
    study.optimize(objective, n_trials=n_trials, n_jobs=-1)

    best_params = study.best_params
    if problem_type == "classification":
        best_rf = RandomForestClassifier(**best_params, random_state=42)
    else:
        best_rf = RandomForestRegressor(**best_params, random_state=42)

    best_pipeline = Pipeline(
        steps=[("preprocessor", preprocessor), ("classifier", best_rf)]
    )
    best_pipeline.fit(X_train, y_train)
    best_score = study.best_value
    best_trial = study.best_trial.number + 1  # 获取最佳轮次（从1开始计数）

    return best_pipeline, best_params, best_score, best_trial


def train_random_forest(
    df: pd.DataFrame,
    target_column: str,
    feature_columns: List[str],
    problem_type: str,
    test_size: float = 0.3,
    param_ranges: Dict[str, Any] = None,
    n_trials: int = 100,
) -> Dict[str, Any]:
    """
    训练随机森林模型并进行评估。

    Args:
        df: 输入数据框
        target_column: 目标变量的列名
        feature_columns: 特征列名列表
        problem_type: 问题类型 ("classification" 或 "regression")
        test_size: 测试集占总数据的比例
        param_ranges: 参数搜索范围，如果为None则使用默认值
        n_trials: Optuna优化的试验次数

    Returns:
        包含模型、特征重要性、评估指标、最佳参数和最佳轮次的字典
    """
    X_train, X_test, y_train, y_test, categorical_cols, numerical_cols = prepare_data(
        df, target_column, feature_columns, test_size
    )

    default_param_ranges = {
        "n_estimators": (10, 200),
        "max_depth": (5, 30),
        "min_samples_split": (2, 20),
        "min_samples_leaf": (1, 20),
        "max_features": ["sqrt", "log2"],
    }
    param_ranges = param_ranges or default_param_ranges

    best_pipeline, best_params, cv_mean_score, best_trial = optimize_random_forest(
        X_train,
        y_train,
        categorical_cols,
        numerical_cols,
        param_ranges,
        problem_type,
        n_trials,
    )

    test_metrics = evaluate_model(best_pipeline, X_test, y_test, problem_type)
    feature_importance = get_feature_importance(
        best_pipeline.named_steps["classifier"],
        best_pipeline.named_steps["preprocessor"],
    )

    results = {
        "model": best_pipeline,
        "feature_importance": feature_importance,
        "cv_mean_score": cv_mean_score,
        "best_params": best_params,
        "best_trial": best_trial,
        **test_metrics,
    }

    # 对于回归问题，CV分数是负的MSE，我们需要取其绝对值
    if problem_type == "regression":
        results["cv_mean_score"] = abs(results["cv_mean_score"])

    return results
