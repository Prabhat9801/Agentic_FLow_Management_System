"""
Google Sheets Flow Management System - Enhanced Workflow Stages
---------------------------------------------------------
An intelligent agent that creates professional Flow Management Systems
with workflow stages, planned/actual/delay tracking, and visual formatting.

Author: Enhanced by Claude
Version: 3.0
"""

import os
import json
import re
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum

from dotenv import load_dotenv
from pydantic import BaseModel, Field, validator
from openai import OpenAI
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError

# =====================================================
# CONFIGURATION & LOGGING
# =====================================================
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/fms_agent.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
# Fix Windows encoding for emojis
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

logger = logging.getLogger(__name__)

# =====================================================
# CONSTANTS
# =====================================================
class Config:
    """Application configuration"""
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    TEMPERATURE = float(os.getenv("TEMPERATURE", "0.2"))
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    PROJECT_BASE_DIR = Path(os.getenv("PROJECT_BASE_DIR", "projects"))
    
    SCOPES = [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/spreadsheets"
    ]

class ColumnType(str, Enum):
    """Supported column types"""
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    CURRENCY = "currency"
    FORMULA = "formula"
    DROPDOWN = "dropdown"
    CHECKBOX = "checkbox"
    EMAIL = "email"
    URL = "url"

# Stage color palette
STAGE_COLORS = [
    {"red": 0.9, "green": 0.85, "blue": 0.85},  # Light red
    {"red": 0.85, "green": 0.9, "blue": 0.85},  # Light green
    {"red": 0.85, "green": 0.85, "blue": 0.9},  # Light blue
    {"red": 0.95, "green": 0.9, "blue": 0.75},  # Light yellow
    {"red": 0.9, "green": 0.85, "blue": 0.9},   # Light purple
    {"red": 0.85, "green": 0.95, "blue": 0.9},  # Light cyan
    {"red": 0.95, "green": 0.85, "blue": 0.8},  # Light orange
    {"red": 0.9, "green": 0.9, "blue": 0.85},   # Light beige
]

# =====================================================
# ENHANCED SCHEMAS WITH STAGE SUPPORT
# =====================================================
class WorkflowStage(BaseModel):
    """Represents a workflow stage with its columns"""
    stage_number: int = Field(..., description="Stage sequence number")
    stage_name: str = Field(..., description="Stage name/title")
    stage_description: Optional[str] = Field(None, description="Stage description")
    columns: List[str] = Field(default_factory=list, description="Column names for this stage")
    has_planned: bool = Field(default=True, description="Include Planned column")
    has_actual: bool = Field(default=True, description="Include Actual column")
    has_delay: bool = Field(default=True, description="Include Delay column")
    
    @validator('stage_name')
    def validate_stage_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Stage name cannot be empty")
        return re.sub(r'[^\w\s-]', '', v).strip()

class ColumnInfo(BaseModel):
    """Enhanced column information with stage awareness"""
    name: str = Field(..., description="Column name")
    type: ColumnType = Field(default=ColumnType.TEXT, description="Column data type")
    description: Optional[str] = Field(None, description="Column purpose description")
    required: bool = Field(default=False, description="Is this column required?")
    validation: Optional[str] = Field(None, description="Validation rule")
    default_value: Optional[str] = Field(None, description="Default value")
    stage_number: Optional[int] = Field(None, description="Associated stage number")
    is_planned: bool = Field(default=False, description="Is this a Planned column?")
    is_actual: bool = Field(default=False, description="Is this an Actual column?")
    is_delay: bool = Field(default=False, description="Is this a Delay column?")
    
    @validator('default_value', pre=True)
    def convert_default_value(cls, v):
        if v is None:
            return v
        return str(v)
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Column name cannot be empty")
        return re.sub(r'[^\w\s-]', '', v).strip()

class SheetSchema(BaseModel):
    """Enhanced sheet schema with workflow stages"""
    name: str = Field(..., description="Sheet name")
    columns: List[ColumnInfo] = Field(..., description="Sheet columns")
    stages: List[WorkflowStage] = Field(default_factory=list, description="Workflow stages")
    description: Optional[str] = Field(None, description="Sheet purpose")
    primary_key: Optional[str] = Field(None, description="Primary key column")
    relationships: Optional[List[str]] = Field(default_factory=list, description="Related sheets")
    has_timestamp: bool = Field(default=False, description="Has Timestamp as first column")
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Sheet name cannot be empty")
        return re.sub(r'[^\w\s-]', '', v)[:100]
    
    def get_column_names(self) -> List[str]:
        return [col.name for col in self.columns]
    
    def get_column_by_name(self, name: str) -> Optional[ColumnInfo]:
        for col in self.columns:
            if col.name == name:
                return col
        return None

class FlowSchema(BaseModel):
    """Complete flow management system schema with stages"""
    system_name: str = Field(..., description="System name")
    description: str = Field(..., description="System description")
    version: str = Field(default="1.0", description="Schema version")
    sheets: List[SheetSchema] = Field(..., description="System sheets")
    workflow_stages: Optional[List[str]] = Field(default_factory=list, description="Overall workflow stages")
    integrations: Optional[List[str]] = Field(default_factory=list, description="Required integrations")
    has_login_master: bool = Field(default=True, description="Include Login Master sheet")
    
    @validator('system_name')
    def validate_system_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("System name cannot be empty")
        return v.strip()

