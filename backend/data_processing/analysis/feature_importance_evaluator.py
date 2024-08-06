import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.model_selection import cross_val_score
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
import optuna
from typing import List, Dict, Tuple, Union
import shap


def encode_categorical_variables(
    df: pd.DataFrame, categorical_columns: List[str]
) -> pd.DataFrame:
    """
    对数据框中的分类变量进行编码。

    Args:
        df (pd.DataFrame): 输入的数据框。
        categorical_columns (List[str]): 需要编码的分类变量列名列表。

    Returns:
        pd.DataFrame: 包含编码后分类变量的数据框。
    """
    encoder = LabelEncoder()
    for column in categorical_columns:
        df[f"{column}_encoded"] = encoder.fit_transform(df[column].astype(str))
    return df


def optimize_random_forest(
    X: pd.DataFrame, y: pd.Series, param_ranges: Dict
) -> Tuple[RandomForestRegressor, Dict]:
    """
    使用Optuna优化随机森林模型的超参数。

    Args:
        X (pd.DataFrame): 特征数据框。
        y (pd.Series): 目标变量系列。
        param_ranges (Dict): 超参数搜索范围的字典。

    Returns:
        Tuple[RandomForestRegressor, Dict]: 优化后的随机森林模型和最佳参数字典。
    """
    numerical_cols = X.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = X.select_dtypes(exclude=[np.number]).columns.tolist()

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), numerical_cols),
            ("cat", LabelEncoder(), categorical_cols),
        ]
    )

    def objective(trial):
        """
        Optuna的目标函数，用于优化随机森林模型。

        Args:
            trial: Optuna试验对象。

        Returns:
            float: 负均方误差(用于最小化)。
        """
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

        rf = RandomForestRegressor(**params, random_state=42)

        pipeline = Pipeline(steps=[("preprocessor", preprocessor), ("regressor", rf)])

        scores = cross_val_score(
            pipeline, X, y, cv=5, scoring="neg_mean_squared_error", n_jobs=-1
        )
        return -scores.mean()

    study = optuna.create_study(direction="minimize")
    study.optimize(objective, n_trials=100, n_jobs=-1)

    best_params = study.best_params
    best_model = RandomForestRegressor(**best_params, random_state=42)
    best_model.fit(X, y)

    return best_model, best_params


def random_forest_analysis(
    X: pd.DataFrame, y: pd.Series, use_optuna: bool, param_ranges: Dict
) -> Tuple[RandomForestRegressor, pd.Series, Dict]:
    """
    执行随机森林分析，可选择是否使用Optuna进行超参数优化。

    Args:
        X (pd.DataFrame): 特征数据框。
        y (pd.Series): 目标变量系列。
        use_optuna (bool): 是否使用Optuna进行超参数优化。
        param_ranges (Dict): 超参数搜索范围的字典。

    Returns:
        Tuple[RandomForestRegressor, pd.Series, Dict]: 训练好的模型、特征重要性和最佳参数（如果使用了Optuna）。
    """
    if use_optuna:
        model, best_params = optimize_random_forest(X, y, param_ranges)
    else:
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X, y)
        best_params = None

    feature_importance = pd.Series(
        model.feature_importances_, index=X.columns
    ).sort_values(ascending=False)
    return model, feature_importance, best_params


def linear_regression_analysis(
    X: pd.DataFrame, y: pd.Series
) -> Tuple[LinearRegression, pd.Series]:
    """
    执行线性回归分析并计算特征影响。

    Args:
        X (pd.DataFrame): 特征数据框。
        y (pd.Series): 目标变量系列。

    Returns:
        Tuple[LinearRegression, pd.Series]: 训练好的线性回归模型和特征影响度。
    """
    model = LinearRegression()
    model.fit(X, y)
    impact = pd.Series(np.abs(model.coef_), index=X.columns)
    normalized_impact = impact / impact.sum()
    return model, normalized_impact.sort_values(ascending=False)


def shap_analysis(
    model: Union[LinearRegression, RandomForestRegressor], X: pd.DataFrame
) -> pd.Series:
    """
    使用SHAP值分析模型的特征重要性。

    Args:
        model (Union[LinearRegression, RandomForestRegressor]): 训练好的模型。
        X (pd.DataFrame): 特征数据框。

    Returns:
        pd.Series: 基于SHAP值的特征重要性。
    """
    if isinstance(model, LinearRegression):
        explainer = shap.LinearExplainer(model, X)
    else:
        explainer = shap.TreeExplainer(model)

    shap_values = explainer.shap_values(X)
    if isinstance(shap_values, list):  # 处理多输出模型
        shap_values = shap_values[0]
    feature_importance = pd.Series(
        np.abs(shap_values).mean(0), index=X.columns
    ).sort_values(ascending=False)
    return feature_importance


def calculate_shap_dependence(
    model: Union[LinearRegression, RandomForestRegressor], X: pd.DataFrame, feature: str
) -> Tuple[np.ndarray, np.ndarray]:
    """
    计算指定特征的SHAP依赖值。

    Args:
        model (Union[LinearRegression, RandomForestRegressor]): 训练好的模型。
        X (pd.DataFrame): 特征数据框。
        feature (str): 要分析的特征名称。

    Returns:
        Tuple[np.ndarray, np.ndarray]: 特征值和对应的SHAP值。
    """
    if isinstance(model, LinearRegression):
        explainer = shap.LinearExplainer(model, X)
    else:
        explainer = shap.TreeExplainer(model)

    shap_values = explainer.shap_values(X)
    if isinstance(shap_values, list):
        shap_values = shap_values[0]

    feature_index = X.columns.get_loc(feature)
    return X[feature].values, shap_values[:, feature_index]


def filter_dataframe(
    df: pd.DataFrame, filters: Dict[str, Tuple[str, Union[List, float, None]]]
) -> pd.DataFrame:
    """
    根据指定的过滤条件筛选数据框。

    Args:
        df (pd.DataFrame): 要筛选的数据框。
        filters (Dict[str, Tuple[str, Union[List, float, None]]]): 过滤条件字典。

    Returns:
        pd.DataFrame: 筛选后的数据框。
    """
    for column, (filter_type, values) in filters.items():
        if filter_type == "包含":
            df = df[df[column].isin(values)]
        elif filter_type == "不包含":
            df = df[~df[column].isin(values)]
        elif filter_type == "大于":
            df = df[df[column] > values]
        elif filter_type == "大于等于":
            df = df[df[column] >= values]
        elif filter_type == "小于":
            df = df[df[column] < values]
        elif filter_type == "小于等于":
            df = df[df[column] <= values]
        elif filter_type == "等于":
            df = df[df[column] == values]
        elif filter_type == "不等于":
            df = df[df[column] != values]
        elif filter_type == "之间":
            df = df[(df[column] >= values[0]) & (df[column] <= values[1])]
        elif filter_type == "为空":
            df = df[df[column].isna()]
        elif filter_type == "非空":
            df = df[df[column].notna()]
    return df
