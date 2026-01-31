# Order Payment Flow Management System

> A comprehensive system to manage the order and payment processes, ensuring efficient tracking from order placement to payment completion.

## 📋 Project Overview

- **Created**: 2026-01-29T22:12:23.527209
- **Original Prompt**: Make a order - payement Flow Management System
- **Version**: 1.0
- **Execution Time**: 128.87s
- **Total Sheets**: 5
- **Total Columns**: 34

## 🔗 Quick Links

- [📊 Open Spreadsheet (View)](https://docs.google.com/spreadsheets/d/1zCxp8YWTLsHljg9961LJWKzKKcx-koBCbEqW7OQK_OU)
- [✏️ Open Spreadsheet (Edit)](https://docs.google.com/spreadsheets/d/1zCxp8YWTLsHljg9961LJWKzKKcx-koBCbEqW7OQK_OU/edit)
- **Spreadsheet ID**: `1zCxp8YWTLsHljg9961LJWKzKKcx-koBCbEqW7OQK_OU`

## 🏗️ System Architecture

### Workflow Stages
1. **Order Placement** → 2. **Order Processing** → 3. **Payment Processing** → 4. **Order Fulfillment** → 5. **Order Completion**

### 📊 Data Structure

#### 1. Customers

> Stores customer information and details.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| **customer_id** | `text` | ✅ | Unique identifier for each customer. |
| **customer_name** | `text` | ✅ | Full name of the customer. |
| **email** | `email` | ✅ | Email address of the customer. |
| **phone_number** | `text` | ❌ | Contact phone number of the customer. |
| **created_date** | `date` | ✅ | Date when the customer record was created. |
| **modified_date** | `date` | ❌ | Date when the customer record was last modified. |

🔑 **Primary Key**: `customer_id`

🔗 **Relationships**: Orders

#### 2. Products

> Catalog of products available for order.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| **product_id** | `text` | ✅ | Unique identifier for each product. |
| **product_name** | `text` | ✅ | Name of the product. |
| **price** | `currency` | ✅ | Price of the product. |
| **stock_quantity** | `number` | ✅ | Available stock quantity. |
| **created_date** | `date` | ✅ | Date when the product was added to the catalog. |
| **modified_date** | `date` | ❌ | Date when the product details were last modified. |

🔑 **Primary Key**: `product_id`

🔗 **Relationships**: Order_Items

#### 3. Orders

> Tracks customer orders and their statuses.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| **order_id** | `text` | ✅ | Unique identifier for each order. |
| **customer_id** | `text` | ✅ | Identifier for the customer placing the order. |
| **order_date** | `date` | ✅ | Date when the order was placed. |
| **status** | `dropdown` | ✅ | Current status of the order. |
| **total_amount** | `currency` | ✅ | Total amount for the order. |
| **created_date** | `date` | ✅ | Date when the order record was created. |
| **modified_date** | `date` | ❌ | Date when the order record was last modified. |

🔑 **Primary Key**: `order_id`

🔗 **Relationships**: Customers, Order_Items, Payments

#### 4. Order_Items

> Details of products included in each order.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| **order_item_id** | `text` | ✅ | Unique identifier for each order item. |
| **order_id** | `text` | ✅ | Identifier for the order to which this item belongs. |
| **product_id** | `text` | ✅ | Identifier for the product included in the order. |
| **quantity** | `number` | ✅ | Quantity of the product ordered. |
| **price** | `currency` | ✅ | Price of the product at the time of order. |
| **created_date** | `date` | ✅ | Date when the order item record was created. |
| **modified_date** | `date` | ❌ | Date when the order item record was last modified. |

🔑 **Primary Key**: `order_item_id`

🔗 **Relationships**: Orders, Products

#### 5. Payments

> Records payment transactions for orders.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| **payment_id** | `text` | ✅ | Unique identifier for each payment transaction. |
| **order_id** | `text` | ✅ | Identifier for the order associated with this payment. |
| **payment_date** | `date` | ✅ | Date when the payment was made. |
| **amount** | `currency` | ✅ | Amount paid in the transaction. |
| **payment_method** | `dropdown` | ✅ | Method used for the payment. |
| **status** | `dropdown` | ✅ | Current status of the payment. |
| **created_date** | `date` | ✅ | Date when the payment record was created. |
| **modified_date** | `date` | ❌ | Date when the payment record was last modified. |

🔑 **Primary Key**: `payment_id`

🔗 **Relationships**: Orders

## ⚙️ Automated Calculations

### 1. Calculates the total amount for each order by summing the price of all order items associated with the order.

- **Sheet**: `Orders`
- **Column**: `total_amount`
- **Formula**: `=IFERROR(SUMIF(Order_Items!A:A, A2, Order_Items!E:E), 0)`
- **Dependencies**: order_id, Order_Items!order_id, Order_Items!price
- **Auto-fill**: Yes

### 2. Calculates the remaining stock quantity by subtracting the total ordered quantity from the initial stock quantity.

- **Sheet**: `Products`
- **Column**: `stock_quantity`
- **Formula**: `=IFERROR(INDEX(Order_Items!C:C, MATCH(A2, Order_Items!C:C, 0)) - SUMIF(Order_Items!C:C, A2, Order_Items!D:D), B2)`
- **Dependencies**: product_id, Order_Items!product_id, Order_Items!quantity
- **Auto-fill**: Yes

### 3. Updates the modified date to the latest of created or modified date for tracking changes.

- **Sheet**: `Customers`
- **Column**: `modified_date`
- **Formula**: `=IFERROR(MAX(created_date, modified_date), created_date)`
- **Dependencies**: created_date, modified_date
- **Auto-fill**: Yes

### 4. Determines the payment status as 'Paid' if the payment amount is greater than or equal to the order total amount, otherwise 'Pending'.

- **Sheet**: `Payments`
- **Column**: `status`
- **Formula**: `=IFERROR(IF(amount >= VLOOKUP(order_id, Orders!A:E, 5, FALSE), "Paid", "Pending"), "Pending")`
- **Dependencies**: amount, order_id, Orders!order_id, Orders!total_amount
- **Auto-fill**: Yes

### 5. Sets the order status to 'Overdue' if the order date is more than 30 days ago, otherwise 'On Time'.

- **Sheet**: `Orders`
- **Column**: `status`
- **Formula**: `=IFERROR(IF(TODAY() - order_date > 30, "Overdue", "On Time"), "On Time")`
- **Dependencies**: order_date
- **Auto-fill**: Yes

## 🔌 Required Integrations

- Payment Gateway API
- Inventory Management System

## 📁 Project Structure

```
20260129_221105_Make_a_order_payement_Flow_Management_System/
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
  │  └─→ links to Order_Items
    ┌─ Orders
    │  └─→ links to Customers
    │  └─→ links to Order_Items
    │  └─→ links to Payments
      ┌─ Order_Items
      │  └─→ links to Orders
      │  └─→ links to Products
        ┌─ Payments
        │  └─→ links to Orders
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
