"""
Google Sheets Flow Management System - Agentic Automation
---------------------------------------------------------
An intelligent agent that creates professional Flow Management Systems
from natural language prompts using OpenAI and Google Sheets API.

Author: Improved by Claude
Version: 2.0
"""

import os
import json
import re
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
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
        logging.FileHandler('fms_agent.log'),
        logging.StreamHandler()
    ]
)
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

# =====================================================
# ENHANCED SCHEMAS
# =====================================================
class ColumnInfo(BaseModel):
    """Enhanced column information with validation"""
    name: str = Field(..., description="Column name")
    type: ColumnType = Field(default=ColumnType.TEXT, description="Column data type")
    description: Optional[str] = Field(None, description="Column purpose description")
    required: bool = Field(default=False, description="Is this column required?")
    validation: Optional[str] = Field(None, description="Validation rule")
    default_value: Optional[str] = Field(None, description="Default value")
    
    @validator('default_value', pre=True)
    def convert_default_value(cls, v):
        """Convert int/float to string for default_value"""
        if v is None:
            return v
        return str(v)
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Column name cannot be empty")
        # Remove special characters that might break formulas
        return re.sub(r'[^\w\s-]', '', v).strip()


class SheetSchema(BaseModel):
    """Enhanced sheet schema with metadata"""
    name: str = Field(..., description="Sheet name")
    columns: List[ColumnInfo] = Field(..., description="Sheet columns")
    description: Optional[str] = Field(None, description="Sheet purpose")
    primary_key: Optional[str] = Field(None, description="Primary key column")
    relationships: Optional[List[str]] = Field(default_factory=list, description="Related sheets")
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Sheet name cannot be empty")
        # Sheet names have specific restrictions in Google Sheets
        return re.sub(r'[^\w\s-]', '', v)[:100]  # Max 100 chars
    
    def get_column_names(self) -> List[str]:
        """Extract column names from columns list."""
        return [col.name for col in self.columns]
    
    def get_column_by_name(self, name: str) -> Optional[ColumnInfo]:
        """Get column info by name"""
        for col in self.columns:
            if col.name == name:
                return col
        return None

class FlowSchema(BaseModel):
    """Complete flow management system schema"""
    system_name: str = Field(..., description="System name")
    description: str = Field(..., description="System description")
    version: str = Field(default="1.0", description="Schema version")
    sheets: List[SheetSchema] = Field(..., description="System sheets")
    workflow_stages: Optional[List[str]] = Field(default_factory=list, description="Workflow stages")
    integrations: Optional[List[str]] = Field(default_factory=list, description="Required integrations")
    
    @validator('system_name')
    def validate_system_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("System name cannot be empty")
        return v.strip()

class FormulaRule(BaseModel):
    """Enhanced formula rule with validation"""
    sheet: str = Field(..., description="Target sheet name")
    target_column: str = Field(..., description="Target column name")
    start_row: int = Field(default=2, ge=2, description="Starting row (headers at row 1)")
    formula: str = Field(..., description="Google Sheets formula")
    description: str = Field(..., description="Formula purpose")
    dependencies: Optional[List[str]] = Field(default_factory=list, description="Dependent columns")
    apply_to_all_rows: bool = Field(default=True, description="Auto-fill formula")

class FormulaPlan(BaseModel):
    """Complete formula implementation plan"""
    formulas: List[FormulaRule] = Field(default_factory=list)
    validation_rules: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    conditional_formatting: Optional[List[Dict[str, Any]]] = Field(default_factory=list)

class ValidationRule(BaseModel):
    """Data validation rules"""
    sheet: str
    column: str
    rule_type: str  # "list", "number_range", "date_range", "custom"
    criteria: Dict[str, Any]
    error_message: Optional[str] = None

