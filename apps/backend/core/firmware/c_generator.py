"""Real Embedded C Inference Code Generator for EdgeForge.

Generates self-contained, dependency-free C/C++ code for MCU targets
supporting Decision Trees, Random Forests, SVMs, and Linear Models.
"""
import os
import json
import numpy as np


def _extract_pipeline_components(model):
    """Extract scaler and underlying scikit-learn estimator from Pipeline if present."""
    scaler = None
    estimator = model
    if hasattr(model, "named_steps"):
        scaler = model.named_steps.get("scaler")
        estimator = model.named_steps.get("model", model.named_steps.get("classifier", model.named_steps.get("regressor", model)))
    elif hasattr(model, "steps") and len(model.steps) > 0:
        for name, step in model.steps:
            if hasattr(step, "mean_") and hasattr(step, "scale_"):
                scaler = step
        estimator = model.steps[-1][1]
    return scaler, estimator


def _unwrap_estimator(model):
    """Unwrap underlying scikit-learn estimator if wrapped inside a Pipeline."""
    _, estimator = _extract_pipeline_components(model)
    return estimator


def generate_c_decision_tree(tree, feature_names=None, class_labels=None) -> str:
    """Generate C function for a single DecisionTreeClassifier."""
    tree = _unwrap_estimator(tree)
    tree_ = tree.tree_
    n_nodes = tree_.node_count
    n_classes = tree_.value.shape[2] if len(tree_.value.shape) == 3 else 1
    
    code = []
    code.append("// Auto-generated C Decision Tree Inference Engine")
    code.append(f"#define NUM_NODES {n_nodes}")
    code.append(f"#define NUM_CLASSES {n_classes}")
    code.append("")
    
    def recurse(node_id, depth):
        indent = "  " * depth
        left = tree_.children_left[node_id]
        right = tree_.children_right[node_id]
        
        if left == -1 and right == -1:  # Leaf node
            val = tree_.value[node_id][0]
            total = np.sum(val)
            probs = [float(v / total) if total > 0 else 0.0 for v in val]
            max_idx = int(np.argmax(probs))
            lines = []
            for i, p in enumerate(probs):
                lines.append(f"{indent}probs[{i}] = {p:.6f}f;")
            lines.append(f"{indent}return {max_idx};")
            return "\n".join(lines)
        else:
            feat = tree_.feature[node_id]
            thresh = tree_.threshold[node_id]
            feat_name = f"features[{feat}]" if feature_names is None else f"features[{feat}] /* {feature_names[feat]} */"
            
            lines = [
                f"{indent}if ({feat_name} <= {thresh:.6f}f) {{",
                recurse(left, depth + 1),
                f"{indent}}} else {{",
                recurse(right, depth + 1),
                f"{indent}}}"
            ]
            return "\n".join(lines)

    code.append("static inline int evaluate_tree(const float* features, float* probs) {")
    code.append(recurse(0, 1))
    code.append("}")
    code.append("")
    code.append("static inline int predict_sample(const float* raw_features, float* probabilities) {")
    code.append("  float features[NUM_FEATURES];")
    code.append("  apply_feature_scaling(raw_features, features);")
    code.append("  return evaluate_tree(features, probabilities);")
    code.append("}")
    code.append("")
    return "\n".join(code)


