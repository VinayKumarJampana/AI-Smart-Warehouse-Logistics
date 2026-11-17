# AI-Powered Smart Warehouse & Logistics Management System

## 1. Project Overview

The AI-Powered Smart Warehouse & Logistics Management System is a web-based application designed to manage warehouse inventory, customer orders, vehicle dispatch operations, and logistics activities.

The system also integrates a Machine Learning-based demand forecasting module to predict future product demand and calculate safety stock and reorder points.

## 2. Technologies Used

- **Backend:** Python 3.11.4, Flask
- **Frontend:** HTML, CSS, Bootstrap 5, JavaScript
- **Database:** MySQL
- **ORM:** SQLAlchemy
- **Machine Learning:** Pandas, Scikit-learn
- **Data Visualization:** Chart.js
- **Testing:** Pytest

## 3. Key Features

### User Authentication & Role-Based Access
- User registration and login
- Secure password handling
- Role-based access control
- Admin user management

### Warehouse Management
- Create and manage warehouses
- Manage product categories
- Add and update product information
- Track warehouse inventory

### Inventory Management
- Stock In and Stock Out operations
- Real-time stock balance updates
- Reorder level monitoring
- Inventory transaction history
- Audit trail

### Order Management
- Customer management
- Create customer orders
- Manage order quantities
- Track order status

### Dispatch & Logistics Management
- Vehicle management
- Driver management
- Assign vehicles and drivers
- Track delivery status
- Update dispatch progress

### AI Demand Forecasting
- Historical sales data analysis
- Machine Learning-based demand prediction
- 7-day, 14-day, and 30-day forecasts
- Safety stock calculation
- Reorder point calculation
- Recommended reorder quantity
- Forecast history

### Analytics & Reports
- Dashboard KPI summaries
- Monthly sales trends
- Stock movement analysis
- Warehouse stock distribution
- AI forecast analytics

## 4. Machine Learning Model

The project uses a Random Forest Regressor for demand forecasting.

**Dataset:** Store Item Demand Forecasting Challenge (Kaggle)

**Dataset Details:**
- Total records: 913,000
- Date range: 2013-01-01 to 2017-12-31
- Features: Date, Store ID, Item ID, Sales

**Feature Engineering:**
- Store ID
- Item ID
- Day
- Month
- Day of Week
- Year
- Day of Year
- Lag 1
- Lag 7
- Lag 14
- Rolling Mean 7

**Model Evaluation:**
- MAE: Approximately 6.4566
- RMSE: Approximately 8.4216
- Chronological 80/20 train-test split

The evaluation metrics represent the model's one-step test-set performance. They should not be interpreted as guaranteed accuracy for recursive multi-day forecasts.

**Note:** The Kaggle dataset is used for demonstration and model development. It is not actual company or Dabur warehouse sales data.

## 5. Inventory Optimization

The system calculates safety stock and reorder point using historical demand.

**Safety Stock Formula:**

Safety Stock = Z × Daily Demand Standard Deviation × √Lead Time

**Reorder Point Formula:**

Reorder Point = Average Daily Demand × Lead Time + Safety Stock

The system uses a service-level factor of Z = 1.65.

## 6. Project Structure

```text
SMART_LOGISTICS/
│
├── app/
│   ├── forms/
│   ├── models/
│   ├── routes/
│   ├── services/
│   ├── static/
│   ├── templates/
│   ├── utils/
│   ├── __init__.py
│   ├── config.py
│   └── extensions.py
│
├── data/
├── ml_models/
│   └── train_model.py
│
├── tests/
├── .env.example
├── requirements.txt
├── run.py
└── README.md
```

## 7. Installation & Setup

### Step 1: Clone or Download the Project

Download the project and open its folder in Visual Studio Code.

### Step 2: Create Virtual Environment

```bash
python -m venv venv
```

Activate the environment on Windows:

```bash
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

Create a `.env` file in the project root using `.env.example` as a reference.

Configure the MySQL database connection and required application settings.

Do not share or commit your `.env` file.

### Step 5: Create MySQL Database

Create the database:

```sql
CREATE DATABASE smart_logistics_db;
```

Configure the database credentials in `.env`.

### Step 6: Initialize Database

```bash
flask init-db
```

### Step 7: Run the Application

```bash
python run.py
```

Open the application:

http://127.0.0.1:5000

## 8. Run Tests

Execute the test suite:

```bash
python -m pytest -v
```

## 9. Future Enhancements

- Integration with real warehouse management systems
- Live GPS vehicle tracking
- Advanced demand forecasting models
- Supplier management
- Automated purchase order generation
- Email and SMS notifications
- Cloud deployment

## 10. Conclusion

The AI-Powered Smart Warehouse & Logistics Management System combines inventory management, order processing, dispatch tracking, analytics, and Machine Learning-based demand forecasting in a single web application.

The project aims to improve inventory visibility, support better stock planning, and streamline warehouse and logistics operations.