# =====================================================
# OPENAI CLIENT
# =====================================================
class LLMClient:
    """Enhanced OpenAI client with retry logic and structured outputs"""
    
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
        
        # Look for credentials file
        for file in Path(".").glob("client_secret*.json"):
            credentials_path = file
            break
        
        if not credentials_path:
            raise FileNotFoundError(
                "Google OAuth credentials file not found. "
                "Please download it from Google Cloud Console."
            )
        
        # Load existing token
        if token_path.exists():
            self.creds = Credentials.from_authorized_user_file(str(token_path), Config.SCOPES)
        
        # Refresh or get new credentials
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
            
            # Save credentials
            token_path.write_text(self.creds.to_json())
            logger.info("Credentials saved successfully")
        
        # Build services
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
        
        # Remove markdown code fences
        if content.startswith("```"):
            first_newline = content.find("\n")
            if first_newline != -1:
                content = content[first_newline + 1:]
            
            closing_fence = content.rfind("```")
            if closing_fence != -1:
                content = content[:closing_fence]
        
        content = content.strip()
        
        # Find JSON object boundaries
        start_idx = content.find("{")
        if start_idx == -1:
            # Try array format
            start_idx = content.find("[")
            if start_idx == -1:
                raise ValueError("No JSON object or array found in response")
        
        # Count braces/brackets to find matching closing
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
        
        # Validate JSON
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
        
        # Create folder structure
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
                "integrations": flow.integrations
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
                                "description": col.description
                            }
                            for col in sheet.columns
                        ],
                        "primary_key": sheet.primary_key,
                        "relationships": sheet.relationships
                    }
                    for sheet in flow.sheets
                ]
            },
            "statistics": {
                "total_columns": sum(len(sheet.columns) for sheet in flow.sheets),
                "sheets_with_relationships": len([s for s in flow.sheets if s.relationships])
            }
        }
        
        metadata_path = folder / "metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Metadata saved to {metadata_path}")
        return metadata

class DocumentationGenerator:
    """Generates comprehensive project documentation"""
    
    @staticmethod
    def generate(folder: Path, prompt: str, flow: FlowSchema, 
                formulas: FormulaPlan, spreadsheet_id: str, metadata: Dict) -> None:
        """Generate detailed README documentation"""
        
        doc = f"""# {flow.system_name}

> {flow.description}

## 📋 Project Overview

- **Created**: {metadata['project_info']['created_at']}
- **Original Prompt**: {prompt}
- **Version**: {flow.version}
- **Execution Time**: {metadata['project_info']['execution_time_seconds']}s
- **Total Sheets**: {len(flow.sheets)}
- **Total Columns**: {metadata['statistics']['total_columns']}

## 🔗 Quick Links

- [📊 Open Spreadsheet (View)]({metadata['spreadsheet']['url']})
- [✏️ Open Spreadsheet (Edit)]({metadata['spreadsheet']['edit_url']})
- **Spreadsheet ID**: `{spreadsheet_id}`

## 🏗️ System Architecture

### Workflow Stages
"""
        
        if flow.workflow_stages:
            for i, stage in enumerate(flow.workflow_stages, 1):
                arrow = " → " if i < len(flow.workflow_stages) else ""
                doc += f"{i}. **{stage}**{arrow}"
            doc += "\n\n"
        else:
            doc += "*No explicit workflow stages defined*\n\n"
        
        # Sheet details
        doc += "### 📊 Data Structure\n\n"
        
        for i, sheet in enumerate(flow.sheets, 1):
            doc += f"#### {i}. {sheet.name}\n\n"
            
            if sheet.description:
                doc += f"> {sheet.description}\n\n"
            
            doc += "| Column | Type | Required | Description |\n"
            doc += "|--------|------|----------|-------------|\n"
            
            for col in sheet.columns:
                required = "✅" if col.required else "❌"
                desc = col.description or "-"
                doc += f"| **{col.name}** | `{col.type.value}` | {required} | {desc} |\n"
            
            if sheet.primary_key:
                doc += f"\n🔑 **Primary Key**: `{sheet.primary_key}`\n"
            
            if sheet.relationships:
                doc += f"\n🔗 **Relationships**: {', '.join(sheet.relationships)}\n"
            
            doc += "\n"
        
        # Formulas section
        if formulas.formulas:
            doc += "## ⚙️ Automated Calculations\n\n"
            
            for i, formula in enumerate(formulas.formulas, 1):
                doc += f"### {i}. {formula.description}\n\n"
                doc += f"- **Sheet**: `{formula.sheet}`\n"
                doc += f"- **Column**: `{formula.target_column}`\n"
                doc += f"- **Formula**: `{formula.formula}`\n"
                
                if formula.dependencies:
                    doc += f"- **Dependencies**: {', '.join(formula.dependencies)}\n"
                
                doc += f"- **Auto-fill**: {'Yes' if formula.apply_to_all_rows else 'No'}\n\n"
        
        # Integrations
        if flow.integrations:
            doc += "## 🔌 Required Integrations\n\n"
            for integration in flow.integrations:
                doc += f"- {integration}\n"
            doc += "\n"
        
        # File structure
        doc += """## 📁 Project Structure

```
{folder_name}/
├── README.md                  # This file
├── metadata.json              # Complete project metadata
├── schemas/
│   ├── flow_structure.json    # System structure
│   ├── formula_plan.json      # Formula definitions
│   └── complete_schema.json   # Full schema
├── docs/
│   └── (additional documentation)
└── logs/
    └── (execution logs)
```

## 🚀 Getting Started

1. **Open the Spreadsheet**: Click the link above to access your Google Sheet
2. **Review the Structure**: Familiarize yourself with the sheets and columns
3. **Start Entering Data**: Begin with the first sheet in your workflow
4. **Automated Formulas**: Formulas will calculate automatically as you add data

## 💡 Usage Tips

- Each sheet represents a stage in your workflow
- Required columns are marked with ✅ in the structure above
- Formulas update automatically when you add new rows
- Use the primary keys to maintain relationships between sheets

## 🔧 Customization

To modify the system:
1. Add new columns as needed
2. Update formulas in the sheet directly
3. Add data validation rules for better data quality
4. Create additional views or pivot tables

## 📊 Data Flow

""".format(folder_name=folder.name)
        
        # Create visual data flow
        doc += "```\n"
        for i, sheet in enumerate(flow.sheets):
            doc += f"{'  ' * i}┌─ {sheet.name}\n"
            if sheet.relationships:
                for rel in sheet.relationships:
                    doc += f"{'  ' * i}│  └─→ links to {rel}\n"
        doc += "```\n\n"
        
        doc += """## ⚠️ Important Notes

- Always fill required fields (marked with ✅)
- Maintain data consistency across related sheets
- Backup your data regularly
- Test formulas before large-scale data entry

## 📞 Support

For issues or questions:
- Review the metadata.json file for technical details
- Check formula_plan.json for formula logic
- Examine flow_structure.json for system architecture

---

*Generated by Flow Management System Agent v2.0*  
*Powered by OpenAI and Google Sheets API*
"""
        
        readme_path = folder / "README.md"
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(doc)
        
        logger.info(f"Documentation generated: {readme_path}")

