"""Serial port management API."""
import asyncio
import json
from typing import Optional
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

router = APIRouter()

# Global serial connection state
_serial_connections = {}


class SerialConfig(BaseModel):
    port: str
    baud_rate: int = 115200
    timeout: float = 1.0


@router.get("/ports")
async def list_ports():
    """Enumerate available serial ports."""
    try:
        import serial.tools.list_ports
        ports = []
        for p in serial.tools.list_ports.comports():
            ports.append({
                "device": p.device,
                "name": p.name,
                "description": p.description,
                "hwid": p.hwid,
                "manufacturer": p.manufacturer,
                "product": p.product,
                "serial_number": p.serial_number,
                "vid": f"0x{p.vid:04x}" if p.vid else None,
                "pid": f"0x{p.pid:04x}" if p.pid else None,
            })
        return {"ports": ports}
    except ImportError:
        return {"ports": [], "error": "pyserial not installed. Install with: pip install pyserial"}


@router.post("/connect")
async def connect(config: SerialConfig):
    """Connect to a serial port."""
    try:
        import serial
    except ImportError:
        raise HTTPException(500, "pyserial not installed")

    if config.port in _serial_connections:
        raise HTTPException(409, f"Already connected to {config.port}")

    try:
        ser = serial.Serial(
            port=config.port,
            baudrate=config.baud_rate,
            timeout=config.timeout,
        )
        _serial_connections[config.port] = {
            "serial": ser,
            "config": config.model_dump(),
            "rx_bytes": 0,
            "packets": 0,
        }
        return {
            "connected": True,
            "port": config.port,
            "baud_rate": config.baud_rate,
        }
    except Exception as e:
        raise HTTPException(400, f"Failed to connect: {str(e)}")


@router.post("/disconnect")
async def disconnect(port: str):
    """Disconnect from a serial port."""
    if port not in _serial_connections:
        raise HTTPException(404, f"Not connected to {port}")

    conn = _serial_connections.pop(port)
    try:
        conn["serial"].close()
    except Exception:
        pass

    return {"disconnected": True, "port": port}


@router.get("/status")
async def serial_status():
    """Get status of all serial connections."""
    statuses = {}
    for port, conn in _serial_connections.items():
        ser = conn["serial"]
        statuses[port] = {
            "connected": ser.is_open,
            "port": port,
            "baud_rate": conn["config"]["baud_rate"],
            "rx_bytes": conn["rx_bytes"],
            "packets": conn["packets"],
        }
    return statuses


@router.websocket("/monitor/{port_name}")
async def serial_monitor(websocket: WebSocket, port_name: str):
    """WebSocket endpoint for real-time serial data monitoring."""
    await websocket.accept()

    # URL-decode port name
    import urllib.parse
    port = urllib.parse.unquote(port_name)

    if port not in _serial_connections:
        await websocket.send_json({"error": f"Not connected to {port}"})
        await websocket.close()
        return

    conn = _serial_connections[port]
    ser = conn["serial"]

    try:
        while True:
            if ser.in_waiting:
                data = ser.readline()
                if data:
                    conn["rx_bytes"] += len(data)
                    conn["packets"] += 1
                    try:
                        text = data.decode("utf-8").strip()
                        await websocket.send_json({
                            "type": "data",
                            "data": text,
                            "bytes": len(data),
                            "packet": conn["packets"],
                        })
                    except UnicodeDecodeError:
                        await websocket.send_json({
                            "type": "binary",
                            "bytes": len(data),
                            "hex": data.hex(),
                        })
            else:
                await asyncio.sleep(0.01)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"error": str(e)})
        except Exception:
            pass
