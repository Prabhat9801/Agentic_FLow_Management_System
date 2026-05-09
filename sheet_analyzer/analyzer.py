import os
import json
import re
import sys
import argparse
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from openai import OpenAI

# Fix Windows encoding for emojis
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except (AttributeError, Exception):
        pass

# Load environment
load_dotenv()

class SheetAnalyzer:
    def __init__(self):
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o")
        self.sa_file = os.getenv("SERVICE_ACCOUNT_FILE", "service_account.json")
        
        if not self.openai_key:
            raise ValueError("OPENAI_API_KEY not found in .env")
            
        self.client = OpenAI(api_key=self.openai_key)
        self.sheets_service = self._init_google_service()

    def _init_google_service(self):
        """Initialize Google Sheets service with service account"""
        scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
        if not os.path.exists(self.sa_file):
            raise FileNotFoundError(f"Service account file {self.sa_file} not found")
            
        creds = service_account.Credentials.from_service_account_file(
            self.sa_file, scopes=scopes
        )
        return build('sheets', 'v4', credentials=creds)

    def extract_id(self, url: str) -> str:
        """Extract Spreadsheet ID from URL"""
        match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
        if not match:
            raise ValueError("Invalid Google Sheet URL")
        return match.group(1)

    def get_spreadsheet_data(self, spreadsheet_id: str) -> Dict[str, Any]:
        """Fetch all metadata, headers, and formulas from the spreadsheet"""
        print(f"🔍 Fetching spreadsheet metadata for: {spreadsheet_id}")
        
        # Get spreadsheet metadata
        spreadsheet = self.sheets_service.spreadsheets().get(
            spreadsheetId=spreadsheet_id,
            includeGridData=True
        ).execute()

        system_name = spreadsheet.get('properties', {}).get('title', 'Unknown System')
        sheets_data = []

        for sheet in spreadsheet.get('sheets', []):
            sheet_name = sheet['properties']['title']
            print(f"📖 Processing sheet: {sheet_name}")
            
            grid_data = sheet.get('data', [])
            if not grid_data:
                continue

            # Process rows to find headers and formulas
            # We usually look at the first 10 rows for headers and logic patterns
            rows = grid_data[0].get('rowData', [])
            
            # Extract Headers (usually row 1 or row 6 in FMS systems)
            # In FMS Row 6 is often the header if stages exist
            header_row_idx = 0
            if len(rows) >= 6:
                # Simple check: if Row 6 has more values than Row 1, it might be the header
                row1_vals = len([c for c in rows[0].get('values', []) if c.get('formattedValue')])
                row6_vals = len([c for c in rows[5].get('values', []) if c.get('formattedValue')])
                if row6_vals > row1_vals:
                    header_row_idx = 5

            headers = []
            if header_row_idx < len(rows):
                header_row = rows[header_row_idx].get('values', [])
                for i, cell in enumerate(header_row):
                    val = cell.get('formattedValue', f"Column_{i}")
                    headers.append(val)

            # Extract Formulas and Patterns
            formulas = []
            for r_idx, row in enumerate(rows):
                cells = row.get('values', [])
                for c_idx, cell in enumerate(cells):
                    formula = cell.get('userEnteredValue', {}).get('formulaValue')
                    if formula:
                        col_name = headers[c_idx] if c_idx < len(headers) else f"Col_{c_idx}"
                        formulas.append({
                            "column": col_name,
                            "row": r_idx + 1,
                            "formula": formula,
                            "description": cell.get('formattedValue', "")
                        })

            sheets_data.append({
                "sheet_name": sheet_name,
                "headers": headers,
                "formulas": formulas[:20], # Sample top formulas to avoid huge payload
                "total_rows": len(rows),
                "total_cols": len(headers)
            })

        return {
            "system_name": system_name,
            "spreadsheet_id": spreadsheet_id,
            "sheets": sheets_data
        }

    def analyze_with_ai(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Use OpenAI to analyze the flow and schema based on raw data"""
        print("🤖 Analyzing system flow with AI...")
        
        prompt = f"""
        Analyze the following Google Sheet structure and formulas to determine the system's schema, logic, and workflow.
        
        System Name: {raw_data['system_name']}
        
        Raw Structure:
        {json.dumps(raw_data['sheets'], indent=2)}
        
        Task:
        1. Identify the "Workflow Stages" if any (e.g., Stage 1, Stage 2).
        2. Explain the "Flow": How data moves from one sheet to another or across columns.
        3. Explain the "Formula Logic": What are the key calculations?
        4. Provide a "Schema Summary" for each sheet.
        
        Return the result as a detailed JSON object.
        """

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a professional systems architect and data analyst."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )

        analysis = json.loads(response.choices[0].message.content)
        return analysis

    def run(self, url: str):
        try:
            spreadsheet_id = self.extract_id(url)
            raw_data = self.get_spreadsheet_data(spreadsheet_id)
            ai_analysis = self.analyze_with_ai(raw_data)
            
            final_report = {
                "metadata": {
                    "analyzed_at": datetime.now().isoformat(),
                    "system_name": raw_data["system_name"],
                    "spreadsheet_id": raw_data["spreadsheet_id"],
                    "spreadsheet_url": url
                },
                "raw_structure": raw_data["sheets"],
                "intelligent_analysis": ai_analysis
            }
            
            output_file = "analysis_report.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(final_report, f, indent=2)
            
            print(f"\n✅ Analysis complete! Report saved to: {output_file}")
            return final_report
            
        except Exception as e:
            print(f"❌ Error during analysis: {e}")
            sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Google Sheet Analyzer")
    parser.add_argument("url", help="Google Sheet URL to analyze")
    args = parser.parse_args()
    
    analyzer = SheetAnalyzer()
    analyzer.run(args.url)