class FormulaRule(BaseModel):
    """Enhanced formula rule with stage support"""
    sheet: str = Field(..., description="Target sheet name")
    target_column: str = Field(..., description="Target column name")
    start_row: int = Field(default=2, ge=2, description="Starting row")
    formula: str = Field(..., description="Google Sheets formula")
    description: str = Field(..., description="Formula purpose")
    dependencies: Optional[List[str]] = Field(default_factory=list, description="Dependent columns")
    apply_to_all_rows: bool = Field(default=True, description="Auto-fill formula")
    is_planned_formula: bool = Field(default=False, description="Is this a Planned date formula?")
    is_delay_formula: bool = Field(default=False, description="Is this a Delay calculation formula?")
    stage_number: Optional[int] = Field(None, description="Associated stage number")

class FormulaPlan(BaseModel):
    """Complete formula implementation plan"""
    formulas: List[FormulaRule] = Field(default_factory=list)
    validation_rules: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    conditional_formatting: Optional[List[Dict[str, Any]]] = Field(default_factory=list)

# =====================================================
# OPENAI CLIENT
# =====================================================
class LLMClient:
    """Enhanced OpenAI client"""
    
    def __init__(self):
        if not Config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
        self.model = Config.OPENAI_MODEL
        self.temperature = Config.TEMPERATURE
        logger.info(f"Initialized OpenAI client with model: {self.model}")
    
    def invoke(self, prompt: str, system_prompt: Optional[str] = None, 
               response_format: Optional[Dict] = None) -> str:
        """Invoke OpenAI with retry logic"""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        for attempt in range(Config.MAX_RETRIES):
            try:
                logger.debug(f"LLM invocation attempt {attempt + 1}/{Config.MAX_RETRIES}")
                
                kwargs = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": self.temperature,
                }
                
                if response_format:
                    kwargs["response_format"] = response_format
                
                response = self.client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content
                
                logger.debug(f"LLM response received: {len(content)} characters")
                return content
                
            except Exception as e:
                logger.error(f"LLM invocation failed (attempt {attempt + 1}): {str(e)}")
                if attempt == Config.MAX_RETRIES - 1:
                    raise
                continue
        
        raise Exception("Max retries exceeded for LLM invocation")

# Initialize global LLM client
llm = LLMClient()

# =====================================================
# GOOGLE SERVICES
# =====================================================
class GoogleServicesManager:
    """Manages Google API authentication and services"""
    
    def __init__(self):
        self.creds = None
        self.drive = None
        self.sheets = None
    
    def authenticate(self) -> tuple:
        """Authenticate and return Google services"""
        logger.info("Authenticating with Google services...")
        
        token_path = Path("token.json")
        credentials_path = None
        
        for file in Path(".").glob("client_secret*.json"):
            credentials_path = file
            break
        
        if not credentials_path:
            raise FileNotFoundError(
                "Google OAuth credentials file not found. "
                "Please download it from Google Cloud Console."
            )
        
        if token_path.exists():
            self.creds = Credentials.from_authorized_user_file(str(token_path), Config.SCOPES)
        
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                logger.info("Refreshing expired credentials...")
                self.creds.refresh(Request())
            else:
                logger.info("Starting OAuth flow...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(credentials_path), Config.SCOPES
                )
                self.creds = flow.run_local_server(port=0)
            
            token_path.write_text(self.creds.to_json())
            logger.info("Credentials saved successfully")
        
        self.drive = build("drive", "v3", credentials=self.creds)
        self.sheets = build("sheets", "v4", credentials=self.creds)
        
        logger.info("Google services initialized successfully")
        return self.drive, self.sheets

# =====================================================
# UTILITY FUNCTIONS
# =====================================================
class JSONCleaner:
    """Enhanced JSON cleaning from LLM responses"""
    
    @staticmethod
    def clean(content: str) -> str:
        """Clean and extract JSON from LLM response"""
        content = content.strip()
        
        if content.startswith("```"):
            first_newline = content.find("\n")
            if first_newline != -1:
                content = content[first_newline + 1:]
            
            closing_fence = content.rfind("```")
            if closing_fence != -1:
                content = content[:closing_fence]
        
        content = content.strip()
        
        start_idx = content.find("{")
        if start_idx == -1:
            start_idx = content.find("[")
            if start_idx == -1:
                raise ValueError("No JSON object or array found in response")
        
        open_char = content[start_idx]
        close_char = "}" if open_char == "{" else "]"
        count = 0
        end_idx = -1
        
        for i in range(start_idx, len(content)):
            if content[i] == open_char:
                count += 1
            elif content[i] == close_char:
                count -= 1
                if count == 0:
                    end_idx = i + 1
                    break
        
        if end_idx == -1:
            raise ValueError("Malformed JSON: no matching closing bracket")
        
        cleaned = content[start_idx:end_idx]
        
        try:
            json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"JSON validation failed: {e}")
            raise ValueError(f"Invalid JSON structure: {e}")
        
        return cleaned

