"""
FMS Agent - Agentic Flow Management System
Adapted from main_cli.py for FastAPI backend integration
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, Dict, Any
import re

from dotenv import load_dotenv
from pydantic import BaseModel
from openai import OpenAI

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Load environment
load_dotenv()

logger = logging.getLogger(__name__)

# Import schemas from main_cli
import sys
sys.path.append(str(Path(__file__).parent.parent))
from main_cli import (
    FlowSchema, FormulaPlan, ColumnInfo, SheetSchema,
    GoogleServicesManager, GoogleSheetsManager,
    JSONCleaner, ProjectManager, DocumentationGenerator
)

# Configuration
class Config:
    """Application configuration"""
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    TEMPERATURE = float(os.getenv("TEMPERATURE", "1.0"))
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    PROJECT_BASE_DIR = Path(os.getenv("PROJECT_BASE_DIR", "projects"))
    
    SCOPES = [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/spreadsheets"
    ]


class AgentState(BaseModel):
    prompt: str
    project_folder: Optional[Path] = None
    flow: Optional[FlowSchema] = None
    formulas: Optional[FormulaPlan] = None
    errors: list = []
    warnings: list = []
    
    class Config:
        arbitrary_types_allowed = True

class FMSAgent:
    """
    Production FMS Agent with real-time logging
    """
    
    def __init__(
        self,
        prompt: str,
        model: str = "gpt-4o",
        temperature: float = 1.0,
        log_callback: Optional[Callable] = None
    ):
        self.prompt = prompt
        self.model = model
        self.temperature = temperature
        self.log_callback = log_callback
        
        # Initialize OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")
        
        self.client = OpenAI(api_key=api_key)
        
        # State
        self.state = AgentState(prompt=prompt)
        
        logger.info(f"FMS Agent initialized: model={model}, temp={temperature}")
    
    async def log(self, level: str, stage: str, message: str, data: dict = None):
        """Log message and broadcast to WebSocket clients"""
        log_entry = {
            "level": level,
            "stage": stage,
            "message": message,
            "data": data or {},
            "timestamp": datetime.now().isoformat()
        }
        
        # Python logging
        log_func = getattr(logger, level.lower(), logger.info)
        log_func(f"[{stage}] {message}")
        
        # Broadcast to WebSocket
        if self.log_callback:
            await self.log_callback(level, stage, message, data)
    
    def invoke_llm(self, user_prompt: str, system_prompt: Optional[str] = None) -> str:
        """Invoke OpenAI LLM"""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": user_prompt})
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature
        )
        
        return response.choices[0].message.content
    
    async def structure_agent(self) -> FlowSchema:
        """Generate system structure"""
        await self.log("INFO", "structure", "🏗️ Structure Agent: Designing system architecture")
        
        # Complete professional prompt from main_cli.py
        system_prompt = """You are an expert business process architect and database designer.
Your role is to analyze business requirements and design comprehensive, professional
flow management systems using Google Sheets as the implementation platform.

Key Principles:
1. Design for scalability and maintainability
2. Follow database normalization principles
3. Include proper relationships between entities
4. Consider real-world business workflows
5. Add validation and data integrity measures
6. Think about reporting and analytics needs
7. Design for multiple user roles when relevant

When designing:
- Identify all key entities and their attributes
- Define clear relationships between entities
- Include audit fields (created_date, modified_date, status)
- Consider workflow stages and approvals
- Plan for data validation and business rules
- Think about integration points with other systems
"""
        
        user_prompt = f"""Design a comprehensive Flow Management System for:

"{self.prompt}"

Create a detailed system structure with the following:

1. System Overview:
   - System name (professional, descriptive)
   - Clear description of the system's purpose
   - Key workflow stages
   - Required integrations (if any)

2. For Each Sheet/Entity:
   - Meaningful name
   - Clear description of its purpose
   - Comprehensive columns with:
     * name (clear, professional naming)
     * type (text, number, date, currency, formula, dropdown, checkbox, email, url)
     * description (what this field represents)
     * required (boolean - is this field mandatory?)
     * validation (any validation rules, optional)
     * default_value (default value if any, optional)
   - primary_key (main identifier column)
   - relationships (list of related sheets)

3. Include these standard workflow sheets where applicable:
   - Master data (customers, products, etc.)
   - Transaction sheets (orders, invoices, etc.)
   - Process tracking (status, approvals, etc.)
   - Reporting/analytics data

Return ONLY valid JSON matching this exact structure:
{{
  "system_name": "Professional System Name",
  "description": "Comprehensive system description",
  "version": "1.0",
  "workflow_stages": ["Stage 1", "Stage 2", "Stage 3"],
  "integrations": ["Integration 1", "Integration 2"],
  "sheets": [
    {{
      "name": "Sheet Name",
      "description": "Sheet purpose",
      "primary_key": "ID",
      "relationships": ["Related Sheet 1", "Related Sheet 2"],
      "columns": [
        {{
          "name": "Column Name",
          "type": "text",
          "description": "Column purpose",
          "required": true,
          "validation": "validation rule",
          "default_value": "default"
        }}
      ]
    }}
  ]
}}

