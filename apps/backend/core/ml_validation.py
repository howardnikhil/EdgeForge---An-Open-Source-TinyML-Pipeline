"""Dataset target type detection and task/algorithm validation for EdgeForge."""
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
from fastapi import HTTPException, status


def inspect_dataset_target(df: pd.DataFrame, target_column: Optional[str] = "label") -> Dict[str, Any]:
    """Inspect dataset schema, determine target column type, task suggestion, class balance, and data warnings.

    Target types:
    - categorical
    - boolean
    - numeric discrete/class-like
    - numeric continuous
    - datetime
    - unsupported
    """
    if df is None or df.empty:
        return {
            "target_column": target_column or "none",
            "target_type": "unsupported",
            "task_suggestion": "unsupported",
            "classes": [],
            "feature_columns": [],
            "num_samples": 0,
            "num_unique_targets": 0,
            "size_info": analyze_dataset_size(0),
            "class_balance": {"is_balanced": True, "balance_status": "balanced", "warning": None},
            "leakage_info": {"has_duplicates": False, "warning": None},
        }

    # Determine target column
    selected_target = target_column
    if not selected_target or selected_target not in df.columns:
        if "label" in df.columns:
            selected_target = "label"
        elif "target" in df.columns:
            selected_target = "target"
        elif "class" in df.columns:
            selected_target = "class"
        else:
            selected_target = df.columns[-1]

    series = df[selected_target]
    n_samples = len(df)
    non_null_series = series.dropna()
    n_unique = int(non_null_series.nunique())

    target_type = "unsupported"
    task_suggestion = "unsupported"
    classes: List[str] = []

    if pd.api.types.is_bool_dtype(series):
        target_type = "boolean"
        task_suggestion = "classification"
        classes = [str(c) for c in non_null_series.unique().tolist()]
    elif pd.api.types.is_datetime64_any_dtype(series):
        target_type = "datetime"
        task_suggestion = "unsupported"
    elif pd.api.types.is_string_dtype(series) or pd.api.types.is_object_dtype(series) or isinstance(series.dtype, pd.CategoricalDtype):
        target_type = "categorical"
        task_suggestion = "classification"
        classes = [str(c) for c in non_null_series.unique().tolist()]
    elif pd.api.types.is_numeric_dtype(series):
        # Check if values are discrete integers / class-like or continuous floats
        is_int_like = (non_null_series % 1 == 0).all() if len(non_null_series) > 0 else False
        if is_int_like and n_unique <= min(50, max(2, int(0.2 * n_samples))):
            target_type = "numeric discrete/class-like"
            task_suggestion = "classification"
            classes = [str(c) for c in sorted(non_null_series.unique().tolist())]
        else:
            target_type = "numeric continuous"
            task_suggestion = "regression"
    else:
        target_type = "unsupported"
        task_suggestion = "unsupported"

    feature_columns = [c for c in df.columns if c != selected_target]

    size_info = analyze_dataset_size(n_samples)
    class_balance = analyze_class_balance(df, selected_target) if task_suggestion == "classification" else {"is_balanced": True, "balance_status": "balanced", "warning": None}
    leakage_info = detect_duplicates_and_leakage(df, feature_columns)

    return {
        "target_column": selected_target,
        "target_type": target_type,
        "task_suggestion": task_suggestion,
        "classes": classes,
        "feature_columns": feature_columns,
        "num_samples": n_samples,
        "num_unique_targets": n_unique,
        "size_info": size_info,
        "class_balance": class_balance,
        "leakage_info": leakage_info,
        "sensor_note": "Random sample split used. For sequential sensor recordings, group/window-aware validation is recommended.",
    }


def analyze_dataset_size(n_samples: int) -> dict:
    """Analyze dataset size and return reliability assessment."""
    if n_samples < 30:
        return {
            "size_warning": f"⚠ Small dataset ({n_samples} samples available). Model metrics may have high variance and may not reliably represent real-world generalization.",
            "reliability": "low",
            "evidence_level": "limited evidence",
        }
    elif n_samples < 100:
        return {
            "size_warning": f"Moderate dataset size ({n_samples} samples). Cross-validation is recommended for reliable performance estimation.",
            "reliability": "moderate",
            "evidence_level": "moderate evidence",
        }
    else:
        return {
            "size_warning": None,
            "reliability": "high",
            "evidence_level": "sufficient evidence",
        }