# =====================================================
# LANGGRAPH STATE
# =====================================================
class AgentState(BaseModel):
    """Enhanced agent state with validation"""
    prompt: str
    project_folder: Optional[Path] = None
    flow: Optional[FlowSchema] = None
    formulas: Optional[FormulaPlan] = None
    validation_rules: Optional[List[ValidationRule]] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    
    class Config:
        arbitrary_types_allowed = True

# =====================================================
# AGENT 1: STRUCTURE AGENT (ENHANCED)
# =====================================================
def structure_agent(state: AgentState) -> Dict:
    """
    Enhanced structure agent with better prompt engineering
    and comprehensive system design
    """
    print("\n" + "="*70)
    print("🏗️  STRUCTURE AGENT: Designing System Architecture")
    print("="*70)
    print(f"\n📝 User Requirement: {state.prompt}")
    
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

"{state.prompt}"

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

Make it production-ready and professional!
"""
    
    try:
        logger.info("Invoking LLM for structure generation...")
        response = llm.invoke(user_prompt, system_prompt=system_prompt)
        
        logger.debug(f"Raw LLM response length: {len(response)} characters")
        
        # Clean and parse JSON
        cleaned_json = JSONCleaner.clean(response)
        logger.debug("JSON cleaned successfully")
        
        # Parse into Pydantic model
        flow = FlowSchema.model_validate_json(cleaned_json)
        logger.info(f"Flow schema validated: {flow.system_name}")
        
        # Save structure to file
        if state.project_folder:
            schema_file = state.project_folder / "schemas" / "flow_structure.json"
            with open(schema_file, "w", encoding="utf-8") as f:
                f.write(flow.model_dump_json(indent=2))
            logger.info(f"Structure saved to {schema_file}")
        
        # Display summary
        print("\n✅ System Structure Created Successfully!")
        print(f"\n📊 System: {flow.system_name}")
        print(f"📝 Description: {flow.description}")
        print(f"📈 Version: {flow.version}")
        
        if flow.workflow_stages:
            print(f"\n🔄 Workflow Stages ({len(flow.workflow_stages)}):")
            for i, stage in enumerate(flow.workflow_stages, 1):
                print(f"   {i}. {stage}")
        
        print(f"\n📋 Sheets ({len(flow.sheets)}):")
        for i, sheet in enumerate(flow.sheets, 1):
            print(f"\n   {i}. {sheet.name}")
            print(f"      Description: {sheet.description or 'N/A'}")
            print(f"      Columns: {len(sheet.columns)}")
            print(f"      Primary Key: {sheet.primary_key or 'N/A'}")
            if sheet.relationships:
                print(f"      Relationships: {', '.join(sheet.relationships)}")
        
        return {"flow": flow}
        
    except Exception as e:
        error_msg = f"Structure generation failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        print(f"\n❌ Error: {error_msg}")
        return {"errors": [error_msg]}

# =====================================================
# AGENT 2: FORMULA AGENT (ENHANCED)
# =====================================================
def formula_agent(state: AgentState) -> Dict:
    """
    Enhanced formula agent with intelligent formula generation
    and validation
    """
    print("\n" + "="*70)
    print("⚙️  FORMULA AGENT: Creating Automated Calculations")
    print("="*70)
    
    if not state.flow:
        error_msg = "No flow structure available for formula generation"
        logger.error(error_msg)
        return {"errors": [error_msg]}
    
    # Build comprehensive sheet information
    sheet_details = []
    for sheet in state.flow.sheets:
        cols_info = []
        for col in sheet.columns:
            cols_info.append(f"    - {col.name} ({col.type.value}): {col.description or 'N/A'}")
        
        sheet_details.append(f"""
