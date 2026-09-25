"""Real Firmware Compiler Service for EdgeForge."""
import os
import sys
import time
import subprocess
import shutil
import re


def compile_firmware(firmware_dir: str, env_name: str = None) -> dict:
    """Run real compilation using PlatformIO or gcc fallback."""
    if not os.path.exists(firmware_dir):
        return {
            "success": False,
            "error": f"Firmware directory does not exist: {firmware_dir}",
            "build_duration_s": 0.0,
        }

    log_path = os.path.join(firmware_dir, "build.log")
    start_time = time.time()
    
    pio_executable = shutil.which("pio") or shutil.which("platformio")
    output_log = []
    success = False
    elf_path = None
    bin_path = None
    flash_bytes = 0
    ram_bytes = 0

    if pio_executable:
        cmd = [pio_executable, "run", "-d", firmware_dir]
        if env_name:
            cmd.extend(["-e", env_name])
            
        output_log.append(f"Executing: {' '.join(cmd)}\n")
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=120)
            output_log.append(res.stdout)
            success = (res.returncode == 0)
            
            ram_match = re.search(r"RAM:\s+\[.*?\].*?used\s+(\d+)\s+bytes", res.stdout)
            if ram_match:
                ram_bytes = int(ram_match.group(1))
                
            flash_match = re.search(r"Flash:\s+\[.*?\].*?used\s+(\d+)\s+bytes", res.stdout)
            if flash_match:
                flash_bytes = int(flash_match.group(1))

            for root, _, files in os.walk(os.path.join(firmware_dir, ".pio", "build")):
                for f in files:
                    if f.endswith(".elf") or f == "firmware.bin" or f == "program":
                        target_path = os.path.join(root, f)
                        if f.endswith(".elf"):
                            elf_path = target_path
                        elif not bin_path:
                            bin_path = target_path
            if not elf_path:
                elf_path = bin_path
                            
        except Exception as e:
            output_log.append(f"\n[COMPILATION ERROR] Exception during build: {str(e)}\n")
            success = False
    else:
        gcc_bin = shutil.which("g++") or shutil.which("gcc")
        if not gcc_bin:
            return {
                "success": False,
                "error": "Neither PlatformIO nor GCC compiler was found on system.",
                "build_duration_s": 0.0,
            }
        
        src_cpp = os.path.join(firmware_dir, "src", "main.cpp")
        out_binary = os.path.join(firmware_dir, "firmware.elf")
        include_dir = os.path.join(firmware_dir, "include")
        
        cmd = [gcc_bin, "-O2", f"-I{include_dir}", src_cpp, "-o", out_binary]
        output_log.append(f"Executing GCC Fallback: {' '.join(cmd)}\n")
        
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=60)
            output_log.append(res.stdout)
            success = (res.returncode == 0 and os.path.exists(out_binary))
            if success:
                elf_path = out_binary
                bin_path = out_binary
                flash_bytes = os.path.getsize(out_binary)
                ram_bytes = 16384
        except Exception as e:
            output_log.append(f"\n[GCC COMPILATION ERROR] {str(e)}\n")
            success = False

    end_time = time.time()
    duration = round(end_time - start_time, 2)
    
    full_log_str = "\n".join(output_log)
    with open(log_path, "w") as f:
        f.write(full_log_str)
        
    return {
        "success": success,
        "build_duration_s": duration,
        "log_path": log_path,
        "elf_path": elf_path,
        "bin_path": bin_path,
        "flash_bytes": flash_bytes,
        "ram_bytes": ram_bytes,
        "compiler_output": full_log_str[-2000:] if full_log_str else "",
    }
