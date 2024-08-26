import pandas as pd
import numpy as np
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
from sklearn.pipeline import Pipeline
from sklearn.model_selection import GridSearchCV
from typing import List, Dict, Any, Tuple

from backend.data_processing.analysis.model_utils import (
    BaseModel,
    create_preprocessor,
    evaluate_model,
    get_feature_importance,
)


class DecisionTreeModel(BaseModel):
    def optimize(
        self, X_train, y_train, categorical_cols, numerical_cols, param_grid, n_trials
    ):
        preprocessor = create_preprocessor(categorical_cols, numerical_cols)

        if self.problem_type == "classification":
            dt = DecisionTreeClassifier(random_state=42)
            scoring = "roc_auc"
        else:
            dt = DecisionTreeRegressor(random_state=42)
            scoring = "neg_mean_squared_error"

        pipeline = Pipeline(steps=[("preprocessor", preprocessor), ("classifier", dt)])

        grid_search = GridSearchCV(
            pipeline, param_grid, cv=5, scoring=scoring, n_jobs=-1
        )
        grid_search.fit(X_train, y_train)

        return (
            grid_search.best_estimator_,
            grid_search.best_params_,
            grid_search.best_score_,
            None,  # 决策树使用网格搜索，没有 trial 的概念
        )

    def train(
        self,
        X_train,
        y_train,
        categorical_cols,
        numerical_cols,
        param_ranges=None,
        n_trials=100,
    ):
        default_param_grid = {
            "classifier__max_depth": [2, 4, 6, 8, 10, None],
            "classifier__min_samples_split": [2, 5, 10],
            "classifier__min_samples_leaf": [1, 2, 4],
            "classifier__max_leaf_nodes": [10, 20, 30, None],
        }

        # 如果提供了param_ranges，更新默认值
        if param_ranges:
            default_param_grid.update({f"{k}": v for k, v in param_ranges.items()})

        param_grid = default_param_grid

        print(param_grid)

        best_pipeline, best_params, cv_mean_score, _ = self.optimize(
            X_train, y_train, categorical_cols, numerical_cols, param_grid, n_trials
        )

        self.model = best_pipeline

        results = {
            "model": self.model,
            "feature_importance": self.get_feature_importance(),
            "cv_mean_score": cv_mean_score,
            "best_params": best_params,
        }

        # 对于回归问题，CV分数是负的MSE，我们需要取其绝对值
        if self.problem_type == "regression":
            results["cv_mean_score"] = abs(results["cv_mean_score"])

        return results
