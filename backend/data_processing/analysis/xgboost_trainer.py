import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import cross_val_score
import optuna
from typing import List, Dict, Any, Tuple

from backend.data_processing.analysis.model_utils import prepare_data, create_preprocessor, evaluate_model, get_feature_importance

def optimize_xgboost(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    categorical_cols: List[str],
    numerical_cols: List[str],
    param_ranges: Dict[str, Any]
) -> Tuple[Pipeline, Dict[str, Any], float]:
    """
    使用Optuna优化XGBoost模型的超参数。

    Args:
        X_train: 训练特征
        y_train: 训练目标
        categorical_cols: 分类特征列名列表
        numerical_cols: 数值特征列名列表
        param_ranges: 超参数搜索范围的字典

    Returns:
        优化后的XGBoost模型管道、最佳参数字典和最佳交叉验证分数
    """
    preprocessor = create_preprocessor(categorical_cols, numerical_cols)

    def objective(trial):
        params = {
            "n_estimators": trial.suggest_int("n_estimators", param_ranges["n_estimators"][0], param_ranges["n_estimators"][1]),
            "max_depth": trial.suggest_int("max_depth", param_ranges["max_depth"][0], param_ranges["max_depth"][1]),
            "learning_rate": trial.suggest_float("learning_rate", param_ranges["learning_rate"][0], param_ranges["learning_rate"][1], log=True),
            "subsample": trial.suggest_float("subsample", param_ranges["subsample"][0], param_ranges["subsample"][1]),
            "colsample_bytree": trial.suggest_float("colsample_bytree", param_ranges["colsample_bytree"][0], param_ranges["colsample_bytree"][1]),
            "min_child_weight": trial.suggest_int("min_child_weight", param_ranges["min_child_weight"][0], param_ranges["min_child_weight"][1]),
            "reg_alpha": trial.suggest_float("reg_alpha", param_ranges["reg_alpha"][0], param_ranges["reg_alpha"][1]),
            "reg_lambda": trial.suggest_float("reg_lambda", param_ranges["reg_lambda"][0], param_ranges["reg_lambda"][1]),
        }

        xgb = XGBClassifier(**params, random_state=42, eval_metric='logloss')
        pipeline = Pipeline(steps=[("preprocessor", preprocessor), ("classifier", xgb)])
        scores = cross_val_score(pipeline, X_train, y_train, cv=5, scoring="roc_auc", n_jobs=-1)
        return np.mean(scores)

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=100, n_jobs=-1)

    best_params = study.best_params
    best_xgb = XGBClassifier(**best_params, random_state=42, eval_metric='logloss')
    best_pipeline = Pipeline(steps=[("preprocessor", preprocessor), ("classifier", best_xgb)])
    best_pipeline.fit(X_train, y_train)
    best_score = study.best_value

    return best_pipeline, best_params, best_score

def train_xgboost(
    df: pd.DataFrame,
    target_column: str,
    feature_columns: List[str],
    test_size: float = 0.3,
    param_ranges: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    训练XGBoost模型并进行评估。

    Args:
        df: 输入数据框
        target_column: 目标变量的列名
        feature_columns: 特征列名列表
        test_size: 测试集占总数据的比例
        param_ranges: 参数搜索范围，如果为None则使用默认值

    Returns:
        包含模型、特征重要性、评估指标和最佳参数的字典
    """
    X_train, X_test, y_train, y_test, categorical_cols, numerical_cols = prepare_data(
        df, target_column, feature_columns, test_size
    )

    # 使用 LabelEncoder 对目标变量进行编码
    le = LabelEncoder()
    y_train_encoded = le.fit_transform(y_train)
    y_test_encoded = le.transform(y_test)

    # 保存标签编码信息
    label_encoding = dict(zip(le.classes_, le.transform(le.classes_)))

    default_param_ranges = {
        "n_estimators": (50, 500),
        "max_depth": (3, 10),
        "learning_rate": (0.01, 1.0),
        "subsample": (0.5, 1.0),
        "colsample_bytree": (0.5, 1.0),
        "min_child_weight": (1, 10),
        "reg_alpha": (0, 10),
        "reg_lambda": (0, 10),
    }
    param_ranges = param_ranges or default_param_ranges

    best_pipeline, best_params, cv_mean_score = optimize_xgboost(
        X_train, y_train_encoded, categorical_cols, numerical_cols, param_ranges
    )

    test_metrics = evaluate_model(best_pipeline, X_test, y_test_encoded)
    feature_importance = get_feature_importance(best_pipeline.named_steps['classifier'], best_pipeline.named_steps['preprocessor'])

    return {
        "model": best_pipeline,
        "feature_importance": feature_importance,
        "cv_mean_score": cv_mean_score,
        "best_params": best_params,
        "label_encoding": label_encoding,
        **test_metrics
    }