class ProjectManager:
    """Manages project folder structure and files"""
    
    @staticmethod
    def create_project_folder(prompt: str) -> Path:
        """Create organized project folder structure"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        sanitized = re.sub(r'[^\w\s-]', '', prompt)[:50]
        sanitized = re.sub(r'[-\s]+', '_', sanitized).strip('_')
        
        folder_name = f"{timestamp}_{sanitized}"
        folder_path = Config.PROJECT_BASE_DIR / folder_name
        
        folder_path.mkdir(parents=True, exist_ok=True)
        (folder_path / "schemas").mkdir(exist_ok=True)
        (folder_path / "docs").mkdir(exist_ok=True)
        (folder_path / "logs").mkdir(exist_ok=True)
        
        logger.info(f"Project folder created: {folder_path}")
        return folder_path
    
    @staticmethod
    def save_metadata(folder: Path, prompt: str, spreadsheet_id: str, 
                     flow: FlowSchema, execution_time: float) -> Dict:
        """Save comprehensive project metadata"""
        metadata = {
            "project_info": {
                "prompt": prompt,
                "created_at": datetime.now().isoformat(),
                "execution_time_seconds": round(execution_time, 2)
            },
            "spreadsheet": {
                "id": spreadsheet_id,
                "url": f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}",
                "edit_url": f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
            },
            "system": {
                "name": flow.system_name,
                "description": flow.description,
                "version": flow.version,
                "total_sheets": len(flow.sheets),
                "workflow_stages": flow.workflow_stages,
                "integrations": flow.integrations,
                "has_login_master": flow.has_login_master
            },
            "structure": {
                "sheets": [
                    {
                        "name": sheet.name,
                        "description": sheet.description,
                        "columns": [
                            {
                                "name": col.name,
                                "type": col.type.value,
                                "required": col.required,
                                "description": col.description,
                                "stage_number": col.stage_number
                            }
                            for col in sheet.columns
                        ],
                        "primary_key": sheet.primary_key,
                        "relationships": sheet.relationships,
                        "stages": [
                            {
                                "stage_number": stage.stage_number,
                                "stage_name": stage.stage_name,
                                "columns": stage.columns
                            }
                            for stage in sheet.stages
                        ]
                    }
                    for sheet in flow.sheets
                ]
            },
            "statistics": {
                "total_columns": sum(len(sheet.columns) for sheet in flow.sheets),
                "total_stages": sum(len(sheet.stages) for sheet in flow.sheets),
                "sheets_with_relationships": len([s for s in flow.sheets if s.relationships])
            }
        }
        
        metadata_path = folder / "metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Metadata saved to {metadata_path}")
        return metadata

# =====================================================
# LANGGRAPH STATE
# =====================================================
class AgentState(BaseModel):
    """Enhanced agent state"""
    prompt: str
    project_folder: Optional[Path] = None
    flow: Optional[FlowSchema] = None
    formulas: Optional[FormulaPlan] = None
    validation_rules: Optional[List[Dict]] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    
    class Config:
        arbitrary_types_allowed = True

# =====================================================
# AGENT 1: STRUCTURE AGENT WITH STAGE SUPPORT
# =====================================================
def structure_agent(state: AgentState) -> Dict:
    """Enhanced structure agent with workflow stage support"""
    print("\n" + "="*70)
    print("🏗️  STRUCTURE AGENT: Designing Workflow System with Stages")
    print("="*70)
    print(f"\n📝 User Requirement: {state.prompt}")
    
    system_prompt = """You are an expert business process architect specializing in workflow management systems.
Your role is to analyze business requirements and design comprehensive workflow systems.

CRITICAL REQUIREMENTS:
1. Every main worksheet MUST have "Timestamp" as the first column
2. Every system MUST include a "Login Master" sheet
3. Workflow stages are sequential steps in a process
4. Each stage has: Planned (date), Actual (date), and Delay (calculated) columns
5. **Column Ordering within Stage**: [Planned{N}] -> [Actual{N}] -> [Delay{N}] -> [Other Stage Columns]
   - Planned, Actual, Delay MUST be the first 3 columns of every stage.
6. Stages are numbered sequentially: Planned1, Actual1, Delay1, Planned2, Actual2, Delay2, etc.
7. Do NOT create columns named "Stage Color" or "Color". Stage colors are handled by formatting.
8. Group related stage columns together in the worksheet.

