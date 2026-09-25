"""Real MCU Firmware Emulation and Sensor Replay Engine for EdgeForge."""
import os
import sys
import time
import subprocess
import re
import json
import shutil
import numpy as np


class MCUEmulator:
    """Manages real MCU binary execution, sensor replay, and UART telemetry capture."""

    def __init__(self, binary_path: str, emulator_type: str = "native"):
        self.binary_path = binary_path
        self.emulator_type = emulator_type
        self.process = None

    def run_sensor_replay(self, samples: list[list[float]], timeout_s: float = 30.0) -> dict:
        """Replay sensor samples into the emulated MCU firmware and capture telemetry."""
        if not os.path.exists(self.binary_path):
            return {
                "success": False,
                "error": f"Firmware binary not found: {self.binary_path}",
                "telemetry": [],
            }

        replay_lines = []
        for idx, sample in enumerate(samples):
            feat_str = ",".join(f"{v:.6f}" for v in sample)
            replay_lines.append(f"SAMPLE {idx}:{feat_str}\n")
            
        input_data = "".join(replay_lines)
        start_time = time.time()
        
        if self.emulator_type == "renode" and shutil.which("renode"):
            cmd = ["renode", "--plain", "-e", f"mach create; sysbus LoadELF @{self.binary_path}; start"]
        elif self.emulator_type == "qemu" and shutil.which("qemu-system-arm"):
            cmd = ["qemu-system-arm", "-M", "microbit", "-kernel", self.binary_path, "-nographic"]
        else:
            cmd = [self.binary_path]

        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout_data, stderr_data = proc.communicate(input=input_data, timeout=timeout_s)
            exit_code = proc.returncode
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout_data, stderr_data = proc.communicate()
            return {
                "success": False,
                "error": "Emulation timed out",
                "telemetry": [],
                "raw_logs": stdout_data + "\n" + stderr_data,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Emulation execution failed: {str(e)}",
                "telemetry": [],
            }

        end_time = time.time()

        telemetry = []
        telemetry_pattern = re.compile(
            r"\[TELEMETRY\]\s+INDEX:(\d+),\s+PRED:(\d+),\s+CONF:([0-9.]+),\s+TIME_US:(\d+),\s+HEAP_FREE:(\d+)"
        )
        
        for line in stdout_data.splitlines():
            line_str = line.strip()
            match = telemetry_pattern.search(line_str)
            if match:
                telemetry.append({
                    "sample_index": int(match.group(1)),
                    "prediction": int(match.group(2)),
                    "confidence": float(match.group(3)),
                    "time_us": int(match.group(4)),
                    "heap_free_bytes": int(match.group(5)),
                })

        avg_latency = float(np.mean([t["time_us"] for t in telemetry])) if telemetry else 0.0
        
        return {
            "success": exit_code == 0 and len(telemetry) > 0,
            "emulator_used": self.emulator_type,
            "samples_processed": len(telemetry),
            "samples_total": len(samples),
            "avg_latency_us": round(avg_latency, 2),
            "telemetry": telemetry,
            "exit_code": exit_code,
            "duration_s": round(end_time - start_time, 2),
            "raw_logs": stdout_data,
            "stderr": stderr_data,
        }
