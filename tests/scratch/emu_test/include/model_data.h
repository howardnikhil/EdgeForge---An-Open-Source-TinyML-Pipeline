#ifndef MODEL_DATA_H
#define MODEL_DATA_H

#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define EDGEFORGE_NUM_FEATURES 2
#define EDGEFORGE_NUM_CLASSES 2

static const char* CLASS_LABELS[] = { "class_0", "class_1" };

// Auto-generated C Random Forest Inference Engine
#define NUM_ESTIMATORS 3
#define NUM_FEATURES 2
#define NUM_CLASSES 2

static inline void evaluate_forest_tree_0(const float* features, float* probs) {
  if (features[1] <= 1.400000f) {
    probs[0] += 1.000000f;
    probs[1] += 0.000000f;
    return;
  } else {
    probs[0] += 0.000000f;
    probs[1] += 1.000000f;
    return;
  }
}

static inline void evaluate_forest_tree_1(const float* features, float* probs) {
  probs[0] += 0.000000f;
  probs[1] += 1.000000f;
  return;
}

static inline void evaluate_forest_tree_2(const float* features, float* probs) {
  if (features[0] <= 0.800000f) {
    probs[0] += 1.000000f;
    probs[1] += 0.000000f;
    return;
  } else {
    probs[0] += 0.000000f;
    probs[1] += 1.000000f;
    return;
  }
}

static inline int predict_sample(const float* features, float* probabilities) {
  for (int i = 0; i < 2; i++) probabilities[i] = 0.0f;
  float tree_probs[NUM_CLASSES];
  for (int i = 0; i < NUM_CLASSES; i++) tree_probs[i] = 0.0f;
  evaluate_forest_tree_0(features, tree_probs);
  for (int i = 0; i < NUM_CLASSES; i++) probabilities[i] += tree_probs[i];
  for (int i = 0; i < NUM_CLASSES; i++) tree_probs[i] = 0.0f;
  evaluate_forest_tree_1(features, tree_probs);
  for (int i = 0; i < NUM_CLASSES; i++) probabilities[i] += tree_probs[i];
  for (int i = 0; i < NUM_CLASSES; i++) tree_probs[i] = 0.0f;
  evaluate_forest_tree_2(features, tree_probs);
  for (int i = 0; i < NUM_CLASSES; i++) probabilities[i] += tree_probs[i];
  int best_class = 0;
  float max_prob = -1.0f;
  for (int i = 0; i < 2; i++) {
    probabilities[i] /= (float)3;
    if (probabilities[i] > max_prob) {
      max_prob = probabilities[i];
      best_class = i;
    }
  }
  return best_class;
}


#endif // MODEL_DATA_H