CRITICAL RULES FOR SHEETS:
- Create ONE (1) Primary Workflow Sheet that tracks the entire process lifecycle.
- Define Stages within this Main Sheet (e.g. Stage 1, Stage 2, etc.)
- **DO NOT** create separate sheets for individual stages (e.g. don't create a "Stage 1 Sheet" if Stage 1 is already in the Main Sheet).
- Create Supporting Sheets ONLY for Master Data (e.g. Item Master, Vendor Master) or Dropdown values.
- If a concept (like "Purchase Requisition" or "Payment") is a step in the flow, keep it as a STAGE in the Main Sheet, NOT a separate sheet.

Workflow Stage Design:
- Identify sequential steps in the workflow (e.g., LOI, Sanction, Foundation, Installation, etc.)
- Each stage represents a key milestone or phase
- Planned = target completion date
- Actual = actual completion date (user enters from frontend)
- Delay = difference between Planned and Actual (formula-based)

Sheet Organization:
- Main worksheet contains all workflow stages
- Login Master sheet for user authentication
- Related stages grouped together visually
"""
    
    user_prompt = f"""Design a comprehensive Workflow Management System for:

"{state.prompt}"

Create a detailed system structure following these rules:

1. System Overview:
   - Professional system name
   - Clear description
   - List of workflow stages (sequential steps)

2. Main Worksheet (primary workflow sheet):
   - MUST start with "Timestamp" column
   - Define workflow stages (e.g., Stage 1: LOI, Stage 2: Sanction, Stage 3: Foundation, etc.)
   - For each stage, include:
     * Planned{{N}} column (date type) - MUST BE FIRST in stage
     * Actual{{N}} column (date type) - MUST BE SECOND in stage
     * Delay{{N}} column (formula type) - MUST BE THIRD in stage
     * Stage-specific columns (data related to that stage) - Follows Delay
   - Group all columns for each stage together
   - Do NOT add "Stage Color" columns
   - Include any additional tracking columns

3. Supporting Sheets:
   - Master data sheets (reference data, lookups)
   - Dump/import sheets if needed
   - Any relationship sheets

4. Login Master Sheet (REQUIRED):
   - Columns: User Name, User ID, Pass, Role, Page Access, Status, Page Name

Return ONLY valid JSON matching this structure:
{{
  "system_name": "Professional System Name",
  "description": "System description",
  "version": "1.0",
  "workflow_stages": ["Stage 1 Name", "Stage 2 Name", "Stage 3 Name"],
  "has_login_master": true,
  "sheets": [
    {{
      "name": "Main Workflow Sheet Name",
      "description": "Main workflow tracking",
      "has_timestamp": true,
      "primary_key": "ID or Reg ID",
      "relationships": ["Related Sheet 1"],
      "stages": [
        {{
          "stage_number": 1,
          "stage_name": "Stage 1 Name",
          "stage_description": "What this stage represents",
          "columns": ["Column1", "Column2"],
          "has_planned": true,
          "has_actual": true,
          "has_delay": true
        }},
        {{
          "stage_number": 2,
          "stage_name": "Stage 2 Name",
          "stage_description": "What this stage represents",
          "columns": ["Column3", "Column4"],
          "has_planned": true,
          "has_actual": true,
          "has_delay": true
        }}
      ],
      "columns": [
        {{
          "name": "Timestamp",
          "type": "date",
          "description": "Record creation timestamp",
          "required": true,
          "stage_number": null
        }},
        {{
          "name": "Serial No",
          "type": "number",
          "description": "Serial number",
          "required": true,
          "stage_number": null
        }},
        {{
          "name": "Reg ID",
          "type": "number",
          "description": "Registration ID",
          "required": true,
          "stage_number": null
        }},
        {{
          "name": "Column from Stage 1",
          "type": "text",
          "description": "Stage 1 specific column",
          "required": false,
          "stage_number": 1
        }},
        {{
          "name": "Planned1",
          "type": "date",
          "description": "Stage 1 planned completion date",
          "required": false,
          "stage_number": 1,
          "is_planned": true
        }},
        {{
          "name": "Actual1",
          "type": "date",
          "description": "Stage 1 actual completion date",
          "required": false,
          "stage_number": 1,
          "is_actual": true
        }},
        {{
          "name": "Delay1",
          "type": "formula",
          "description": "Stage 1 delay calculation",
          "required": false,
          "stage_number": 1,
          "is_delay": true
        }}
      ]
    }},
    {{
      "name": "Login Master",
      "description": "User authentication and access control",
      "columns": [
        {{"name": "User Name", "type": "text", "required": true}},
        {{"name": "User ID", "type": "text", "required": true}},
        {{"name": "Pass", "type": "text", "required": true}},
        {{"name": "Role", "type": "text", "required": true}},
        {{"name": "Page Access", "type": "text", "required": false}},
        {{"name": "Status", "type": "text", "required": true}},
        {{"name": "Page Name", "type": "text", "required": false}}
      ]
    }}
  ]
}}

Design a professional, production-ready system!
"""
    
    try:
        logger.info("Invoking LLM for structure generation...")
        response = llm.invoke(user_prompt, system_prompt=system_prompt)
        
        cleaned_json = JSONCleaner.clean(response)
        flow = FlowSchema.model_validate_json(cleaned_json)
        logger.info(f"Flow schema validated: {flow.system_name}")
        
        # Save structure
        if state.project_folder:
            schema_file = state.project_folder / "schemas" / "flow_structure.json"
            with open(schema_file, "w", encoding="utf-8") as f:
                f.write(flow.model_dump_json(indent=2))
            logger.info(f"Structure saved to {schema_file}")
        
        # Display summary
        print("\n✅ System Structure Created Successfully!")
        print(f"\n📊 System: {flow.system_name}")
        print(f"📝 Description: {flow.description}")
        
        if flow.workflow_stages:
            print(f"\n🔄 Workflow Stages ({len(flow.workflow_stages)}):")
            for i, stage in enumerate(flow.workflow_stages, 1):
                print(f"   {i}. {stage}")
        
        print(f"\n📋 Sheets ({len(flow.sheets)}):")
        for i, sheet in enumerate(flow.sheets, 1):
            print(f"\n   {i}. {sheet.name}")
            if sheet.stages:
                print(f"      Stages: {len(sheet.stages)}")
                for stage in sheet.stages:
                    print(f"        - Stage {stage.stage_number}: {stage.stage_name}")
            print(f"      Total Columns: {len(sheet.columns)}")
        
        return {"flow": flow}
        
    except Exception as e:
        error_msg = f"Structure generation failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        print(f"\n❌ Error: {error_msg}")
        return {"errors": [error_msg]}

# =====================================================
# AGENT 2: FORMULA AGENT WITH STAGE FORMULAS
# =====================================================
def formula_agent(state: AgentState) -> Dict:
    """Enhanced formula agent with stage-based formulas"""
    print("\n" + "="*70)
    print("⚙️  FORMULA AGENT: Creating Stage Formulas")
    print("="*70)
    
    if not state.flow:
        error_msg = "No flow structure available"
        logger.error(error_msg)
        return {"errors": [error_msg]}
    
    # Build sheet information
    sheet_details = []
    for sheet in state.flow.sheets:
        cols_info = []
        for col in sheet.columns:
            stage_info = f" (Stage {col.stage_number})" if col.stage_number else ""
            cols_info.append(f"    - {col.name} ({col.type.value}){stage_info}: {col.description or 'N/A'}")
        
        stage_info = ""
        if sheet.stages:
            stage_info = f"\nStages:\n"
            for stage in sheet.stages:
                stage_info += f"  Stage {stage.stage_number}: {stage.stage_name}\n"
        
        sheet_details.append(f"""
Sheet: "{sheet.name}"
Description: {sheet.description or 'N/A'}
Has Timestamp: {sheet.has_timestamp}
{stage_info}
Columns:
{chr(10).join(cols_info)}
""")
    
    available_info = "\n".join(sheet_details)
    
    system_prompt = """You are an expert in Google Sheets formulas.

CRITICAL FORMULA REQUIREMENTS:

1. Planned Formulas (for each stage):
   - Formula: =ARRAYFORMULA(if(row(A4:A)=4,"Planned{N}",IF(A4:A="","",TEXT(A4:A, "yyyy-mm-dd hh:mm:ss"))))
   - Logic: Copies Timestamp (Col A) if preset, formatted as a string "yyyy-mm-dd hh:mm:ss".
   - Start from row 4.

2. Delay Formulas (for each stage):
   - Formula: =ARRAYFORMULA(if(row(A4:A)=4,"Delay{N}",if(AND(Actual{N}4:Actual{N}<>"",Planned{N}4:Planned{N}<>""),Actual{N}4:Actual{N}-DATEVALUE(Planned{N}4:Planned{N}),"")))
   - Calculates difference between Actual (Date) and Planned (Text Timestamp).
   - Use DATEVALUE() for Planned column since it is text.
   - Start from row 4.

3. Lookup Formulas (if needed):
   - Use VLOOKUP or XLOOKUP.

Google Sheets Syntax:
- ARRAYFORMULA for auto-fill
- Range notation: A4:A
- Conditional: IF(condition, true_value, false_value)
- Row function: ROW(A4:A)
"""
    
    user_prompt = f"""Create formulas for this workflow system:

SYSTEM STRUCTURE:
{available_info}

REQUIRED FORMULAS:

1. For each Planned column (Planned1, Planned2, etc.):
   - Use: =ARRAYFORMULA(if(row(A4:A)=4,"PlannedN",IF(A4:A="","",TEXT(A4:A, "yyyy-mm-dd hh:mm:ss"))))
   - Formats timestamp as string.

2. For each Delay column (Delay1, Delay2, etc.):
   - Calculate: Actual - DATEVALUE(Planned)
   - Handle empty values
   - Auto-fill for all rows starting at Row 4

3. Any lookup formulas needed.

Return ONLY valid JSON:
{{
  "formulas": [
    {{
      "sheet": "Sheet Name",
      "target_column": "Planned1",
      "start_row": 4,
      "formula": "=ARRAYFORMULA(if(row(A4:A)=4,\\"Planned1\\",IF(A4:A=\\"\\",\\"\\",TEXT(A4:A, \\"yyyy-mm-dd hh:mm:ss\\"))))",
      "description": "Stage 1 planned calculated from timestamp",
      "dependencies": ["Timestamp"],
      "apply_to_all_rows": true,
      "is_planned_formula": true,
      "stage_number": 1
    }},
    {{
      "sheet": "Sheet Name",
      "target_column": "Delay1",
      "start_row": 4,
      "formula": "=ARRAYFORMULA(if(row(A4:A)=4,\\"Delay1\\",if(AND(N4:N<>\\"\\",M4:M<>\\"\\"),N4:N-DATEVALUE(M4:M),\\"\\")))",
      "description": "Stage 1 delay calculation",
      "dependencies": ["Planned1", "Actual1"],
      "apply_to_all_rows": true,
      "is_delay_formula": true,
      "stage_number": 1
    }}
  ],
  "validation_rules": [],
  "conditional_formatting": []
}}

Generate formulas for ALL stages!
"""
    
    try:
        logger.info("Invoking LLM for formula generation...")
        response = llm.invoke(user_prompt, system_prompt=system_prompt)
        
        cleaned_json = JSONCleaner.clean(response)
        formulas = FormulaPlan.model_validate_json(cleaned_json)
        logger.info(f"Formula plan validated: {len(formulas.formulas)} formulas")
        
        # Validate formulas
        validated_formulas = []
        for formula in formulas.formulas:
            sheet = next((s for s in state.flow.sheets if s.name == formula.sheet), None)
            if not sheet:
                logger.warning(f"Skipping formula: Sheet '{formula.sheet}' not found")
                continue
            
            if formula.target_column not in sheet.get_column_names():
                logger.warning(f"Skipping formula: Column '{formula.target_column}' not found")
                continue
            
            validated_formulas.append(formula)
        
        formulas.formulas = validated_formulas
        
        # Save formulas
        if state.project_folder:
            formula_file = state.project_folder / "schemas" / "formula_plan.json"
            with open(formula_file, "w", encoding="utf-8") as f:
                f.write(formulas.model_dump_json(indent=2))
            logger.info(f"Formulas saved to {formula_file}")
        
        print(f"\n✅ Formula Plan Created: {len(formulas.formulas)} formulas")
        
        if formulas.formulas:
            for i, formula in enumerate(formulas.formulas, 1):
                print(f"\n   {i}. {formula.description}")
                print(f"      Location: {formula.sheet}.{formula.target_column}")
                print(f"      Formula: {formula.formula[:80]}...")
        
        return {"formulas": formulas}
        
    except Exception as e:
        error_msg = f"Formula generation failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        print(f"\n❌ Error: {error_msg}")
        return {"errors": [error_msg]}

# =====================================================
# GOOGLE SHEETS OPERATIONS WITH STAGE FORMATTING
# =====================================================
class GoogleSheetsManager:
    """Enhanced Google Sheets operations with stage formatting"""
    
    def __init__(self, drive, sheets):
        self.drive = drive
        self.sheets = sheets
    
    def create_spreadsheet(self, title: str) -> str:
        """Create a new spreadsheet"""
        try:
            logger.info(f"Creating spreadsheet: {title}")
            print(f"\n   📄 Creating spreadsheet: '{title}'...")
            
            file = self.drive.files().create(
                body={
                    "name": title,
                    "mimeType": "application/vnd.google-apps.spreadsheet"
                },
                fields="id"
            ).execute()
            
            spreadsheet_id = file["id"]
            logger.info(f"Spreadsheet created: {spreadsheet_id}")
            print(f"   ✅ Spreadsheet created")
            
            return spreadsheet_id
            
        except HttpError as e:
            logger.error(f"Failed to create spreadsheet: {e}")
            raise Exception(f"Spreadsheet creation failed: {e}")
    
    def setup_sheets(self, spreadsheet_id: str, flow: FlowSchema) -> None:
        """Create sheets with stage formatting"""
        try:
            logger.info(f"Setting up {len(flow.sheets)} sheets...")
            print(f"\n   📋 Creating {len(flow.sheets)} sheets...")
            
            # Get default sheet to delete
            spreadsheet = self.sheets.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            default_sheet_id = spreadsheet['sheets'][0]['properties']['sheetId']
            
            requests = []
            
            # Create new sheets
            for sheet in flow.sheets:
                requests.append({
                    "addSheet": {
                        "properties": {
                            "title": sheet.name,
                            "gridProperties": {
                                "rowCount": 1000,
                                "columnCount": len(sheet.columns) + 10
                            }
                        }
                    }
                })
            
            # Execute
            self.sheets.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={"requests": requests}
            ).execute()
            
            print("   ✅ All sheets created")
            
            # Delete default sheet
            try:
                self.sheets.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body={"requests": [{"deleteSheet": {"sheetId": default_sheet_id}}]}
                ).execute()
            except:
                pass
            
            # Add headers and formatting
            print("\n   🎨 Adding headers and stage formatting...")
            for sheet in flow.sheets:
                self._add_headers_with_stage_format(spreadsheet_id, sheet)
            
            print("   ✅ Formatting applied")
            
        except HttpError as e:
            logger.error(f"Failed to setup sheets: {e}")
            raise Exception(f"Sheet setup failed: {e}")
    
    def _add_headers_with_stage_format(self, spreadsheet_id: str, sheet: SheetSchema) -> None:
        """Add headers with stage names and colors (Rows 2 & 3) OR Standard (Row 1)"""
        column_names = sheet.get_column_names()
        
        # Check if sheet has stages
        has_stages = bool(sheet.stages)
        
        if has_stages:
            # --- STAGE FORMAT (Rows 2 & 3) ---
            # Add column headers (Row 3)
            self.sheets.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet.name}!A3",
                valueInputOption="RAW",
                body={"values": [column_names]}
            ).execute()
        else:
            # --- STANDARD FORMAT (Row 1) ---
            # Add column headers (Row 1)
            self.sheets.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet.name}!A1",
                valueInputOption="RAW",
                body={"values": [column_names]}
            ).execute()

        # Get sheet ID
        spreadsheet = self.sheets.spreadsheets().get(
            spreadsheetId=spreadsheet_id
        ).execute()
        
        sheet_id = None
        for s in spreadsheet['sheets']:
            if s['properties']['title'] == sheet.name:
                sheet_id = s['properties']['sheetId']
                break
        
        if sheet_id is None:
            return
        
        # Build formatting requests
        requests = []
        
        if has_stages:
            # 1. Standard format for Header Row (Row 3)
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 2,
                        "endRowIndex": 3
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {"red": 0.95, "green": 0.95, "blue": 0.95},
                            "textFormat": {"bold": True, "fontSize": 10},
                            "horizontalAlignment": "CENTER",
                            "verticalAlignment": "MIDDLE",
                            "wrapStrategy": "WRAP",
                            "borders": {
                                 "bottom": {"style": "SOLID", "width": 1, "color": {"red": 0, "green": 0, "blue": 0}}
                            }
                        }
                    },
                    "fields": "userEnteredFormat"
                }
            })
            
            # 2. Stage Name Logic
            stage_names_row = [""] * len(column_names)
            stage_ranges = {}
            col_indices = {name: i for i, name in enumerate(column_names)}
            
            for stage in sheet.stages:
                start_idx = None
                end_idx = None
                
                # Check explicit columns list
                for col_name in stage.columns:
                     if col_name in col_indices:
                         idx = col_indices[col_name]
                         if start_idx is None or idx < start_idx: start_idx = idx
                         if end_idx is None or idx > end_idx: end_idx = idx
                
                # Check derived from stage_number columns
                if start_idx is None:
                    for col in sheet.columns:
                        if col.stage_number == stage.stage_number:
                            idx = col_indices.get(col.name)
                            if idx is not None:
                                if start_idx is None or idx < start_idx: start_idx = idx
                                if end_idx is None or idx > end_idx: end_idx = idx

                if start_idx is not None and end_idx is not None:
                    stage_names_row[start_idx] = stage.stage_name
                    stage_ranges[stage.stage_number] = {
                        "start": start_idx, 
                        "end": end_idx,
                        "name": stage.stage_name
                    }
            
            # Write Stage Names to Row 2
            if any(stage_names_row):
                self.sheets.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range=f"{sheet.name}!A2",
                    valueInputOption="RAW",
                    body={"values": [stage_names_row]}
                ).execute()
                
                # Format Stages
                for stage_num, info in stage_ranges.items():
                    start = info["start"]
                    end = info["end"]
                    color_idx = (stage_num - 1) % len(STAGE_COLORS)
                    color = STAGE_COLORS[color_idx]
                    
                    # Merge Row 2
                    if end > start:
                        requests.append({
                            "mergeCells": {
                                "range": {
                                    "sheetId": sheet_id,
                                    "startRowIndex": 1,
                                    "endRowIndex": 2,
                                    "startColumnIndex": start,
                                    "endColumnIndex": end + 1
                                },
                                "mergeType": "MERGE_ALL"
                            }
                        })
                    
                    # Color Rows 2 & 3
                    requests.append({
                        "repeatCell": {
                            "range": {
                                "sheetId": sheet_id,
                                "startRowIndex": 1,
                                "endRowIndex": 3,
                                "startColumnIndex": start,
                                "endColumnIndex": end + 1
                            },
                            "cell": {
                                "userEnteredFormat": {
                                    "backgroundColor": color,
                                    "textFormat": {"bold": True, "fontSize": 10},
                                    "horizontalAlignment": "CENTER",
                                    "verticalAlignment": "MIDDLE",
                                    "borders": {
                                        "bottom": {"style": "SOLID", "width": 1, "color": {"red": 0, "green": 0, "blue": 0}},
                                        "left": {"style": "SOLID", "width": 1, "color": {"red": 0, "green": 0, "blue": 0}},
                                        "right": {"style": "SOLID", "width": 1, "color": {"red": 0, "green": 0, "blue": 0}},
                                        "top": {"style": "SOLID", "width": 1, "color": {"red": 0, "green": 0, "blue": 0}}
                                    }
                                }
                            },
                            "fields": "userEnteredFormat"
                        }
                    })

            # Freeze 3 rows
            requests.append({
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": sheet_id,
                        "gridProperties": {"frozenRowCount": 3}
                    },
                    "fields": "gridProperties.frozenRowCount"
                }
            })
            
        else:
            # --- STANDARD FORMATTING (No Stages) ---
            
            # Format Header Row (Row 1)
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0,
                        "endRowIndex": 1
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {"red": 0.2, "green": 0.4, "blue": 0.8},
                            "textFormat": {
                                "bold": True,
                                "foregroundColor": {"red": 1, "green": 1, "blue": 1}
                            },
                            "horizontalAlignment": "CENTER",
                            "verticalAlignment": "MIDDLE",
                            "wrapStrategy": "WRAP"
                        }
                    },
                    "fields": "userEnteredFormat"
                }
            })

            # Freeze 1 row
            requests.append({
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": sheet_id,
                        "gridProperties": {"frozenRowCount": 1}
                    },
                    "fields": "gridProperties.frozenRowCount"
                }
            })
        
        # Execute formatting
        if requests:
            self.sheets.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={"requests": requests}
            ).execute()
        
        logger.info(f"Headers and stage formatting applied for: {sheet.name}")
    
    def apply_formulas(self, spreadsheet_id: str, flow: FlowSchema, plan: FormulaPlan) -> None:
        """Apply formulas"""
        if not plan.formulas:
            print("\n   ℹ️  No formulas to apply")
            return
        
        print(f"\n   ⚙️  Applying {len(plan.formulas)} formulas...")
        
        applied_count = 0
        for formula in plan.formulas:
            try:
                # Apply formula directly
                range_notation = f"{formula.sheet}!{self._get_column_letter(formula.target_column, flow, formula.sheet)}{formula.start_row}"
                
                self.sheets.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range=range_notation,
                    valueInputOption="USER_ENTERED",
                    body={"values": [[formula.formula]]}
                ).execute()
                
                applied_count += 1
                logger.info(f"Formula applied: {formula.sheet}.{formula.target_column}")
                print(f"   ✅ {formula.description}")
                
            except Exception as e:
                logger.warning(f"Failed to apply formula: {e}")
                print(f"   ⚠️  Skipped: {formula.description}")
        
        print(f"\n   ✅ Applied {applied_count}/{len(plan.formulas)} formulas")
    
    def _get_column_letter(self, col_name: str, flow: FlowSchema, sheet_name: str) -> str:
        """Get column letter for a column name"""
        sheet = next((s for s in flow.sheets if s.name == sheet_name), None)
        if not sheet:
            return "A"
        
        col_names = sheet.get_column_names()
        try:
            col_index = col_names.index(col_name)
            return self._col_letter(col_index + 1)
        except ValueError:
            return "A"
    
    @staticmethod
    def _col_letter(index: int) -> str:
        """Convert column index to Excel letter"""
        result = ""
        while index:
            index, rem = divmod(index - 1, 26)
            result = chr(65 + rem) + result
        return result

# =====================================================
# MAIN WORKFLOW
# =====================================================
def build_workflow() -> StateGraph:
    """Build the workflow"""
    workflow = StateGraph(AgentState)
    
    workflow.add_node("structure", structure_agent)
    workflow.add_node("formula", formula_agent)
    
    workflow.set_entry_point("structure")
    workflow.add_edge("structure", "formula")
    workflow.add_edge("formula", END)
    
    return workflow.compile()

def main():
    """Main execution"""
    start_time = datetime.now()
    
    parser = argparse.ArgumentParser(
        description="🤖 Flow Management System - Enhanced Workflow Stages v3.0"
    )
    parser.add_argument("prompt", nargs="?", help="System description")
    parser.add_argument("--model", default=Config.OPENAI_MODEL, help="OpenAI model")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if args.model:
        Config.OPENAI_MODEL = args.model
    
    # Get prompt
    if args.prompt:
        user_prompt = args.prompt
    else:
        print("\n" + "="*70)
        print("🤖 WORKFLOW MANAGEMENT SYSTEM - STAGE-BASED")
        print("="*70)
        print("\nDescribe the workflow system you want to create:")
        print("💡 Example: Solar pump installation tracking system")
        user_prompt = input("\n📝 Your prompt: ").strip()
        
        if not user_prompt:
            print("\n❌ Error: Prompt cannot be empty")
            return
    
    try:
        print("\n" + "="*70)
        print("🚀 STARTING WORKFLOW SYSTEM GENERATION")
        print("="*70)
        print(f"\n📌 System: {user_prompt}")
        print(f"🤖 Model: {Config.OPENAI_MODEL}")
        
        # Create project folder
        project_folder = ProjectManager.create_project_folder(user_prompt)
        print(f"📁 Project: {project_folder.name}")
        
        # Build workflow
        workflow = build_workflow()
        
        # Initialize state
        initial_state = AgentState(
            prompt=user_prompt,
            project_folder=project_folder
        )
        
        # Run workflow
        print("\n" + "="*70)
        print("🔄 EXECUTING WORKFLOW")
        print("="*70)
        
        final_state = workflow.invoke(initial_state.dict())
        
        if final_state.get("errors"):
            print("\n❌ WORKFLOW FAILED")
            for error in final_state["errors"]:
                print(f"   {error}")
            return
        
        # Create spreadsheet
        print("\n" + "="*70)
        print("📊 CREATING GOOGLE SPREADSHEET")
        print("="*70)
        
        google_manager = GoogleServicesManager()
        drive, sheets = google_manager.authenticate()
        
        sheets_manager = GoogleSheetsManager(drive, sheets)
        
        flow = final_state["flow"] if isinstance(final_state["flow"], FlowSchema) else FlowSchema(**final_state["flow"])
        spreadsheet_id = sheets_manager.create_spreadsheet(flow.system_name)
        
        sheets_manager.setup_sheets(spreadsheet_id, flow)
        
        formulas = final_state["formulas"] if isinstance(final_state["formulas"], FormulaPlan) else FormulaPlan(**final_state["formulas"])
        sheets_manager.apply_formulas(spreadsheet_id, flow, formulas)
        
        # Save metadata
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        print("\n" + "="*70)
        print("📄 SAVING METADATA")
        print("="*70)
        
        metadata = ProjectManager.save_metadata(
            project_folder,
            user_prompt,
            spreadsheet_id,
            flow,
            execution_time
        )
        
        # Success message
        print("\n" + "="*70)
        print("✅ SYSTEM GENERATED SUCCESSFULLY!")
        print("="*70)
        
        print(f"\n📊 System: {flow.system_name}")
        print(f"⏱️  Time: {execution_time:.2f}s")
        print(f"📋 Sheets: {len(flow.sheets)}")
        print(f"🔄 Total Stages: {sum(len(s.stages) for s in flow.sheets)}")
        
        print("\n🔗 Spreadsheet:")
        print(f"   {metadata['spreadsheet']['edit_url']}")
        
        print(f"\n📁 Project:")
        print(f"   {project_folder.absolute()}")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelled")
        
    except Exception as e:
        print("\n❌ ERROR")
        print(f"{str(e)}")
        logger.error(f"Critical error: {e}", exc_info=True)

if __name__ == "__main__":
    main()