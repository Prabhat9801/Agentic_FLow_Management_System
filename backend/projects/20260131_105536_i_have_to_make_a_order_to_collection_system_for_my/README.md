# OrderToCollection Management System

> A comprehensive system to manage the order to collection process for the company, facilitating order placement, tracking, invoicing, and collection activities.

## 📋 Project Overview

- **Created**: 2026-01-31T10:56:31.798125
- **Original Prompt**: i have to make a order to collection system for my company
- **Version**: 1.0
- **Execution Time**: 55.35s
- **Total Sheets**: 6
- **Total Columns**: 41

## 🔗 Quick Links

- [📊 Open Spreadsheet (View)](https://docs.google.com/spreadsheets/d/1jVHUVvjkVeggIom5BigFeWW5XeK4sRLraqC6Gd0r4Ek)
- [✏️ Open Spreadsheet (Edit)](https://docs.google.com/spreadsheets/d/1jVHUVvjkVeggIom5BigFeWW5XeK4sRLraqC6Gd0r4Ek/edit)
- **Spreadsheet ID**: `1jVHUVvjkVeggIom5BigFeWW5XeK4sRLraqC6Gd0r4Ek`

## 🏗️ System Architecture

### Workflow Stages
1. **Order Placement** → 2. **Order Fulfillment** → 3. **Invoicing** → 4. **Payment Collection** → 5. **Order Completion**

### 📊 Data Structure

#### 1. Customers

> Stores customer details for order management.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| **CustomerID** | `text` | ✅ | Unique identifier for each customer. |
| **CustomerName** | `text` | ✅ | Full name of the customer. |
| **Email** | `email` | ✅ | Email address of the customer. |
| **Phone** | `text` | ✅ | Contact number of the customer. |
| **created_date** | `date` | ✅ | Date the record was created. |
| **modified_date** | `date` | ❌ | Date the record was last modified. |
| **status** | `dropdown` | ✅ | Current status of the customer. |

🔑 **Primary Key**: `CustomerID`

🔗 **Relationships**: Orders

#### 2. Products

> Details of products available for order.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| **ProductID** | `text` | ✅ | Unique identifier for each product. |
| **ProductName** | `text` | ✅ | Name of the product. |
| **Price** | `currency` | ✅ | Price of the product. |
| **StockQuantity** | `number` | ✅ | Available stock quantity. |
| **created_date** | `date` | ✅ | Date the record was created. |
| **modified_date** | `date` | ❌ | Date the record was last modified. |

🔑 **Primary Key**: `ProductID`

🔗 **Relationships**: OrderItems

#### 3. Orders

> Records of customer orders.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| **OrderID** | `text` | ✅ | Unique identifier for each order. |
| **CustomerID** | `text` | ✅ | Identifier for the customer placing the order. |
| **OrderDate** | `date` | ✅ | Date the order was placed. |
| **TotalAmount** | `currency` | ✅ | Total amount of the order. |
| **created_date** | `date` | ✅ | Date the record was created. |
| **modified_date** | `date` | ❌ | Date the record was last modified. |
| **status** | `dropdown` | ✅ | Current status of the order. |

🔑 **Primary Key**: `OrderID`

🔗 **Relationships**: Customers, OrderItems, Invoices

#### 4. OrderItems

> Details of products included in each order.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| **LineItemID** | `text` | ✅ | Unique identifier for each line item. |
| **OrderID** | `text` | ✅ | Identifier for the associated order. |
| **ProductID** | `text` | ✅ | Identifier for the product in the order. |
| **Quantity** | `number` | ✅ | Quantity of the product ordered. |
| **created_date** | `date` | ✅ | Date the record was created. |
| **modified_date** | `date` | ❌ | Date the record was last modified. |

🔑 **Primary Key**: `LineItemID`

🔗 **Relationships**: Orders, Products

#### 5. Invoices

> Stores invoicing details for orders.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| **InvoiceID** | `text` | ✅ | Unique identifier for each invoice. |
| **OrderID** | `text` | ✅ | Identifier for the associated order. |
| **InvoiceDate** | `date` | ✅ | Date when the invoice was issued. |
| **DueDate** | `date` | ✅ | Date when the invoice is due. |
| **AmountDue** | `currency` | ✅ | Total amount due for the invoice. |
| **created_date** | `date` | ✅ | Date the record was created. |
| **modified_date** | `date` | ❌ | Date the record was last modified. |
| **status** | `dropdown` | ✅ | Current status of the invoice. |

🔑 **Primary Key**: `InvoiceID`

🔗 **Relationships**: Orders

#### 6. Payments

> Tracks payment transactions related to invoices.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| **PaymentID** | `text` | ✅ | Unique identifier for each payment. |
| **InvoiceID** | `text` | ✅ | Identifier of the invoice associated with the payment. |
| **PaymentDate** | `date` | ✅ | Date when the payment was made. |
| **AmountPaid** | `currency` | ✅ | Amount paid in this transaction. |
| **PaymentMethod** | `dropdown` | ✅ | Method used for the payment. |
| **created_date** | `date` | ✅ | Date the record was created. |
| **modified_date** | `date` | ❌ | Date the record was last modified. |

🔑 **Primary Key**: `PaymentID`

🔗 **Relationships**: Invoices

## ⚙️ Automated Calculations

### 1. Calculates the total amount for the order by summing the quantity of each product in the OrderItems sheet multiplied by the product price from the Products sheet.

- **Sheet**: `Orders`
- **Column**: `TotalAmount`
- **Formula**: `=IFERROR(SUMIF(OrderItems!B:B, A2, OrderItems!D:D) * VLOOKUP(VLOOKUP(INDEX(OrderItems!C:C, MATCH(A2, OrderItems!B:B, 0)), Products!A:B, 2, FALSE), Products!A:C, 3, FALSE), 0)`
- **Dependencies**: OrderItems!B, OrderItems!C, OrderItems!D, Products!A, Products!B, Products!C
- **Auto-fill**: Yes

### 2. Sets the due date of the invoice to be 30 working days after the invoice date.

- **Sheet**: `Invoices`
- **Column**: `DueDate`
- **Formula**: `=IFERROR(WORKDAY(C2, 30), C2 + 30)`
- **Dependencies**: InvoiceDate
- **Auto-fill**: Yes

### 3. Calculates the total amount paid for each invoice by summing all payment transactions associated with an invoice.

- **Sheet**: `Payments`
- **Column**: `AmountPaid`
- **Formula**: `=IFERROR(SUMIF(Payments!B:B, A2, Payments!D:D), 0)`
- **Dependencies**: InvoiceID, AmountPaid
- **Auto-fill**: Yes

## 🔌 Required Integrations

- Payment Gateway API
- CRM System

## 📁 Project Structure

```
20260131_105536_i_have_to_make_a_order_to_collection_system_for_my/
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
┌─ Customers
│  └─→ links to Orders
  ┌─ Products
  │  └─→ links to OrderItems
    ┌─ Orders
    │  └─→ links to Customers
    │  └─→ links to OrderItems
    │  └─→ links to Invoices
      ┌─ OrderItems
      │  └─→ links to Orders
      │  └─→ links to Products
        ┌─ Invoices
        │  └─→ links to Orders
          ┌─ Payments
          │  └─→ links to Invoices
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
