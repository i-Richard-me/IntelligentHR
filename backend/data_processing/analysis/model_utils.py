import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_auc_score, classification_report, confusion_matrix
from typing import List, Dict, Any, Tuple


def prepare_data(
    df: pd.DataFrame,
    target_column: str,
    feature_columns: List[str],
    test_size: float = 0.3,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, List[str], List[str]]:
    """
    准备模型训练和测试数据。

    Args:
        df: 输入数据框
        target_column: 目标变量的列名
        feature_columns: 特征列名列表
        test_size: 测试集占总数据的比例

    Returns:
        训练特征, 测试特征, 训练目标, 测试目标, 分类特征列表, 数值特征列表
    """
    X = df[feature_columns]
    y = df[target_column]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42
    )

    categorical_cols = X.select_dtypes(include=["object"]).columns.tolist()
    numerical_cols = X.select_dtypes(exclude=["object"]).columns.tolist()

    return X_train, X_test, y_train, y_test, categorical_cols, numerical_cols


def create_preprocessor(
    categorical_cols: List[str], numerical_cols: List[str]
) -> ColumnTransformer:
    """
    创建特征预处理器。

    Args:
        categorical_cols: 分类特征列名列表
        numerical_cols: 数值特征列名列表

    Returns:
        预处理器
    """
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), numerical_cols),
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_cols),
        ]
    )


def evaluate_model(
    model: Any, X_test: pd.DataFrame, y_test: pd.Series
) -> Dict[str, Any]:
    """
    评估模型性能。

    Args:
        model: 训练好的模型
        X_test: 测试特征
        y_test: 测试目标

    Returns:
        包含评估指标的字典
    """
    y_test_pred = model.predict(X_test)
    y_test_pred_proba = model.predict_proba(X_test)[:, 1]

    return {
        "test_roc_auc": roc_auc_score(y_test, y_test_pred_proba),
        "test_confusion_matrix": confusion_matrix(y_test, y_test_pred),
        "test_classification_report": classification_report(y_test, y_test_pred),
    }


def get_feature_importance(model: Any, preprocessor: ColumnTransformer) -> pd.Series:
    """
    获取特征重要性。

    Args:
        model: 训练好的模型
        preprocessor: 特征预处理器

    Returns:
        特征重要性系列
    """
    feature_names = preprocessor.get_feature_names_out()
    feature_importance = pd.Series(
        model.feature_importances_,
        index=feature_names,
    ).sort_values(ascending=False)
    return feature_importance
