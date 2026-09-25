"""Hardware Compatibility Analysis Engine for EdgeForge."""

def analyze_hardware_compatibility(
    model_size_bytes: int,
    n_features: int,
    n_classes: int,
    algorithm: str,
    hardware_profile: dict
) -> dict:
    """Analyze detailed hardware memory footprint and operator compatibility."""
    board_name = hardware_profile.get("name", "Unknown MCU")
    flash_limit = hardware_profile.get("flash_bytes", 524288)
    ram_limit = hardware_profile.get("ram_bytes", 262144)
    
    firmware_sdk_base = 65536 if "esp32" in board_name.lower() else 16384
    c_runtime_code = 4096
    model_code = model_size_bytes
    total_flash_required = firmware_sdk_base + c_runtime_code + model_code
    
    stack_allocation = 8192
    heap_uart_buffer = 4096
    tensor_intermediate_ram = (n_features * 4) + (n_classes * 4) + (1024 if algorithm == "random_forest" else 256)
    total_ram_required = stack_allocation + heap_uart_buffer + tensor_intermediate_ram
    
    flash_compatible = total_flash_required <= flash_limit
    ram_compatible = total_ram_required <= ram_limit
    is_compatible = flash_compatible and ram_compatible
    
    remediations = []
    if not flash_compatible:
        exceeded = total_flash_required - flash_limit
        remediations.append(f"FLASH EXCEEDED by {exceeded // 1024} KB. Apply INT8 quantization or prune decision trees.")
    if not ram_compatible:
        exceeded = total_ram_required - ram_limit
        remediations.append(f"RAM EXCEEDED by {exceeded // 1024} KB. Reduce input window size or tree depth.")
        
    status_message = "Compatible with target MCU hardware constraints." if is_compatible else "Incompatible with target MCU. Exceeds hardware memory limits."

    return {
        "hardware_name": board_name,
        "compatible": is_compatible,
        "status_message": status_message,
        "breakdown": {
            "flash": {
                "required_bytes": total_flash_required,
                "available_bytes": flash_limit,
                "used_percentage": round((total_flash_required / flash_limit) * 100, 2),
                "sdk_base_bytes": firmware_sdk_base,
                "model_code_bytes": model_code,
                "runtime_code_bytes": c_runtime_code,
            },
            "ram": {
                "required_bytes": total_ram_required,
                "available_bytes": ram_limit,
                "used_percentage": round((total_ram_required / ram_limit) * 100, 2),
                "stack_bytes": stack_allocation,
                "heap_bytes": heap_uart_buffer,
                "tensor_arena_bytes": tensor_intermediate_ram,
            }
        },
        "remediations": remediations,
    }
