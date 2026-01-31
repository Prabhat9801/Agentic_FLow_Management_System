import os
import json
import re
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, TypedDict
from dotenv import load_dotenv

from pydantic import BaseModel

from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# =====================================================
# ENV
# =====================================================
load_dotenv()

# =====================================================
# LLM (GROQ + LLAMA)
# =====================================================
llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0
)

# =====================================================
# GOOGLE AUTH (OAUTH)
# =====================================================
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets"
]

def get_google_services():
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "client_secret_338288800367-8ts74qb6m95tasp9ikpgfr39klkn97pk.apps.googleusercontent.com.json",
                SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open("token.json", "w") as f:
            f.write(creds.to_json())

    drive = build("drive", "v3", credentials=creds)
    sheets = build("sheets", "v4", credentials=creds)

    return drive, sheets

# =====================================================
# SCHEMAS
# =====================================================
class ColumnInfo(BaseModel):
    name: str
    type: str | None = None
    description: str | None = None

class SheetSchema(BaseModel):
    name: str
    columns: List[ColumnInfo | str]  # Accept both detailed and simple formats
    
    def get_column_names(self) -> List[str]:
        """Extract column names from columns list."""
        names = []
        for col in self.columns:
            if isinstance(col, str):
                names.append(col)
            elif isinstance(col, dict):
                names.append(col.get('name', col))
            else:
                names.append(col.name)
        return names

class FlowSchema(BaseModel):
    system_name: str
    sheets: List[SheetSchema]

class FormulaRule(BaseModel):
    sheet: str
    target_column: str
    start_row: int = 2
    formula: str
    description: str

class FormulaPlan(BaseModel):
    formulas: List[FormulaRule]

# =====================================================
# HELPER FUNCTIONS
# =====================================================
def strip_markdown_json(content: str) -> str:
    """Strip markdown code fences and extract only valid JSON from LLM response."""
    content = content.strip()
    
    # Remove markdown code fences
    if content.startswith("```"):
        # Find the first newline after the opening ```
        first_newline = content.find("\n")
        if first_newline != -1:
            content = content[first_newline + 1:]
        # Find and remove the closing ```
        closing_fence = content.find("```")
        if closing_fence != -1:
            content = content[:closing_fence]
    
    content = content.strip()
    
    # Find the actual JSON object boundaries
    # Look for the first { and the matching closing }
    start_idx = content.find("{")
    if start_idx == -1:
        return content
    
    # Count braces to find the matching closing brace
    brace_count = 0
    end_idx = -1
    for i in range(start_idx, len(content)):
        if content[i] == "{":
            brace_count += 1
        elif content[i] == "}":
            brace_count -= 1
            if brace_count == 0:
                end_idx = i + 1
                break
    
    if end_idx != -1:
        return content[start_idx:end_idx]
    
    return content

def create_project_folder(prompt: str) -> Path:
    """Create a project folder with timestamp and sanitized prompt name."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Sanitize prompt for folder name
    sanitized = re.sub(r'[^\w\s-]', '', prompt)[:50]  # Max 50 chars
    sanitized = re.sub(r'[-\s]+', '_', sanitized).strip('_')
    
    folder_name = f"{timestamp}_{sanitized}"
    folder_path = Path("projects") / folder_name
    folder_path.mkdir(parents=True, exist_ok=True)
    
    return folder_path

def save_metadata(folder: Path, prompt: str, spreadsheet_id: str, flow: FlowSchema):
    """Save project metadata."""
    metadata = {
        "prompt": prompt,
        "timestamp": datetime.now().isoformat(),
        "spreadsheet_id": spreadsheet_id,
        "spreadsheet_url": f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}",
        "system_name": flow.system_name,
        "total_sheets": len(flow.sheets),
        "sheets": [
            {
                "name": sheet.name,
                "columns": sheet.get_column_names()
            }
            for sheet in flow.sheets
        ]
    }
    
    with open(folder / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    
    return metadata

def generate_documentation(folder: Path, prompt: str, flow: FlowSchema, formulas: FormulaPlan, spreadsheet_id: str):
    """Generate comprehensive documentation in markdown."""
    doc = f"""# {flow.system_name}