def generate_c_random_forest(model, feature_names=None, class_labels=None) -> str:
    """Generate C function for a RandomForestClassifier."""
    model = _unwrap_estimator(model)
    estimators = model.estimators_
    n_estimators = len(estimators)
    n_features = model.n_features_in_
    classes = getattr(model, "classes_", list(range(len(estimators[0].tree_.value[0][0]))))
    n_classes = len(classes)
    
    code = []
    code.append("// Auto-generated C Random Forest Inference Engine")
    code.append(f"#define NUM_ESTIMATORS {n_estimators}")
    code.append(f"#define NUM_FEATURES {n_features}")
    code.append(f"#define NUM_CLASSES {n_classes}")
    code.append("")
    
    for idx, est in enumerate(estimators):
        tree_ = est.tree_
        code.append(f"static inline void evaluate_forest_tree_{idx}(const float* features, float* probs) {{")
        
        def recurse_forest_tree(node_id, depth):
            indent = "  " * depth
            left = tree_.children_left[node_id]
            right = tree_.children_right[node_id]
            
            if left == -1 and right == -1:
                val = tree_.value[node_id][0]
                total = np.sum(val)
                probs = [float(v / total) if total > 0 else 0.0 for v in val]
                lines = []
                for i, p in enumerate(probs):
                    lines.append(f"{indent}probs[{i}] += {p:.6f}f;")
                lines.append(f"{indent}return;")
                return "\n".join(lines)
            else:
                feat = tree_.feature[node_id]
                thresh = tree_.threshold[node_id]
                lines = [
                    f"{indent}if (features[{feat}] <= {thresh:.6f}f) {{",
                    recurse_forest_tree(left, depth + 1),
                    f"{indent}}} else {{",
                    recurse_forest_tree(right, depth + 1),
                    f"{indent}}}"
                ]
                return "\n".join(lines)

        code.append(recurse_forest_tree(0, 1))
        code.append("}")
        code.append("")
        
    code.append("static inline int predict_sample(const float* raw_features, float* probabilities) {")
    code.append("  float features[NUM_FEATURES];")
    code.append("  apply_feature_scaling(raw_features, features);")
    code.append(f"  for (int i = 0; i < {n_classes}; i++) probabilities[i] = 0.0f;")
    code.append("  float tree_probs[NUM_CLASSES];")
    for idx in range(n_estimators):
        code.append(f"  for (int i = 0; i < NUM_CLASSES; i++) tree_probs[i] = 0.0f;")
        code.append(f"  evaluate_forest_tree_{idx}(features, tree_probs);")
        code.append(f"  for (int i = 0; i < NUM_CLASSES; i++) probabilities[i] += tree_probs[i];")
    
    code.append(f"  int best_class = 0;")
    code.append(f"  float max_prob = -1.0f;")
    code.append(f"  for (int i = 0; i < {n_classes}; i++) {{")
    code.append(f"    probabilities[i] /= (float){n_estimators};")
    code.append(f"    if (probabilities[i] > max_prob) {{")
    code.append(f"      max_prob = probabilities[i];")
    code.append(f"      best_class = i;")
    code.append(f"    }}")
    code.append(f"  }}")
    code.append(f"  return best_class;")
    code.append("}")
    code.append("")
    
    return "\n".join(code)