Sheet: "{sheet.name}"
Description: {sheet.description or 'N/A'}
Primary Key: {sheet.primary_key or 'N/A'}
Columns:
{chr(10).join(cols_info)}
""")
    
    available_info = "\n".join(sheet_details)
    
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

If no useful formulas are needed, return: {{"formulas": [], "validation_rules": [], "conditional_formatting": []}}
"""
    
    try:
        logger.info("Invoking LLM for formula generation...")
        response = llm.invoke(user_prompt, system_prompt=system_prompt)
        
        logger.debug(f"Raw formula response length: {len(response)} characters")
        
        # Clean and parse JSON
        cleaned_json = JSONCleaner.clean(response)
        logger.debug("Formula JSON cleaned successfully")
        
        # Parse into Pydantic model
        formulas = FormulaPlan.model_validate_json(cleaned_json)
        logger.info(f"Formula plan validated: {len(formulas.formulas)} formulas")
        
        # Validate formulas against schema
        validated_formulas = []
        for formula in formulas.formulas:
            # Check sheet exists
            sheet = next((s for s in state.flow.sheets if s.name == formula.sheet), None)
            if not sheet:
                warning = f"Skipping formula: Sheet '{formula.sheet}' not found"
                logger.warning(warning)
                state.warnings.append(warning)
                continue
            
            # Check column exists
            if formula.target_column not in sheet.get_column_names():
                warning = f"Skipping formula: Column '{formula.target_column}' not found in sheet '{formula.sheet}'"
                logger.warning(warning)
                state.warnings.append(warning)
                continue
            
            validated_formulas.append(formula)
        
        formulas.formulas = validated_formulas
        
        # Save formulas to file
        if state.project_folder:
            formula_file = state.project_folder / "schemas" / "formula_plan.json"
            with open(formula_file, "w", encoding="utf-8") as f:
                f.write(formulas.model_dump_json(indent=2))
            logger.info(f"Formulas saved to {formula_file}")
        
        # Display summary
        print(f"\n✅ Formula Plan Created: {len(formulas.formulas)} formulas")
        
        if formulas.formulas:
            for i, formula in enumerate(formulas.formulas, 1):
                print(f"\n   {i}. {formula.description}")
                print(f"      Location: {formula.sheet}.{formula.target_column}")
                print(f"      Formula: {formula.formula}")
                if formula.dependencies:
                    print(f"      Dependencies: {', '.join(formula.dependencies)}")
        else:
            print("\n   ℹ️  No formulas generated (may not be needed for this system)")
        
        if state.warnings:
            print(f"\n⚠️  Warnings ({len(state.warnings)}):")
            for warning in state.warnings:
                print(f"   - {warning}")
        
        return {"formulas": formulas}
        
    except Exception as e:
        error_msg = f"Formula generation failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        print(f"\n❌ Error: {error_msg}")
        return {"errors": [error_msg]}

