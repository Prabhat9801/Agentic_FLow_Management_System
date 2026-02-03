"""
FMS Agent - Agentic Flow Management System
Adapted from main_cli.py (v3.0) for FastAPI backend integration
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List
import re

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from openai import OpenAI

# Load environment
load_dotenv()

logger = logging.getLogger(__name__)

# Import schemas and functions from main_cli
import sys
sys.path.append(str(Path(__file__).parent))
import main_cli
from main_cli import (
    FlowSchema, FormulaPlan, ColumnInfo, SheetSchema, WorkflowStage, ColumnType,
    GoogleServicesManager, GoogleSheetsManager,
    JSONCleaner, ProjectManager, AgentState
)

class FMSAgent:
    """
    Production FMS Agent with real-time logging.
    Delegates core logic to main_cli.py to ensure consistency.
    """
    
    def __init__(
        self,
        prompt: str,
        model: str = "gpt-4o",
        temperature: float = 1.0,
        log_callback: Optional[Callable] = None
    ):
        self.prompt = prompt
        # We update the main_cli config if a specific model/temp is requested
        main_cli.Config.OPENAI_MODEL = model
        # Note: main_cli.py doesn't currently support passing temperature to LLMClient.invoke easily
        # but it reads it from environment if we added it there.
        
        self.log_callback = log_callback
        
        # State
        self.state = AgentState(prompt=prompt)
        
        logger.info(f"FMS Agent initialized: model={model}, temp={temperature}")
    
    async def log(self, level: str, stage: str, message: str, data: dict = None):
        """Log message and broadcast to WebSocket clients"""
        # Python logging
        log_func = getattr(logger, level.lower(), logger.info)
        log_func(f"[{stage}] {message}")
        
        # Broadcast to WebSocket
        if self.log_callback:
            await self.log_callback(level, stage, message, data)
    
    async def structure_agent(self) -> FlowSchema:
        """Delegate to main_cli.structure_agent"""
        await self.log("INFO", "structure", "🏗️ Structure Agent: Designing system with workflow stages")
        
        # Use main_cli's agent logic
        result = main_cli.structure_agent(self.state)
        
        if "errors" in result:
            error_msg = result["errors"][0]
            await self.log("ERROR", "structure", f"❌ Structure failed: {error_msg}")
            raise Exception(error_msg)
        
        self.state.flow = result["flow"]
        
        await self.log("INFO", "structure", f"✅ System structure created: {self.state.flow.system_name}", {
            "sheets_count": len(self.state.flow.sheets),
            "workflow_stages": self.state.flow.workflow_stages
        })
        
        return self.state.flow
    
    async def formula_agent(self) -> FormulaPlan:
        """Delegate to main_cli.formula_agent"""
        if not self.state.flow:
            raise ValueError("No flow structure available")
        
        await self.log("INFO", "formula", "⚙️ Formula Agent: Creating stage-based calculations")
        
        # Use main_cli's agent logic
        result = main_cli.formula_agent(self.state)
        
        if "errors" in result:
            error_msg = result["errors"][0]
            await self.log("ERROR", "formula", f"❌ Formula generation failed: {error_msg}")
            raise Exception(error_msg)
        
        self.state.formulas = result["formulas"]
        
        await self.log("INFO", "formula", f"✅ Formulas created: {len(self.state.formulas.formulas)} formulas")
        
        return self.state.formulas
    
    async def create_google_sheet(self) -> tuple:
        """Create Google Sheet with Stage Formatting using main_cli managers"""
        await self.log("INFO", "sheets", "📊 Creating Google Spreadsheet with Stage Formatting...")
        
        # Authenticate using main_cli managers
        google_manager = GoogleServicesManager()
        drive, sheets = google_manager.authenticate()
        
        sheets_manager = GoogleSheetsManager(drive, sheets)
        
        # Create spreadsheet
        spreadsheet_id = sheets_manager.create_spreadsheet(self.state.flow.system_name)
        
        await self.log("INFO", "sheets", f"Spreadsheet created: {spreadsheet_id}")
        
        # Setup sheets with stage formatting
        sheets_manager.setup_sheets(spreadsheet_id, self.state.flow)
        
        # Apply formulas
        sheets_manager.apply_formulas(spreadsheet_id, self.state.flow, self.state.formulas)
        
        await self.log("INFO", "sheets", "✅ Google Sheet ready with workflow stages!")
        
        return spreadsheet_id, sheets_manager
    
    async def execute(self) -> Dict[str, Any]:
        """Execute complete FMS workflow"""
        start_time = datetime.now()
        
        try:
            # Create project folder (using main_cli's ProjectManager)
            self.state.project_folder = ProjectManager.create_project_folder(self.prompt)
            await self.log("INFO", "setup", f"Project folder: {self.state.project_folder.name}")
            
            # Phase 1: Structure
            await self.structure_agent()
            
            # Phase 2: Formulas
            await self.formula_agent()
            
            # Phase 3: Google Sheets
            spreadsheet_id, _ = await self.create_google_sheet()
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Save metadata (using main_cli's ProjectManager)
            metadata = ProjectManager.save_metadata(
                self.state.project_folder,
                self.prompt,
                spreadsheet_id,
                self.state.flow,
                execution_time
            )
            
            await self.log("INFO", "complete", "🎉 Workflow creation complete!", {
                "execution_time": execution_time,
                "spreadsheet_id": spreadsheet_id
            })
            
            return {
                "success": True,
                "project_id": self.state.project_folder.name,
                "project_folder": str(self.state.project_folder),
                "spreadsheet_id": spreadsheet_id,
                "spreadsheet_url": f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}",
                "sheets_count": len(self.state.flow.sheets),
                "formulas_count": len(self.state.formulas.formulas),
                "execution_time": execution_time
            }
            
        except Exception as e:
            await self.log("ERROR", "error", f"❌ Workflow failed: {str(e)}")
            raise