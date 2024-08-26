import pandas as pd
import numpy as np
from xgboost import XGBClassifier, XGBRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import cross_val_score
import optuna
import logging
from typing import List, Dict, Any, Tuple

from backend.data_processing.analysis.model_utils import (
    BaseModel,
    create_preprocessor,
    evaluate_model,
    get_feature_importance,
)


class XGBoostModel(BaseModel):
    def __init__(self, problem_type):
        super().__init__(problem_type)
        self.label_encoder = None
        self.logger = logging.getLogger(__name__)

    def optimize(
        self, X_train, y_train, categorical_cols, numerical_cols, param_ranges, n_trials
    ):
        preprocessor = create_preprocessor(categorical_cols, numerical_cols)

        def objective(trial):
            params = {
                "n_estimators": trial.suggest_int(
                    "n_estimators",
                    param_ranges["n_estimators"][0],
                    param_ranges["n_estimators"][1],
                ),
                "max_depth": trial.suggest_int(
                    "max_depth",
                    param_ranges["max_depth"][0],
                    param_ranges["max_depth"][1],
                ),
                "learning_rate": trial.suggest_float(
                    "learning_rate",
                    param_ranges["learning_rate"][0],
                    param_ranges["learning_rate"][1],
                    log=True,
                ),
                "subsample": trial.suggest_float(
                    "subsample",
                    param_ranges["subsample"][0],
                    param_ranges["subsample"][1],
                ),
                "colsample_bytree": trial.suggest_float(
                    "colsample_bytree",
                    param_ranges["colsample_bytree"][0],
                    param_ranges["colsample_bytree"][1],
                ),
                "min_child_weight": trial.suggest_int(
                    "min_child_weight",
                    param_ranges["min_child_weight"][0],
                    param_ranges["min_child_weight"][1],
                ),
                "reg_alpha": trial.suggest_float(
                    "reg_alpha",
                    param_ranges["reg_alpha"][0],
                    param_ranges["reg_alpha"][1],
                ),
                "reg_lambda": trial.suggest_float(
                    "reg_lambda",
                    param_ranges["reg_lambda"][0],
                    param_ranges["reg_lambda"][1],
                ),
            }

            if self.problem_type == "classification":
                xgb = XGBClassifier(**params, random_state=42, eval_metric="logloss")
                scoring = "roc_auc"
            else:
                xgb = XGBRegressor(**params, random_state=42, eval_metric="rmse")
                scoring = "neg_mean_squared_error"

            pipeline = Pipeline(
                steps=[("preprocessor", preprocessor), ("classifier", xgb)]
            )
            scores = cross_val_score(
                pipeline, X_train, y_train, cv=5, scoring=scoring, n_jobs=-1
            )
            return np.mean(scores)

        self.logger.info(f"Starting optimization with {n_trials} trials")
        study = optuna.create_study(direction="maximize")
        study.optimize(objective, n_trials=n_trials, n_jobs=-1)
        self.logger.info(
            f"Optimization completed. Best trial: {study.best_trial.number}"
        )

        best_params = study.best_params
        if self.problem_type == "classification":
            best_xgb = XGBClassifier(
                **best_params, random_state=42, eval_metric="logloss"
            )
        else:
            best_xgb = XGBRegressor(**best_params, random_state=42, eval_metric="rmse")

        best_pipeline = Pipeline(
            steps=[("preprocessor", preprocessor), ("classifier", best_xgb)]
        )
        best_pipeline.fit(X_train, y_train)
        best_score = study.best_value
        best_trial = study.best_trial.number + 1

        return best_pipeline, best_params, best_score, best_trial

    def train(
        self,
        X_train,
        y_train,
        categorical_cols,
        numerical_cols,
        param_ranges=None,
        n_trials=100,
    ):
        self.logger.info(f"Starting XGBoost training for {self.problem_type} problem")

        if self.problem_type == "classification":
            self.label_encoder = LabelEncoder()
            y_train_encoded = self.label_encoder.fit_transform(y_train)
        else:
            y_train_encoded = np.array(y_train)  # 确保y_train是numpy数组

        self.logger.info(
            f"Shape of X_train: {X_train.shape}, Shape of y_train: {y_train_encoded.shape}"
        )

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

        if param_ranges:
            default_param_ranges.update(param_ranges)

        param_ranges = default_param_ranges

        best_pipeline, best_params, cv_mean_score, best_trial = self.optimize(
            X_train,
            y_train_encoded,
            categorical_cols,
            numerical_cols,
            param_ranges,
            n_trials,
        )

        self.model = best_pipeline

        results = {
            "model": self.model,
            "feature_importance": self.get_feature_importance(),
            "cv_mean_score": cv_mean_score,
            "best_params": best_params,
            "best_trial": best_trial,
        }

        if self.problem_type == "classification":
            results["label_encoding"] = dict(
                zip(
                    self.label_encoder.classes_,
                    self.label_encoder.transform(self.label_encoder.classes_),
                )
            )
        else:
            results["cv_mean_score"] = abs(results["cv_mean_score"])

        self.logger.info(f"XGBoost training completed. CV mean score: {cv_mean_score}")
        return results

    def evaluate(self, X_test, y_test):
        self.logger.info("Starting model evaluation")
        if self.problem_type == "classification" and self.label_encoder is not None:
            y_test_encoded = self.label_encoder.transform(y_test)
        else:
            y_test_encoded = np.array(y_test)
        return evaluate_model(self.model, X_test, y_test_encoded, self.problem_type)
