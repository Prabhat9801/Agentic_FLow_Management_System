# Advanced CRM Management System

> A comprehensive CRM system with lead scoring, an opportunity pipeline, and revenue forecasting capabilities.

## 📋 Project Overview

- **Created**: 2026-01-31T10:40:35.677913
- **Original Prompt**: Build CRM with lead scoring, opportunity pipeline, and revenue forecasting
- **Version**: 1.0
- **Execution Time**: 49.74s
- **Total Sheets**: 5
- **Total Columns**: 22

## 🔗 Quick Links

- [📊 Open Spreadsheet (View)](https://docs.google.com/spreadsheets/d/1qVZEwBYHdRxBzXQhxND8bEJYRY7S44ceikSADbXO_bI)
- [✏️ Open Spreadsheet (Edit)](https://docs.google.com/spreadsheets/d/1qVZEwBYHdRxBzXQhxND8bEJYRY7S44ceikSADbXO_bI/edit)
- **Spreadsheet ID**: `1qVZEwBYHdRxBzXQhxND8bEJYRY7S44ceikSADbXO_bI`

## 🏗️ System Architecture

### Workflow Stages
1. **Lead Capture** → 2. **Lead Qualification** → 3. **Opportunity Tracking** → 4. **Revenue Forecasting** → 5. **Reporting**

### 📊 Data Structure

#### 1. Leads

> This sheet captures and manages potential customer leads.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| **lead_id** | `text` | ✅ | Unique identifier for each lead |
| **lead_name** | `text` | ✅ | Full name of the lead |
| **email** | `email` | ✅ | Email address of the lead |
| **phone_number** | `text` | ❌ | Contact number of the lead |
| **created_date** | `date` | ✅ | Date when the lead was added |
| **status** | `dropdown` | ✅ | Current status of the lead |

🔑 **Primary Key**: `lead_id`

🔗 **Relationships**: Opportunities, Lead Scoring

#### 2. Opportunities

> Tracks the sales opportunities related to leads.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| **opportunity_id** | `text` | ✅ | Unique identifier for each opportunity |
| **lead_id** | `text` | ✅ | Identifier of the related lead |
| **opportunity_name** | `text` | ✅ | Descriptive name for the opportunity |
| **expected_revenue** | `currency` | ✅ | Estimated revenue from this opportunity |
| **close_date** | `date` | ✅ | Projected close date for the opportunity |
| **stage** | `dropdown` | ✅ | Current stage of the opportunity |

🔑 **Primary Key**: `opportunity_id`

🔗 **Relationships**: Leads

#### 3. Lead Scoring

> This sheet calculates and stores scores for each lead based on multiple criteria.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| **lead_id** | `text` | ✅ | Identifier of the related lead |
| **score** | `number` | ✅ | Calculated score for the lead |
| **last_updated** | `date` | ✅ | Date when the score was last updated |

🔑 **Primary Key**: `lead_id`

🔗 **Relationships**: Leads

#### 4. Revenue Forecasting

> Provides revenue forecasts based on opportunities.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| **forecast_id** | `text` | ✅ | Unique identifier for each revenue forecast record |
| **opportunity_id** | `text` | ✅ | Identifier of the related opportunity |
| **forecasted_revenue** | `currency` | ✅ | Projected revenue figure |
| **forecast_date** | `date` | ✅ | Date of the forecast creation |

🔑 **Primary Key**: `forecast_id`

🔗 **Relationships**: Opportunities

#### 5. Reports

> Summarized data for visualizing CRM metrics and KPI analysis.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| **report_id** | `text` | ✅ | Unique identifier for each report |
| **report_name** | `text` | ✅ | Name of the report |
| **created_date** | `date` | ✅ | Date of report generation |

🔑 **Primary Key**: `report_id`

## ⚙️ Automated Calculations

### 1. Calculate the lead score based on the recency of the lead creation date. Recent leads (added within the last 30 days) get a score of 10, others get 5.

- **Sheet**: `Lead Scoring`
- **Column**: `score`
- **Formula**: `=IFERROR(IF(DATEDIF(INDIRECT("A"&ROW()), TODAY(), "D") <= 30, 10, 5), 0)`
- **Dependencies**: created_date
- **Auto-fill**: Yes

### 2. Pulls the expected revenue from the Opportunities sheet into the Revenue Forecasting sheet based on the opportunity_id match.

- **Sheet**: `Revenue Forecasting`
- **Column**: `forecasted_revenue`
- **Formula**: `=IFERROR(VLOOKUP(INDIRECT("B"&ROW()), Opportunities!A2:E, 4, FALSE), 0)`
- **Dependencies**: opportunity_id
- **Auto-fill**: Yes

### 3. Automatically sets the lead status to 'Inactive' if the lead is older than 60 days from the created_date, otherwise 'Active'.

- **Sheet**: `Leads`
- **Column**: `status`
- **Formula**: `=IFERROR(IF(DATEDIF(INDIRECT("E"&ROW()), TODAY(), "D") > 60, "Inactive", "Active"), "Undefined")`
- **Dependencies**: created_date
- **Auto-fill**: Yes

## 🔌 Required Integrations

- Email Marketing Platform
- Sales Dashboard

## 📁 Project Structure

```
20260131_103945_Build_CRM_with_lead_scoring_opportunity_pipeline_a/
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

```
┌─ Leads
│  └─→ links to Opportunities
│  └─→ links to Lead Scoring
  ┌─ Opportunities
  │  └─→ links to Leads
    ┌─ Lead Scoring
    │  └─→ links to Leads
      ┌─ Revenue Forecasting
      │  └─→ links to Opportunities
        ┌─ Reports
```

## ⚠️ Important Notes

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