## Project Information
- **Prompt**: {prompt}
- **Created**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- **Spreadsheet ID**: `{spreadsheet_id}`
- **Spreadsheet URL**: [Open in Google Sheets](https://docs.google.com/spreadsheets/d/{spreadsheet_id})

## System Architecture

### Overview
This system consists of {len(flow.sheets)} interconnected Google Sheets designed to manage the workflow from {prompt}.

### Sheets Structure

"""
    
    # Document each sheet
    for i, sheet in enumerate(flow.sheets, 1):
        doc += f"#### {i}. {sheet.name}\n\n"
        doc += "| Column Name | Type | Description |\n"
        doc += "|------------|------|-------------|\n"
        
        for col in sheet.columns:
            if isinstance(col, str):
                doc += f"| {col} | auto | - |\n"
            else:
                doc += f"| {col.name} | {col.type or 'auto'} | {col.description or '-'} |\n"
        
        doc += "\n"
    
    # Document formulas
    if formulas.formulas:
        doc += "## Formulas and Automation\n\n"
        
        for i, formula in enumerate(formulas.formulas, 1):
            doc += f"### {i}. {formula.description}\n\n"
            doc += f"- **Sheet**: {formula.sheet}\n"
            doc += f"- **Column**: {formula.target_column}\n"
            doc += f"- **Starting Row**: {formula.start_row}\n"
            doc += f"- **Formula**: `{formula.formula}`\n\n"
    
    # Document relationships
    doc += "## Sheet Relationships\n\n"
    doc += "```\n"
    for sheet in flow.sheets:
        doc += f"{sheet.name}\n"
        cols = sheet.get_column_names()
        for col in cols:
            if "ID" in col:
                doc += f"  ├─ {col} (Potential relationship key)\n"
    doc += "```\n\n"
    
    # Add file structure
    doc += "## Project Files\n\n"
    doc += "```\n"
    doc += f"projects/{folder.name}/\n"
    doc += "├── README.md              # This file\n"
    doc += "├── metadata.json          # Project metadata\n"
    doc += "├── flow_structure.json    # Complete sheet structure\n"
    doc += "├── formula_plan.json      # Formula definitions\n"
    doc += "└── schema.json            # Raw schema data\n"
    doc += "```\n\n"
    
    doc += "## How to Use\n\n"
    doc += "1. Open the Google Sheet using the URL above\n"
    doc += "2. Review the structure and formulas\n"
    doc += "3. Start entering data into the appropriate sheets\n"
    doc += "4. Formulas will automatically calculate based on your input\n\n"
    
    doc += "---\n"
    doc += "*Generated by Google Sheets Automation Agent*\n"
    
    with open(folder / "README.md", "w", encoding="utf-8") as f:
        f.write(doc)
    
    print(f"\n   ✓ Documentation generated: README.md")

# =====================================================
# LANGGRAPH STATE
# =====================================================
class AgentState(TypedDict):
    prompt: str
    project_folder: Path | None
    flow: FlowSchema | None
    formulas: FormulaPlan | None

# =====================================================
# AGENT 1 — STRUCTURE AGENT
# =====================================================
def structure_agent(state: AgentState):
    print("\n" + "="*60)
    print("📋 STEP 1: STRUCTURE AGENT")
    print("="*60)
    print(f"\n📝 Input Prompt: {state['prompt']}")
    
    prompt = f"""
You are a business workflow architect.

Create a Google Sheets structure for:
{state['prompt']}

Return ONLY valid JSON:
{{
  "system_name": "",
  "sheets": [
    {{
      "name": "",
      "columns": []
    }}
  ]
}}
"""
    print("\n🤖 Calling LLM...")
    response = llm.invoke(prompt)
    
    print("\n📥 Raw LLM Response:")
    print("-" * 60)
    print(response.content[:500] + "..." if len(response.content) > 500 else response.content)
    print("-" * 60)
    
    cleaned_content = strip_markdown_json(response.content)
    print("\n🧹 Cleaned JSON:")
    print("-" * 60)
    print(cleaned_content[:500] + "..." if len(cleaned_content) > 500 else cleaned_content)
    print("-" * 60)
    
    flow = FlowSchema.model_validate_json(cleaned_content)
    
    # Save to JSON file in project folder
    if state.get('project_folder'):
        output_file = state['project_folder'] / "flow_structure.json"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(flow.model_dump_json(indent=2))
        print(f"\n💾 Structure saved to: {output_file}")
    
    print("\n✅ Structure Generated:")
    print(f"   System Name: {flow.system_name}")
    print(f"   Number of Sheets: {len(flow.sheets)}")
    for i, sheet in enumerate(flow.sheets, 1):
        print(f"   {i}. {sheet.name} ({len(sheet.columns)} columns)")
        for col in sheet.columns:
            if isinstance(col, str):
                print(f"      - {col}")
            else:
                print(f"      - {col.name} ({col.type if col.type else 'auto'})")
    
    return {"flow": flow}

# =====================================================
# AGENT 2 — FORMULA AGENT
# =====================================================
def formula_agent(state: AgentState):
    print("\n" + "="*60)
    print("🔧 STEP 2: FORMULA AGENT")
    print("="*60)
    
    # Create a clear list of available columns for each sheet
    sheet_info = []
    for sheet in state['flow'].sheets:
        cols = sheet.get_column_names()
        sheet_info.append(f"- {sheet.name}: {', '.join(cols)}")
    
    available_columns = "\n".join(sheet_info)
    
    prompt = f"""
You are a spreadsheet formula architect.

Given this structure:
{state['flow'].model_dump()}

AVAILABLE COLUMNS BY SHEET:
{available_columns}

IMPORTANT RULES:
1. Only create formulas for columns that ALREADY EXIST in the structure above
2. Do NOT create formulas for new columns that don't exist
3. Use simple Google Sheets formulas (avoid SUMIFS with sheet references)
4. Keep formulas simple and practical

Return ONLY valid JSON:
{{
  "formulas": [
    {{
      "sheet": "",
      "target_column": "",
      "start_row": 2,
      "formula": "",
      "description": ""
    }}
  ]
}}

If no formulas are needed, return: {{"formulas": []}}
"""
    print("\n🤖 Calling LLM for formulas...")
    response = llm.invoke(prompt)
    
    print("\n📥 Raw LLM Response:")
    print("-" * 60)
    print(response.content[:500] + "..." if len(response.content) > 500 else response.content)
    print("-" * 60)
    
    cleaned_content = strip_markdown_json(response.content)
    print("\n🧹 Cleaned JSON:")
    print("-" * 60)
    print(cleaned_content[:500] + "..." if len(cleaned_content) > 500 else cleaned_content)
    print("-" * 60)
    
    formulas = FormulaPlan.model_validate_json(cleaned_content)
    
    # Save to JSON file in project folder
    if state.get('project_folder'):
        output_file = state['project_folder'] / "formula_plan.json"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(formulas.model_dump_json(indent=2))
        print(f"\n💾 Formulas saved to: {output_file}")
    
    print("\n✅ Formulas Generated:")
    for i, formula in enumerate(formulas.formulas, 1):
        print(f"   {i}. {formula.sheet}.{formula.target_column}")
        print(f"      Formula: {formula.formula}")
        print(f"      Description: {formula.description}")
    
    return {"formulas": formulas}

# =====================================================
# UTILS
# =====================================================
def col_letter(index: int) -> str:
    result = ""
    while index:
        index, rem = divmod(index - 1, 26)
        result = chr(65 + rem) + result
    return result

def build_column_map(flow: FlowSchema):
    return {
        sheet.name: {
            col: col_letter(i + 1)
            for i, col in enumerate(sheet.get_column_names())
        }
        for sheet in flow.sheets
    }

def translate_formula(formula: str, col_map: dict, row: int):
    for col, letter in col_map.items():
        formula = re.sub(
            rf"\b{re.escape(col)}\b",
            f"{letter}{row}",
            formula
        )
    return formula

# =====================================================
# GOOGLE SHEETS EXECUTION
# =====================================================
def create_spreadsheet(drive, title: str) -> str:
    print(f"\n   Creating spreadsheet: {title}")
    file = drive.files().create(
        body={
            "name": title,
            "mimeType": "application/vnd.google-apps.spreadsheet"
        },
        fields="id"
    ).execute()
    print(f"   ✓ Spreadsheet created with ID: {file['id']}")
    return file["id"]

def add_sheets_and_headers(sheets, spreadsheet_id: str, flow: FlowSchema):
    requests = []

    for sheet in flow.sheets:
        requests.append({
            "addSheet": {
                "properties": {"title": sheet.name}
            }
        })

    print(f"\n   Creating {len(flow.sheets)} sheets...")
    sheets.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": requests}
    ).execute()
    print("   ✓ All sheets created")
    
    print("\n   Adding headers to sheets...")

    for sheet in flow.sheets:
        column_names = sheet.get_column_names()
        sheets.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet.name}!A1",
            valueInputOption="RAW",
            body={"values": [column_names]}
        ).execute()
        print(f"   ✓ Added headers for sheet: {sheet.name}")

def apply_formulas(sheets, spreadsheet_id: str, flow: FlowSchema, plan: FormulaPlan):
    if not plan.formulas:
        print("\n   ⚠️ No formulas to apply")
        return
        
    print(f"\n   Processing {len(plan.formulas)} formulas...")
    col_map = build_column_map(flow)

    for rule in plan.formulas:
        # Validate that the sheet exists
        if rule.sheet not in col_map:
            print(f"   ⚠️ Skipping formula: Sheet '{rule.sheet}' not found")
            continue
            
        # Validate that the target column exists
        if rule.target_column not in col_map[rule.sheet]:
            print(f"   ⚠️ Skipping formula: Column '{rule.target_column}' not found in sheet '{rule.sheet}'")
            print(f"      Available columns: {', '.join(col_map[rule.sheet].keys())}")
            continue
        
        target_col = col_map[rule.sheet][rule.target_column]
        formula = translate_formula(
            rule.formula,
            col_map[rule.sheet],
            rule.start_row
        )

        sheets.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{rule.sheet}!{target_col}{rule.start_row}",
            valueInputOption="USER_ENTERED",
            body={"values": [[formula]]}
        ).execute()

        print(f"   ✓ {rule.description}")

# =====================================================
# LANGGRAPH FLOW
# =====================================================
def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("structure", structure_agent)
    graph.add_node("formula", formula_agent)

    graph.set_entry_point("structure")
    graph.add_edge("structure", "formula")
    graph.add_edge("formula", END)

    return graph.compile()

# =====================================================
# MAIN
# =====================================================
def main():
    print("\n" + "="*60)
    print("🚀 GOOGLE SHEETS AUTOMATION WORKFLOW")
    print("="*60)
    
    graph = build_graph()

    state = graph.invoke({
        "prompt": "Order to payment system for grocery items",
        "flow": None,
        "formulas": None
    })

    print("\n" + "="*60)
    print("📋 STEP 3: CREATING GOOGLE SHEET")
    print("="*60)
    
    drive, sheets = get_google_services()

    print("\n📊 Creating Google Sheet...")
    spreadsheet_id = create_spreadsheet(drive, state["flow"].system_name)

    print("\n📑 Adding sheets and headers...")
    add_sheets_and_headers(sheets, spreadsheet_id, state["flow"])

    print("\n⚙️ Applying formulas...")
    apply_formulas(sheets, spreadsheet_id, state["flow"], state["formulas"])

    print("\n" + "="*60)
    print("✅ SYSTEM READY!")
    print("="*60)
    print(f"\n🔗 Spreadsheet URL:")
    print(f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
    print("\n💾 Generated Files:")
    print("   - flow_structure.json")
    print("   - formula_plan.json")
    print("\n" + "="*60)

if __name__ == "__main__":
    main()
