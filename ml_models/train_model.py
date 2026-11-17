
import os
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error


# 1. Project paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "train.csv")
MODEL_DIR = os.path.join(BASE_DIR, "ml_models")

os.makedirs(MODEL_DIR, exist_ok=True)


# 2. Load Dataset
print("\nLoading Dataset...")

df = pd.read_csv(DATA_PATH)
df.columns = df.columns.str.strip().str.lower()

print("Original Shape:", df.shape)


# 3. Data Cleaning
print("\nCleaning Data...")

df["date"] = pd.to_datetime(df["date"], errors="coerce")
df["store"] = pd.to_numeric(df["store"], errors="coerce")
df["item"] = pd.to_numeric(df["item"], errors="coerce")
df["sales"] = pd.to_numeric(df["sales"], errors="coerce")

df.dropna(subset=["date", "store", "item", "sales"], inplace=True)
df.drop_duplicates(inplace=True)

df = df[
    (df["sales"] >= 0) &
    (df["store"] > 0) &
    (df["item"] > 0)
].copy()

df["store"] = df["store"].astype(int)
df["item"] = df["item"].astype(int)

df.sort_values(["store", "item", "date"], inplace=True)
df.reset_index(drop=True, inplace=True)

print("Cleaned Shape:", df.shape)
print("Missing Values:\n", df.isnull().sum())

# Keep cleaned historical data for future forecasting
historical_data = df[["date", "store", "item", "sales"]].copy()


# 4. Exploratory Data Analysis
print("\nGenerating EDA...")

daily_sales = df.groupby("date")["sales"].sum()

plt.figure(figsize=(12, 5))
daily_sales.plot()
plt.title("Daily Store Sales")
plt.xlabel("Date")
plt.ylabel("Sales")
plt.tight_layout()

chart_path = os.path.join(MODEL_DIR, "sales_trend.png")
plt.savefig(chart_path)
plt.close()


# 5. Feature Engineering
print("\nCreating Features...")

df["day"] = df["date"].dt.day
df["month"] = df["date"].dt.month
df["day_of_week"] = df["date"].dt.dayofweek
df["year"] = df["date"].dt.year
df["day_of_year"] = df["date"].dt.dayofyear

group = df.groupby(["store", "item"])["sales"]

df["lag_1"] = group.shift(1)
df["lag_7"] = group.shift(7)
df["lag_14"] = group.shift(14)

df["rolling_mean_7"] = (
    df.groupby(["store", "item"])["sales"]
    .transform(lambda x: x.shift(1).rolling(7).mean())
)

features = [
    "store",
    "item",
    "day",
    "month",
    "day_of_week",
    "year",
    "day_of_year",
    "lag_1",
    "lag_7",
    "lag_14",
    "rolling_mean_7",
]

df.dropna(subset=features + ["sales"], inplace=True)


# 6. Global Chronological Train/Test Split
print("\nSplitting Data Chronologically...")

unique_dates = sorted(df["date"].unique())

if len(unique_dates) < 2:
    raise ValueError("Not enough unique dates for train/test split.")

split_index = int(len(unique_dates) * 0.8)
split_index = max(1, min(split_index, len(unique_dates) - 1))

cutoff_date = unique_dates[split_index - 1]

train_df = df[df["date"] <= cutoff_date].copy()
test_df = df[df["date"] > cutoff_date].copy()

X_train = train_df[features]
X_test = test_df[features]

y_train = train_df["sales"]
y_test = test_df["sales"]

print("Training Records:", len(X_train))
print("Testing Records:", len(X_test))
print("Training End Date:", train_df["date"].max())
print("Testing Start Date:", test_df["date"].min())


# 7. Random Forest Model Training
print("\nTraining Random Forest Model...")

model = RandomForestRegressor(
    n_estimators=100,
    max_depth=15,
    min_samples_leaf=2,
    random_state=42,
    n_jobs=-1
)

model.fit(X_train, y_train)


# 8. Model Evaluation
print("\nEvaluating Model...")

predictions = model.predict(X_test)

mae = mean_absolute_error(y_test, predictions)
rmse = np.sqrt(mean_squared_error(y_test, predictions))

print("MAE:", round(mae, 4))
print("RMSE:", round(rmse, 4))


# 9. Save Model and Metadata
model_data = {
    "model": model,
    "features": features,
    "mae": float(mae),
    "rmse": float(rmse),
    "model_name": "RandomForestRegressor",
    "train_size": int(len(X_train)),
    "test_size": int(len(X_test)),
    "train_end_date": str(train_df["date"].max().date()),
    "test_start_date": str(test_df["date"].min().date()),
    "last_date": historical_data["date"].max(),
    "training_data": historical_data,
}

model_path = os.path.join(
    MODEL_DIR,
    "demand_forecast_model.pkl"
)

joblib.dump(model_data, model_path)

print("\nModel Saved Successfully!")
print("Model Path:", model_path)
print("EDA Chart Saved:", chart_path)

print("\nTRAINING COMPLETED SUCCESSFULLY!")