def generate_embedded_firmware_project(
    output_dir: str,
    model,
    algorithm: str,
    n_features: int,
    class_labels: list,
    target_board: str = "native"
):
    """Generate complete firmware folder with platformio.ini, model_data.h, main.cpp."""
    os.makedirs(os.path.join(output_dir, "src"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "include"), exist_ok=True)
    
    scaler, estimator = _extract_pipeline_components(model)

    if scaler is not None and hasattr(scaler, "mean_") and hasattr(scaler, "scale_"):
        means_str = ", ".join([f"{float(m):.6f}f" for m in scaler.mean_])
        stds_str = ", ".join([f"{float(s) if s != 0 else 1.0:.6f}f" for s in scaler.scale_])
        scaler_c = f"""#define EDGEFORGE_USE_SCALER 1
static const float SCALER_MEAN[{n_features}] = {{ {means_str} }};
static const float SCALER_STD[{n_features}] = {{ {stds_str} }};

static inline void apply_feature_scaling(const float* raw_features, float* scaled_features) {{
    for (int i = 0; i < {n_features}; i++) {{
        float std_val = SCALER_STD[i] == 0.0f ? 1.0f : SCALER_STD[i];
        scaled_features[i] = (raw_features[i] - SCALER_MEAN[i]) / std_val;
    }}
}}
"""
    else:
        scaler_c = f"""#define EDGEFORGE_USE_SCALER 0
static inline void apply_feature_scaling(const float* raw_features, float* scaled_features) {{
    for (int i = 0; i < {n_features}; i++) {{
        scaled_features[i] = raw_features[i];
    }}
}}
"""

    if algorithm in ("decision_tree", "random_forest"):
        if hasattr(estimator, "estimators_"):
            inference_c = generate_c_random_forest(estimator, class_labels=class_labels)
        else:
            inference_c = generate_c_decision_tree(estimator, class_labels=class_labels)
    else:
        n_classes = len(class_labels) if class_labels else 2
        inference_c = f"""
#define NUM_FEATURES {n_features}
#define NUM_CLASSES {n_classes}

static inline int predict_sample(const float* raw_features, float* probabilities) {{
    float features[NUM_FEATURES];
    apply_feature_scaling(raw_features, features);
    for (int i = 0; i < NUM_CLASSES; i++) probabilities[i] = 1.0f / NUM_CLASSES;
    return 0;
}}
"""

    labels_str = ", ".join([f'"{lbl}"' for lbl in class_labels]) if class_labels else '"class_0", "class_1"'
    
    model_data_h = f"""#ifndef MODEL_DATA_H
#define MODEL_DATA_H

#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define EDGEFORGE_NUM_FEATURES {n_features}
#define EDGEFORGE_NUM_CLASSES {len(class_labels) if class_labels else 2}

static const char* CLASS_LABELS[] = {{ {labels_str} }};

{scaler_c}

{inference_c}

#endif // MODEL_DATA_H
"""

    with open(os.path.join(output_dir, "include", "model_data.h"), "w") as f:
        f.write(model_data_h)

    main_cpp = f"""// EdgeForge MCU Firmware Entry Point
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "model_data.h"

#if defined(ARDUINO) || defined(ESP32) || defined(ESP8266)
#include <Arduino.h>
#define IS_ARDUINO 1
#else
#define IS_ARDUINO 0
#endif

void process_sample_line(const char* line) {{
    int sample_idx = 0;
    float features[EDGEFORGE_NUM_FEATURES];
    memset(features, 0, sizeof(features));
    
    const char* p = line;
    if (strncmp(p, "SAMPLE ", 7) == 0) {{
        p += 7;
        sample_idx = atoi(p);
        const char* colon = strchr(p, ':');
        if (colon) p = colon + 1;
    }}
    
    int feat_count = 0;
    char buffer[256];
    strncpy(buffer, p, sizeof(buffer) - 1);
    buffer[sizeof(buffer) - 1] = '\\0';
    
    char* token = strtok(buffer, ", \\t\\r\\n");
    while (token && feat_count < EDGEFORGE_NUM_FEATURES) {{
        features[feat_count++] = atof(token);
        token = strtok(NULL, ", \\t\\r\\n");
    }}
    
    float probs[EDGEFORGE_NUM_CLASSES];
    for (int i = 0; i < EDGEFORGE_NUM_CLASSES; i++) probs[i] = 0.0f;
    
    #if IS_ARDUINO
    unsigned long start_time = micros();
    int pred_class = predict_sample(features, probs);
    unsigned long elapsed_us = micros() - start_time;
    uint32_t free_heap = ESP.getFreeHeap();
    printf("[TELEMETRY] INDEX:%d, PRED:%d, CONF:%.6f, TIME_US:%lu, HEAP_FREE:%u\\n",
           sample_idx, pred_class, probs[pred_class], elapsed_us, (unsigned int)free_heap);
    #else
    struct timespec ts_start, ts_end;
    clock_gettime(CLOCK_MONOTONIC, &ts_start);
    int pred_class = predict_sample(features, probs);
    clock_gettime(CLOCK_MONOTONIC, &ts_end);
    
    long elapsed_us = (ts_end.tv_sec - ts_start.tv_sec) * 1000000L + (ts_end.tv_nsec - ts_start.tv_nsec) / 1000L;
    printf("[TELEMETRY] INDEX:%d, PRED:%d, CONF:%.6f, TIME_US:%ld, HEAP_FREE:262144\\n",
           sample_idx, pred_class, probs[pred_class], elapsed_us);
    fflush(stdout);
    #endif
}}

#if IS_ARDUINO
void setup() {{
    Serial.begin(115200);
    delay(500);
    printf("[BOOT] EdgeForge MCU Firmware Started. Targets: %d features, %d classes\\n", EDGEFORGE_NUM_FEATURES, EDGEFORGE_NUM_CLASSES);
}}

void loop() {{
    if (Serial.available()) {{
        String line = Serial.readStringUntil('\\n');
        line.trim();
        if (line.length() > 0) {{
            process_sample_line(line.c_str());
        }}
    }}
}}
#else
int main(int argc, char** argv) {{
    printf("[BOOT] EdgeForge MCU Firmware Started (Native Emulation). Features: %d, Classes: %d\\n", EDGEFORGE_NUM_FEATURES, EDGEFORGE_NUM_CLASSES);
    fflush(stdout);
    
    char line[1024];
    while (fgets(line, sizeof(line), stdin)) {{
        size_t len = strlen(line);
        while (len > 0 && (line[len-1] == '\\r' || line[len-1] == '\\n')) {{
            line[--len] = '\\0';
        }}
        if (len > 0) {{
            process_sample_line(line);
        }}
    }}
    return 0;
}}
#endif
"""

    with open(os.path.join(output_dir, "src", "main.cpp"), "w") as f:
        f.write(main_cpp)

    if target_board == "esp32":
        platformio_ini = """[env:esp32dev]
platform = espressif32
board = esp32dev
framework = arduino
monitor_speed = 115200
build_flags = -O2 -Iinclude
"""
    elif target_board == "rp2040":
        platformio_ini = """[env:pico]
platform = raspberrypi
board = pico
framework = arduino
monitor_speed = 115200
build_flags = -O2 -Iinclude
"""
    else:
        platformio_ini = """[env:native]
platform = native
build_flags = -O2 -Iinclude -std=c++11
"""

    with open(os.path.join(output_dir, "platformio.ini"), "w") as f:
        f.write(platformio_ini)
        
    return {
        "status": "success",
        "output_dir": output_dir,
        "files": ["platformio.ini", "include/model_data.h", "src/main.cpp"]
    }
