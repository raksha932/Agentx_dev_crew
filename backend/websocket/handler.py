import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from websocket.manager import websocket_manager

router = APIRouter()


@router.websocket("/ws/runs/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str):
    """WebSocket endpoint for real-time run updates."""
    await websocket_manager.connect(websocket, run_id)

    try:
        await websocket.send_json({
            "type": "connected",
            "run_id": run_id,
            "message": f"Connected to run {run_id}",
        })

        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)

                try:
                    message = json.loads(data)

                    if message.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                    elif message.get("type") == "get_status":
                        await websocket.send_json({
                            "type": "status",
                            "connection_count": websocket_manager.get_connection_count(run_id),
                        })

                except json.JSONDecodeError:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Invalid JSON",
                    })

            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})

    except WebSocketDisconnect:
        await websocket_manager.disconnect(websocket, run_id)

    except Exception as e:
        print(f"WebSocket error: {e}")
        await websocket_manager.disconnect(websocket, run_id)