def analyze_class_balance(df: pd.DataFrame, target_column: str) -> dict:
    """Analyze class distribution balance."""
    if target_column not in df.columns:
        return {"is_balanced": True, "balance_status": "balanced", "warning": None, "class_counts": {}}

    counts = df[target_column].value_counts().to_dict()
    if not counts:
        return {"is_balanced": True, "balance_status": "balanced", "warning": None, "class_counts": {}}

    min_c = min(counts.values())
    max_c = max(counts.values())
    ratio = max_c / min_c if min_c > 0 else float("inf")

    if ratio <= 1.5:
        status_str = "balanced"
        warning = None
    elif ratio <= 3.0:
        status_str = "moderate_imbalance"
        warning = f"Moderate class imbalance detected (ratio {ratio:.1f}:1)."
    else:
        status_str = "severe_imbalance"
        warning = f"⚠ Severe class imbalance detected: Majority class has {max_c} samples vs minority class {min_c} samples (ratio {ratio:.1f}:1)."

    return {
        "is_balanced": ratio <= 1.5,
        "balance_status": status_str,
        "imbalance_ratio": round(ratio, 2) if min_c > 0 else None,
        "min_class_count": min_c,
        "max_class_count": max_c,
        "warning": warning,
        "class_counts": {str(k): int(v) for k, v in counts.items()},
    }


def detect_duplicates_and_leakage(df: pd.DataFrame, feature_columns: List[str]) -> dict:
    """Detect duplicate sample rows or identical feature vectors."""
    duplicate_rows = int(df.duplicated().sum())
    dup_features = int(df[feature_columns].duplicated().sum()) if feature_columns else 0

    warning = None
    if duplicate_rows > 0 or dup_features > 0:
        warning = f"⚠ Potential data leakage: {dup_features} identical or near-identical sample feature vectors detected in dataset."

    return {
        "duplicate_rows": duplicate_rows,
        "duplicate_feature_vectors": dup_features,
        "has_duplicates": dup_features > 0,
        "warning": warning,
    }


def calculate_cv_folds(n_samples: int, min_class_count: Optional[int] = None) -> int:
    """Calculate valid stratified K-Fold cross validation count."""
    if n_samples < 4:
        return 0
    if min_class_count is not None:
        if min_class_count < 2:
            return 0
        return max(2, min(5, min_class_count))
    return max(2, min(5, n_samples // 3))


def check_stratification_possibility(df: pd.DataFrame, target_column: str, task_type: str) -> Tuple[bool, Optional[str]]:
    """Determine if stratified split is possible for dataset target."""
    if task_type != "classification":
        return False, "Stratification is only applicable for classification tasks."
    if target_column not in df.columns:
        return False, f"Target column '{target_column}' not found."

    counts = df[target_column].value_counts()
    min_c = counts.min() if not counts.empty else 0
    if min_c < 2:
        return False, f"Stratification impossible: At least one class has fewer than 2 samples (smallest class count: {min_c})."
    return True, None


def validate_task_compatibility(
    target_info: Dict[str, Any],
    requested_task: str,
    algorithm: Optional[str] = None,
    algorithm_map: Optional[Dict[str, Any]] = None,
) -> None:
    """Validate target type vs requested task type vs algorithm.

    Raises HTTPException(422) on configuration mismatch instead of allowing 500 errors.
    """
    target_type = target_info["target_type"]
    target_col = target_info["target_column"]
    suggested_task = target_info["task_suggestion"]
    classes = target_info["classes"]

    # 1. Target Type vs Requested Task Type
    if target_type == "categorical" and requested_task == "regression":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "TASK_DATA_MISMATCH",
                "message": f"The selected Regression task is incompatible with the categorical dataset target '{target_col}'.",
                "details": {
                    "target_column": target_col,
                    "target_type": target_type,
                    "detected_classes": classes,
                    "suggested_task": suggested_task,
                },
            },
        )

    if target_type == "boolean" and requested_task == "regression":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "TASK_DATA_MISMATCH",
                "message": f"The selected Regression task is incompatible with the boolean dataset target '{target_col}'.",
                "details": {
                    "target_column": target_col,
                    "target_type": target_type,
                    "detected_classes": classes,
                    "suggested_task": suggested_task,
                },
            },
        )

    if target_type == "numeric continuous" and requested_task == "classification":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "TASK_DATA_MISMATCH",
                "message": f"The selected Classification task is incompatible with continuous numeric target '{target_col}'.",
                "details": {
                    "target_column": target_col,
                    "target_type": target_type,
                    "suggested_task": suggested_task,
                },
            },
        )

    if target_type in ("datetime", "unsupported"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "UNSUPPORTED_TARGET_TYPE",
                "message": f"Target column '{target_col}' has unsupported type '{target_type}'.",
                "details": {
                    "target_column": target_col,
                    "target_type": target_type,
                },
            },
        )

    # 2. Algorithm vs Requested Task Type
    if algorithm and algorithm_map:
        algo_info = algorithm_map.get(algorithm)
        if not algo_info:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": "UNKNOWN_ALGORITHM",
                    "message": f"Unknown algorithm '{algorithm}'.",
                    "details": {"algorithm": algorithm, "available": list(algorithm_map.keys())},
                },
            )

        if not algo_info.get(requested_task):
            supported_tasks = [t for t, dot in algo_info.items() if dot]
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": "ALGORITHM_TASK_MISMATCH",
                    "message": f"Algorithm '{algorithm}' does not support task type '{requested_task}'.",
                    "details": {
                        "algorithm": algorithm,
                        "requested_task": requested_task,
                        "supported_tasks": supported_tasks,
                    },
                },
            )