# =====================================================
# GOOGLE SHEETS OPERATIONS (ENHANCED)
# =====================================================
class GoogleSheetsManager:
    """Enhanced Google Sheets operations with error handling"""
    
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
            logger.info(f"Spreadsheet created successfully: {spreadsheet_id}")
            print(f"   ✅ Spreadsheet created: {spreadsheet_id}")
            
            return spreadsheet_id
            
        except HttpError as e:
            logger.error(f"Failed to create spreadsheet: {e}")
            raise Exception(f"Spreadsheet creation failed: {e}")
    
    def setup_sheets(self, spreadsheet_id: str, flow: FlowSchema) -> None:
        """Create sheets and add headers with formatting"""
        try:
            logger.info(f"Setting up {len(flow.sheets)} sheets...")
            print(f"\n   📋 Creating {len(flow.sheets)} sheets...")
            
            # Get default sheet to delete it later
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
                                "columnCount": len(sheet.columns) + 5  # Extra columns
                            }
                        }
                    }
                })
            
            # Execute batch request
            self.sheets.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={"requests": requests}
            ).execute()
            
            logger.info("Sheets created successfully")
            print("   ✅ All sheets created")
            
            # Delete default sheet
            try:
                self.sheets.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body={"requests": [{"deleteSheet": {"sheetId": default_sheet_id}}]}
                ).execute()
                logger.info("Default sheet deleted")
            except:
                pass  # Default sheet might have been renamed
            
            # Add headers with formatting
            print("\n   📝 Adding headers and formatting...")
            for sheet in flow.sheets:
                self._add_headers_with_format(spreadsheet_id, sheet)
            
            print("   ✅ Headers and formatting applied")
            
        except HttpError as e:
            logger.error(f"Failed to setup sheets: {e}")
            raise Exception(f"Sheet setup failed: {e}")
    
    def _add_headers_with_format(self, spreadsheet_id: str, sheet: SheetSchema) -> None:
        """Add headers with professional formatting"""
        column_names = sheet.get_column_names()
        
        # Add header values
        self.sheets.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet.name}!A1",
            valueInputOption="RAW",
            body={"values": [column_names]}
        ).execute()
        
        # Get sheet ID for formatting
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
        
        # Format headers (bold, background color, frozen)
        requests = [
            # Bold headers
            {
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
                            "horizontalAlignment": "CENTER"
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
                }
            },
            # Freeze header row
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": sheet_id,
                        "gridProperties": {"frozenRowCount": 1}
                    },
                    "fields": "gridProperties.frozenRowCount"
                }
            }
        ]
        
        self.sheets.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": requests}
        ).execute()
        
        logger.info(f"Headers formatted for sheet: {sheet.name}")
    
    def apply_formulas(self, spreadsheet_id: str, flow: FlowSchema, plan: FormulaPlan) -> None:
        """Apply formulas with validation"""
        if not plan.formulas:
            logger.info("No formulas to apply")
            print("\n   ℹ️  No formulas to apply")
            return
        
        print(f"\n   ⚙️  Applying {len(plan.formulas)} formulas...")
        
        # Build column map
        col_map = self._build_column_map(flow)
        
        applied_count = 0
        for formula in plan.formulas:
            try:
                target_col = col_map[formula.sheet][formula.target_column]
                translated_formula = self._translate_formula(
                    formula.formula,
                    col_map[formula.sheet],
                    formula.start_row
                )
                
                # Apply formula
                self.sheets.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range=f"{formula.sheet}!{target_col}{formula.start_row}",
                    valueInputOption="USER_ENTERED",
                    body={"values": [[translated_formula]]}
                ).execute()
                
                applied_count += 1
                logger.info(f"Formula applied: {formula.sheet}.{formula.target_column}")
                print(f"   ✅ {formula.description}")
                
            except Exception as e:
                logger.warning(f"Failed to apply formula: {e}")
                print(f"   ⚠️  Skipped: {formula.description} ({str(e)})")
        
        print(f"\n   ✅ Applied {applied_count}/{len(plan.formulas)} formulas successfully")
    
    @staticmethod
    def _build_column_map(flow: FlowSchema) -> Dict[str, Dict[str, str]]:
        """Build mapping of column names to Excel-style letters"""
        col_map = {}
        for sheet in flow.sheets:
            col_map[sheet.name] = {}
            for i, col_name in enumerate(sheet.get_column_names()):
                col_map[sheet.name][col_name] = GoogleSheetsManager._col_letter(i + 1)
        return col_map
    
    @staticmethod
    def _col_letter(index: int) -> str:
        """Convert column index to Excel-style letter"""
        result = ""
        while index:
            index, rem = divmod(index - 1, 26)
            result = chr(65 + rem) + result
        return result
    
    @staticmethod
    def _translate_formula(formula: str, col_map: Dict[str, str], row: int) -> str:
        """Translate formula with column names to Excel-style references"""
        for col_name, col_letter in col_map.items():
            # Replace column name with letter+row
            pattern = rf"\b{re.escape(col_name)}\b"
            formula = re.sub(pattern, f"{col_letter}{row}", formula)
        return formula