Make it production-ready and professional!"""
        
        await self.log("INFO", "structure", "Invoking LLM for structure generation...")
        
        response = self.invoke_llm(user_prompt, system_prompt)
       
        cleaned = JSONCleaner.clean(response)
        flow = FlowSchema.model_validate_json(cleaned)
        
        # Save structure
        if self.state.project_folder:
            schema_file = self.state.project_folder / "schemas" / "flow_structure.json"
            schema_file.parent.mkdir(parents=True, exist_ok=True)
            with open(schema_file, 'w', encoding='utf-8') as f:
                f.write(flow.model_dump_json(indent=2))
        
        await self.log("INFO", "structure", f"✅ System structure created: {flow.system_name}", {
            "sheets_count": len(flow.sheets),
            "workflow_stages": flow.workflow_stages
        })
        
        self.state.flow = flow
        return flow
    
    async def formula_agent(self) -> FormulaPlan:
        """Generate formulas"""
        if not self.state.flow:
            raise ValueError("No flow structure available")
        
        await self.log("INFO", "formula", "⚙️ Formula Agent: Creating automated calculations")
        
        # Build comprehensive sheet information
        sheet_details = []
        for sheet in self.state.flow.sheets:
            cols_info = []
            for col in sheet.columns:
                cols_info.append(f"    - {col.name} ({col.type}): {col.description or 'N/A'}")
            
            sheet_details.append(f"""
Sheet: "{sheet.name}"
Description: {sheet.description or 'N/A'}
Primary Key: {sheet.primary_key or 'N/A'}
Columns:
{chr(10).join(cols_info)}
""")
        
        available_info = "\n".join(sheet_details)
        
        # Complete professional prompt from main_cli.py
        system_prompt = """You are an expert in Google Sheets formulas and business logic automation.
Your role is to create intelligent formulas that automate calculations, validations,
and data transformations in flow management systems.

Formula Design Principles:
1. Use ONLY columns that exist in the provided structure
2. Create practical, useful calculations
3. Keep formulas maintainable and understandable
4. Consider performance for large datasets
5. Add proper error handling (IFERROR, IFNA)
6. Use relative references for auto-fill capability
7. Create formulas that add real business value

Common Formula Types:
- Calculations: SUM, AVERAGE, COUNT, mathematical operations
- Lookups: VLOOKUP, INDEX-MATCH, XLOOKUP
- Conditionals: IF, IFS, SWITCH
- Text: CONCATENATE, TEXT, LEFT, RIGHT, MID
- Dates: TODAY, NOW, DATE, DATEDIF, WORKDAY
- Status tracking: Based on conditions and dates
- Data validation: Check integrity and consistency

Google Sheets Formula Syntax:
- Column references: A1, B2, C3 (will be converted)
- Ranges: A2:A10, B2:B (entire column from row 2)
- Functions: Always use proper Google Sheets function names
- Text in formulas: Use double quotes "text"
- Comparisons: =, <>, <, >, <=, >=
"""
        
        user_prompt = f"""Create intelligent formulas for this system:

SYSTEM STRUCTURE:
{available_info}

IMPORTANT RULES:
1. Only create formulas for columns that ALREADY EXIST in the structure above
2. Use simple Google Sheets formulas (avoid complex cross-sheet references initially)
3. Formulas should add real business value
4. Include proper error handling
5. Make formulas auto-fillable (use relative references)

Create formulas for:
- Calculated fields (totals, subtotals, percentages)
- Status determination (based on dates, conditions)
- Data concatenation (full names, addresses)
- Date calculations (days elapsed, due dates)
- Conditional values (based on business rules)
- Lookup values (from related sheets if applicable)

Return ONLY valid JSON:
{{
  "formulas": [
    {{
      "sheet": "Sheet Name",
      "target_column": "Exact Column Name",
      "start_row": 2,
      "formula": "=FORMULA_HERE",
      "description": "Clear description of what this calculates",
      "dependencies": ["Column1", "Column2"],
      "apply_to_all_rows": true
    }}
  ],
  "validation_rules": [],
  "conditional_formatting": []
}}

If no formulas are needed for this system, return an empty formulas array.
Focus on quality over quantity - only create formulas that add real value!"""
        
        await self.log("INFO", "formula", "Invoking LLM for formula generation...")
        
        response = self.invoke_llm(user_prompt, system_prompt)
        cleaned = JSONCleaner.clean(response)
        formulas = FormulaPlan.model_validate_json(cleaned)
        
        # Save formulas
        if self.state.project_folder:
            formula_file = self.state.project_folder / "schemas" / "formula_plan.json"
            with open(formula_file, 'w', encoding='utf-8') as f:
                f.write(formulas.model_dump_json(indent=2))
        
        await self.log("INFO", "formula", f"✅ Formulas created: {len(formulas.formulas)} formulas")
        
        self.state.formulas = formulas
        return formulas
    
    async def create_google_sheet(self) -> tuple:
        """Create Google Sheet"""
        await self.log("INFO", "sheets", "📊 Creating Google Spreadsheet...")
        
        # Authenticate
        google_manager = GoogleServicesManager()
        drive, sheets = google_manager.authenticate()
        
        sheets_manager = GoogleSheetsManager(drive, sheets)
        
        # Create spreadsheet
        spreadsheet_id = sheets_manager.create_spreadsheet(self.state.flow.system_name)
        
        await self.log("INFO", "sheets", f"Spreadsheet created: {spreadsheet_id}")
        
        # Setup sheets
        sheets_manager.setup_sheets(spreadsheet_id, self.state.flow)
        
        # Apply formulas
        sheets_manager.apply_formulas(spreadsheet_id, self.state.flow, self.state.formulas)
        
        await self.log("INFO", "sheets", "✅ Google Sheet ready!")
        
        return spreadsheet_id, sheets_manager
    
    async def execute(self) -> Dict[str, Any]:
        """Execute complete FMS workflow"""
        start_time = datetime.now()
        
        try:
            # Create project folder
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
            
            # Save metadata
            metadata = ProjectManager.save_metadata(
                self.state.project_folder,
                self.prompt,
                spreadsheet_id,
                self.state.flow,
                execution_time
            )
            
            # Generate documentation
            DocumentationGenerator.generate(
                self.state.project_folder,
                self.prompt,
                self.state.flow,
                self.state.formulas,
                spreadsheet_id,
                metadata
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
