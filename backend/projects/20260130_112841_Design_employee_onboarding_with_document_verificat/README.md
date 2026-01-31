# Employee Onboarding Management System

> A system to manage the onboarding process of new employees, including document verification and training scheduling.

## 📋 Project Overview

- **Created**: 2026-01-30T11:29:21.914631
- **Original Prompt**: Design employee onboarding with document verification and training schedules
- **Version**: 1.0
- **Execution Time**: 40.76s
- **Total Sheets**: 4
- **Total Columns**: 29

## 🔗 Quick Links

- [📊 Open Spreadsheet (View)](https://docs.google.com/spreadsheets/d/1m7FYfKDix9ZmEzcI2V5i1oOQmGzBp2OWVCv2EMhSN2s)
- [✏️ Open Spreadsheet (Edit)](https://docs.google.com/spreadsheets/d/1m7FYfKDix9ZmEzcI2V5i1oOQmGzBp2OWVCv2EMhSN2s/edit)
- **Spreadsheet ID**: `1m7FYfKDix9ZmEzcI2V5i1oOQmGzBp2OWVCv2EMhSN2s`

## 🏗️ System Architecture

### Workflow Stages
1. **Initiation** → 2. **Document Verification** → 3. **Training Schedule** → 4. **Completion**

### 📊 Data Structure

#### 1. Employees

> Stores master data of employees being onboarded.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| **employee_id** | `text` | ✅ | Unique identifier for an employee |
| **first_name** | `text` | ✅ | The first name of the employee |
| **last_name** | `text` | ✅ | The last name of the employee |
| **email** | `email` | ✅ | The email address of the employee |
| **start_date** | `date` | ✅ | The employment start date |
| **created_date** | `date` | ✅ | The date the employee record was created |
| **modified_date** | `date` | ❌ | The date the employee record was last modified |
| **status** | `dropdown` | ✅ | Current status of employee onboarding |

🔑 **Primary Key**: `employee_id`

🔗 **Relationships**: Document Verification, Training Schedule

#### 2. Document Verification

> Tracks the verification status of necessary documents for onboarding.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| **verification_id** | `text` | ✅ | Unique identifier for a document verification record |
| **employee_id** | `text` | ✅ | Link to the employee being verified |
| **document_type** | `text` | ✅ | Type of document being verified (e.g., ID, contract) |
| **verification_status** | `dropdown` | ✅ | Status of the document verification |
| **verified_date** | `date` | ❌ | Date when the document was verified |
| **created_date** | `date` | ✅ | Date the verification record was created |
| **modified_date** | `date` | ❌ | Date the verification record was last modified |

🔑 **Primary Key**: `verification_id`

🔗 **Relationships**: Employees

#### 3. Training Schedule

> Manages the training schedule and status for new employees.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| **schedule_id** | `text` | ✅ | Unique identifier for a training schedule record |
| **employee_id** | `text` | ✅ | Link to the employee enrolled in the training |
| **training_program** | `text` | ✅ | Name of the training program |
| **start_date** | `date` | ✅ | Start date of the training |
| **end_date** | `date` | ✅ | End date of the training |
| **completion_status** | `dropdown` | ✅ | Status of training completion |
| **created_date** | `date` | ✅ | Date the training schedule was created |
| **modified_date** | `date` | ❌ | Date the training schedule was last modified |

🔑 **Primary Key**: `schedule_id`

🔗 **Relationships**: Employees

#### 4. Onboarding Process Tracking

> Tracks the overall status and stages of the onboarding process.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| **process_id** | `text` | ✅ | Unique identifier for an onboarding process record |
| **employee_id** | `text` | ✅ | Link to the employee undergoing onboarding |
| **current_stage** | `dropdown` | ✅ | Current stage of the onboarding process |
| **approval_status** | `dropdown` | ✅ | Approval status of the current stage |
| **created_date** | `date` | ✅ | Date the process tracking was initiated |
| **modified_date** | `date` | ❌ | Date the tracking record was last updated |

🔑 **Primary Key**: `process_id`

🔗 **Relationships**: Employees

## ⚙️ Automated Calculations

### 1. Concatenates the first name and last name into a full name

- **Sheet**: `Employees`
- **Column**: `full_name`
- **Formula**: `=CONCATENATE(IFERROR(A2, ""), " ", IFERROR(B2, ""))`
- **Dependencies**: first_name, last_name
- **Auto-fill**: Yes

### 2. Calculates the number of days since document verification

- **Sheet**: `Document Verification`
- **Column**: `days_since_verification`
- **Formula**: `=IF(ISDATE(E2), TODAY() - E2, "")`
- **Dependencies**: verified_date
- **Auto-fill**: Yes

### 3. Calculates the days remaining until the training ends

- **Sheet**: `Training Schedule`
- **Column**: `days_until_training_end`
- **Formula**: `=IF(ISDATE(E2), E2 - TODAY(), "")`
- **Dependencies**: end_date
- **Auto-fill**: Yes

### 4. Calculates the number of days spent in the current onboarding stage

- **Sheet**: `Onboarding Process Tracking`
- **Column**: `days_in_current_stage`
- **Formula**: `=IF(ISDATE(G2), TODAY() - G2, "")`
- **Dependencies**: modified_date
- **Auto-fill**: Yes

## 🔌 Required Integrations

- HRIS
- Payroll System

## 📁 Project Structure

```
20260130_112841_Design_employee_onboarding_with_document_verificat/
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
┌─ Employees
│  └─→ links to Document Verification
│  └─→ links to Training Schedule
  ┌─ Document Verification
  │  └─→ links to Employees
    ┌─ Training Schedule
    │  └─→ links to Employees
      ┌─ Onboarding Process Tracking
      │  └─→ links to Employees
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
