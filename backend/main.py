"""
FMS Backend - FastAPI Application
Production-ready Flow Management System with real-time agent logs
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Import the FMS agent logic
import sys
sys.path.append(str(Path(__file__).parent))
from fms_agent import FMSAgent, AgentState

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
# Fix Windows encoding for emojis
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

logger = logging.getLogger(__name__)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")

manager = ConnectionManager()

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 FMS Backend starting up...")
    
    # Ensure directories exist
    Path("projects").mkdir(exist_ok=True)
    
    logger.info("✅ FMS Backend ready!")
    
    yield
    
    # Shutdown
    logger.info("👋 FMS Backend shutting down...")

# FastAPI app
app = FastAPI(
    title="Flow Management System API",
    description="Production-ready agentic FMS with real-time logs",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request models
class WorkflowRequest(BaseModel):
    prompt: str
    model: Optional[str] = "gpt-4o"
    temperature: Optional[float] = 1.0

class WorkflowResponse(BaseModel):
    success: bool
    message: str
    project_id: Optional[str] = None
    project_folder: Optional[str] = None
    spreadsheet_url: Optional[str] = None
    spreadsheet_id: Optional[str] = None
    execution_time: Optional[float] = None
    sheets_count: Optional[int] = None
    formulas_count: Optional[int] = None

# Health check
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "FMS Backend",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat()
    }

# WebSocket endpoint for real-time logs
@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# Create workflow endpoint
@app.post("/api/workflow/create", response_model=WorkflowResponse)
async def create_workflow(request: WorkflowRequest):
    """
    Create a new workflow using the FMS agent
    Streams real-time logs to connected WebSocket clients
    """
    try:
        start_time = datetime.now()
        
        # Log start
        await manager.broadcast({
            "type": "log",
            "level": "info",
            "stage": "init",
            "message": f"🚀 Starting workflow creation: {request.prompt}",
            "timestamp": datetime.now().isoformat()
        })
        
        # Create FMS agent with WebSocket log callback
        async def log_callback(level: str, stage: str, message: str, data: dict = None):
            """Callback to broadcast logs to WebSocket clients"""
            await manager.broadcast({
                "type": "log",
                "level": level,
                "stage": stage,
                "message": message,
                "data": data,
                "timestamp": datetime.now().isoformat()
            })
        
        # Initialize agent
        agent = FMSAgent(
            prompt=request.prompt,
            model=request.model,
            temperature=request.temperature,
            log_callback=log_callback
        )
        
        # Execute workflow
        result = await agent.execute()
        
        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Broadcast completion
        await manager.broadcast({
            "type": "complete",
            "message": "✅ Workflow created successfully!",
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
        
        return WorkflowResponse(
            success=True,
            message="Workflow created successfully",
            project_id=result.get("project_id"),
            project_folder=result.get("project_folder"),
            spreadsheet_url=result.get("spreadsheet_url"),
            spreadsheet_id=result.get("spreadsheet_id"),
            execution_time=execution_time,
            sheets_count=result.get("sheets_count"),
            formulas_count=result.get("formulas_count")
        )
        
    except Exception as e:
        logger.error(f"Workflow creation failed: {e}", exc_info=True)
        
        # Broadcast error
        await manager.broadcast({
            "type": "error",
            "message": f"❌ Error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        })
        
        raise HTTPException(status_code=500, detail=str(e))

# List projects
@app.get("/api/projects")
async def list_projects():
    """List all created projects"""
    try:
        projects_dir = Path("projects")
        if not projects_dir.exists():
            return {"projects": []}
        
        projects = []
        for project_folder in sorted(projects_dir.iterdir(), reverse=True):
            if project_folder.is_dir():
                metadata_file = project_folder / "metadata.json"
                if metadata_file.exists():
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                        projects.append({
                            "folder": project_folder.name,
                            "metadata": metadata
                        })
        
        return {"projects": projects, "count": len(projects)}
    
    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Get project details
@app.get("/api/projects/{project_id}")
async def get_project(project_id: str):
    """Get details of a specific project"""
    try:
        project_folder = Path("projects") / project_id
        
        if not project_folder.exists():
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Load all project files
        metadata_file = project_folder / "metadata.json"
        flow_file = project_folder / "schemas" / "flow_structure.json"
        formula_file = project_folder / "schemas" / "formula_plan.json"
        readme_file = project_folder / "README.md"
        
        result = {"project_id": project_id}
        
        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                result["metadata"] = json.load(f)
        
        if flow_file.exists():
            with open(flow_file, 'r', encoding='utf-8') as f:
                result["flow_structure"] = json.load(f)
        
        if formula_file.exists():
            with open(formula_file, 'r', encoding='utf-8') as f:
                result["formula_plan"] = json.load(f)
        
        if readme_file.exists():
            result["readme"] = readme_file.read_text(encoding='utf-8')
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Delete project
@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete a project"""
    try:
        project_folder = Path("projects") / project_id
        
        if not project_folder.exists():
            raise HTTPException(status_code=404, detail="Project not found")
        
        import shutil
        shutil.rmtree(project_folder)
        
        return {"success": True, "message": f"Project {project_id} deleted"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting project: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Mount frontend (add this at the very end)
# Serve frontend static files
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
    logger.info(f"✅ Frontend mounted from: {frontend_path}")
else:
    logger.warning("⚠️ Frontend directory not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disabled to prevent constant reloading from log files
        log_level="info"
    )
