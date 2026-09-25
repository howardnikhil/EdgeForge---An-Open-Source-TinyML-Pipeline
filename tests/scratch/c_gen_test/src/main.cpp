// EdgeForge MCU Firmware Entry Point
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

void process_sample_line(const char* line) {
    int sample_idx = 0;
    float features[EDGEFORGE_NUM_FEATURES];
    memset(features, 0, sizeof(features));
    
    const char* p = line;
    if (strncmp(p, "SAMPLE ", 7) == 0) {
        p += 7;
        sample_idx = atoi(p);
        const char* colon = strchr(p, ':');
        if (colon) p = colon + 1;
    }
    
    int feat_count = 0;
    char buffer[256];
    strncpy(buffer, p, sizeof(buffer) - 1);
    buffer[sizeof(buffer) - 1] = '\0';
    
    char* token = strtok(buffer, ", \t\r\n");
    while (token && feat_count < EDGEFORGE_NUM_FEATURES) {
        features[feat_count++] = atof(token);
        token = strtok(NULL, ", \t\r\n");
    }
    
    float probs[EDGEFORGE_NUM_CLASSES];
    for (int i = 0; i < EDGEFORGE_NUM_CLASSES; i++) probs[i] = 0.0f;
    
    #if IS_ARDUINO
    unsigned long start_time = micros();
    int pred_class = predict_sample(features, probs);
    unsigned long elapsed_us = micros() - start_time;
    uint32_t free_heap = ESP.getFreeHeap();
    printf("[TELEMETRY] INDEX:%d, PRED:%d, CONF:%.6f, TIME_US:%lu, HEAP_FREE:%u\n",
           sample_idx, pred_class, probs[pred_class], elapsed_us, (unsigned int)free_heap);
    #else
    struct timespec ts_start, ts_end;
    clock_gettime(CLOCK_MONOTONIC, &ts_start);
    int pred_class = predict_sample(features, probs);
    clock_gettime(CLOCK_MONOTONIC, &ts_end);
    
    long elapsed_us = (ts_end.tv_sec - ts_start.tv_sec) * 1000000L + (ts_end.tv_nsec - ts_start.tv_nsec) / 1000L;
    printf("[TELEMETRY] INDEX:%d, PRED:%d, CONF:%.6f, TIME_US:%ld, HEAP_FREE:262144\n",
           sample_idx, pred_class, probs[pred_class], elapsed_us);
    fflush(stdout);
    #endif
}

#if IS_ARDUINO
void setup() {
    Serial.begin(115200);
    delay(500);
    printf("[BOOT] EdgeForge MCU Firmware Started. Targets: %d features, %d classes\n", EDGEFORGE_NUM_FEATURES, EDGEFORGE_NUM_CLASSES);
}

void loop() {
    if (Serial.available()) {
        String line = Serial.readStringUntil('\n');
        line.trim();
        if (line.length() > 0) {
            process_sample_line(line.c_str());
        }
    }
}
#else
int main(int argc, char** argv) {
    printf("[BOOT] EdgeForge MCU Firmware Started (Native Emulation). Features: %d, Classes: %d\n", EDGEFORGE_NUM_FEATURES, EDGEFORGE_NUM_CLASSES);
    fflush(stdout);
    
    char line[1024];
    while (fgets(line, sizeof(line), stdin)) {
        size_t len = strlen(line);
        while (len > 0 && (line[len-1] == '\r' || line[len-1] == '\n')) {
            line[--len] = '\0';
        }
        if (len > 0) {
            process_sample_line(line);
        }
    }
    return 0;
}
#endif