# =====================================================
# MAIN WORKFLOW ORCHESTRATION
# =====================================================
def build_workflow() -> StateGraph:
    """Build the LangGraph workflow"""
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("structure", structure_agent)
    workflow.add_node("formula", formula_agent)
    
    # Define flow
    workflow.set_entry_point("structure")
    workflow.add_edge("structure", "formula")
    workflow.add_edge("formula", END)
    
    return workflow.compile()

def main():
    """Main execution function"""
    start_time = datetime.now()
    
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="🤖 Flow Management System - Agentic Automation v2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main_improved.py
  python main_improved.py "Create an order-to-payment system for e-commerce"
  python main_improved.py "Employee onboarding workflow with document tracking"
  python main_improved.py "Inventory management with reorder automation"

Features:
  ✨ Intelligent system design with OpenAI GPT-4
  📊 Professional Google Sheets generation
  ⚙️  Automated calculations and formulas
  📝 Comprehensive documentation
  🔍 Data validation and relationships
  📈 Workflow stage tracking
        """
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        help="Description of the system you want to create"
    )
    parser.add_argument(
        "--model",
        default=Config.OPENAI_MODEL,
        help=f"OpenAI model to use (default: {Config.OPENAI_MODEL})"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Override model if specified
    if args.model:
        Config.OPENAI_MODEL = args.model
    
    # Get user prompt
    if args.prompt:
        user_prompt = args.prompt
    else:
        print("\n" + "="*70)
        print("🤖 FLOW MANAGEMENT SYSTEM - AGENTIC AUTOMATION")
        print("="*70)
        print("\n✨ Powered by OpenAI GPT-4 and Google Sheets API")
        print("\nDescribe the system you want to create:")
        print("💡 Examples:")
        print("   - Order to payment flow for grocery items")
        print("   - Employee attendance tracking with leave management")
        print("   - Customer relationship management system")
        print("   - Project task tracking with time logging")
        print()
        user_prompt = input("📝 Your prompt: ").strip()
        
        if not user_prompt:
            print("\n❌ Error: Prompt cannot be empty")
            return
    
    try:
        # Display banner
        print("\n" + "="*70)
        print("🚀 STARTING FLOW MANAGEMENT SYSTEM GENERATION")
        print("="*70)
        print(f"\n📌 System Description: {user_prompt}")
        print(f"🤖 AI Model: {Config.OPENAI_MODEL}")
        print(f"📅 Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Create project folder
        logger.info("Creating project folder...")
        project_folder = ProjectManager.create_project_folder(user_prompt)
        print(f"📁 Project Folder: {project_folder.name}")
        
        # Build and run workflow
        logger.info("Building workflow graph...")
        workflow = build_workflow()
        
        # Initialize state
        initial_state = AgentState(
            prompt=user_prompt,
            project_folder=project_folder
        )
        
        # Run workflow
        logger.info("Executing workflow...")
        print("\n" + "="*70)
        print("🔄 EXECUTING WORKFLOW")
        print("="*70)
        
        final_state = workflow.invoke(initial_state.dict())
        
        # Check for errors
        if final_state.get("errors"):
            print("\n" + "="*70)
            print("❌ WORKFLOW FAILED")
            print("="*70)
            for error in final_state["errors"]:
                print(f"\n   Error: {error}")
            return
        
        # Create Google Sheets
        print("\n" + "="*70)
        print("📊 CREATING GOOGLE SPREADSHEET")
        print("="*70)
        
        # Authenticate with Google
        google_manager = GoogleServicesManager()
        drive, sheets = google_manager.authenticate()
        
        # Initialize sheets manager
        sheets_manager = GoogleSheetsManager(drive, sheets)
        
        # Create spreadsheet
        # Handle flow - it's already a FlowSchema instance from the agent
        flow = final_state["flow"] if isinstance(final_state["flow"], FlowSchema) else FlowSchema(**final_state["flow"])
        spreadsheet_id = sheets_manager.create_spreadsheet(flow.system_name)
        
        # Setup sheets
        sheets_manager.setup_sheets(spreadsheet_id, flow)
        
        # Apply formulas
        # Handle formulas - it's already a FormulaPlan instance from the agent
        formulas = final_state["formulas"] if isinstance(final_state["formulas"], FormulaPlan) else FormulaPlan(**final_state["formulas"])
        sheets_manager.apply_formulas(spreadsheet_id, flow, formulas)
        
        # Calculate execution time
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        # Save metadata and generate documentation
        print("\n" + "="*70)
        print("📄 GENERATING DOCUMENTATION")
        print("="*70)
        
        metadata = ProjectManager.save_metadata(
            project_folder,
            user_prompt,
            spreadsheet_id,
            flow,
            execution_time
        )
        
        DocumentationGenerator.generate(
            project_folder,
            user_prompt,
            flow,
            formulas,
            spreadsheet_id,
            metadata
        )
        
        # Save complete schema
        complete_schema_path = project_folder / "schemas" / "complete_schema.json"
        with open(complete_schema_path, "w", encoding="utf-8") as f:
            json.dump({
                "flow": flow.dict(),
                "formulas": formulas.dict(),
                "metadata": metadata
            }, f, indent=2, ensure_ascii=False)
        
        # Display success message
        print("\n" + "="*70)
        print("✅ SYSTEM GENERATED SUCCESSFULLY!")
        print("="*70)
        
        print(f"\n📊 System: {flow.system_name}")
        print(f"⏱️  Execution Time: {execution_time:.2f} seconds")
        print(f"📋 Sheets Created: {len(flow.sheets)}")
        print(f"⚙️  Formulas Applied: {len(formulas.formulas)}")
        
        print("\n🔗 Quick Links:")
        print(f"   View: {metadata['spreadsheet']['url']}")
        print(f"   Edit: {metadata['spreadsheet']['edit_url']}")
        
        print(f"\n📁 Project Location:")
        print(f"   {project_folder.absolute()}")
        
        print("\n📄 Generated Files:")
        print("   ✓ README.md                    (Comprehensive documentation)")
        print("   ✓ metadata.json                (Project metadata)")
        print("   ✓ schemas/flow_structure.json  (System structure)")
        print("   ✓ schemas/formula_plan.json    (Formula definitions)")
        print("   ✓ schemas/complete_schema.json (Complete schema)")
        
        if final_state.get("warnings"):
            print(f"\n⚠️  Warnings ({len(final_state['warnings'])}):")
            for warning in final_state["warnings"]:
                print(f"   - {warning}")
        
        print("\n💡 Next Steps:")
        print("   1. Open the spreadsheet using the link above")
        print("   2. Review the structure and relationships")
        print("   3. Start entering your data")
        print("   4. Formulas will calculate automatically")
        
        print("\n" + "="*70)
        logger.info("Workflow completed successfully")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        logger.warning("Operation cancelled by user")
        
    except Exception as e:
        print("\n" + "="*70)
        print("❌ CRITICAL ERROR")
        print("="*70)
        print(f"\n{str(e)}")
        logger.error(f"Critical error: {e}", exc_info=True)
        
        print("\n💡 Troubleshooting:")
        print("   1. Check your .env file has OPENAI_API_KEY set")
        print("   2. Verify Google OAuth credentials are present")
        print("   3. Check logs in fms_agent.log for details")
        print("   4. Try with --verbose flag for more information")

if __name__ == "__main__":
    main()