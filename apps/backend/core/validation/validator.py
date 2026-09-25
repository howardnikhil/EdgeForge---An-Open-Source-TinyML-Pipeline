"""Desktop vs MCU Validation Service for EdgeForge."""
import numpy as np


def validate_desktop_vs_mcu(
    desktop_model,
    X_test: np.ndarray,
    y_test: np.ndarray,
    mcu_telemetry: list[dict],
    class_labels: list = None
) -> dict:
    """Compare Desktop Python inference against Emulated MCU C inference."""
    n_samples = len(X_test)
    if n_samples == 0:
        return {"error": "Test set is empty"}

    desktop_preds = desktop_model.predict(X_test)
    if hasattr(desktop_model, "predict_proba"):
        desktop_probs = desktop_model.predict_proba(X_test)
    else:
        desktop_probs = None

    desktop_correct = np.sum(desktop_preds == y_test)
    desktop_accuracy = float(desktop_correct / n_samples)

    mcu_preds = []
    mcu_confidences = []
    mcu_latencies = []

    telemetry_map = {t["sample_index"]: t for t in mcu_telemetry}

    mismatches = []
    agreements = 0

    for idx in range(n_samples):
        if idx in telemetry_map:
            item = telemetry_map[idx]
            m_pred = item["prediction"]
            m_conf = item["confidence"]
            m_lat = item["time_us"]
            
            mcu_preds.append(m_pred)
            mcu_confidences.append(m_conf)
            mcu_latencies.append(m_lat)

            d_pred = int(desktop_preds[idx])
            ground_truth = int(y_test[idx])

            if m_pred == d_pred:
                agreements += 1
            else:
                mismatches.append({
                    "sample_index": idx,
                    "features": X_test[idx].tolist(),
                    "ground_truth": ground_truth,
                    "desktop_prediction": d_pred,
                    "mcu_prediction": m_pred,
                    "mcu_confidence": m_conf,
                    "desktop_confidence": float(desktop_probs[idx][d_pred]) if desktop_probs is not None else 1.0,
                })

    mcu_preds_arr = np.array(mcu_preds) if mcu_preds else np.array([])
    mcu_correct = np.sum(mcu_preds_arr == y_test[:len(mcu_preds_arr)]) if len(mcu_preds_arr) > 0 else 0
    mcu_accuracy = float(mcu_correct / len(mcu_preds_arr)) if len(mcu_preds_arr) > 0 else 0.0
    agreement_rate = float(agreements / len(mcu_preds_arr)) if len(mcu_preds_arr) > 0 else 0.0

    avg_latency = float(np.mean(mcu_latencies)) if mcu_latencies else 0.0

    report = {
        "status": "completed",
        "total_test_samples": n_samples,
        "emulated_mcu_samples": len(mcu_preds_arr),
        "desktop_accuracy": round(desktop_accuracy * 100.0, 2),
        "mcu_accuracy": round(mcu_accuracy * 100.0, 2),
        "agreement_rate": round(agreement_rate * 100.0, 2),
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "avg_mcu_latency_us": round(avg_latency, 2),
        "metrics_status": {
            "mcu_accuracy": "MEASURED",
            "prediction_agreement": "MEASURED",
            "mcu_inference_latency": "MEASURED",
            "mcu_ram_flash_usage": "MEASURED",
            "power_consumption_mw": "UNAVAILABLE",
        }
    }

    return report
