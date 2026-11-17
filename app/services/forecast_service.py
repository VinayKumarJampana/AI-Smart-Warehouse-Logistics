
import os
import math
import joblib
import pandas as pd

from datetime import timedelta


BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

MODEL_PATH = os.path.join(
    BASE_DIR, "ml_models", "demand_forecast_model.pkl"
)


class ForecastService:

    _model_data = None

    SERVICE_LEVEL_Z = 1.65

    @classmethod
    def load_model(cls):
        if cls._model_data is None:
            if not os.path.exists(MODEL_PATH):
                raise FileNotFoundError(
                    "Forecast model not found. Train the model first."
                )

            cls._model_data = joblib.load(MODEL_PATH)

        return cls._model_data

    @classmethod
    def calculate_safety_stock(cls, history, lead_time_days):
        """Calculate safety stock using historical demand variability."""

        if lead_time_days < 1:
            raise ValueError("Lead time must be at least 1 day.")

        daily_std = float(history["sales"].std(ddof=0))

        if pd.isna(daily_std):
            daily_std = 0.0

        safety_stock = math.ceil(
            cls.SERVICE_LEVEL_Z
            * daily_std
            * math.sqrt(lead_time_days)
        )

        average_daily_demand = float(history["sales"].mean())

        reorder_point = math.ceil(
            average_daily_demand * lead_time_days
            + safety_stock
        )

        return {
            "safety_stock": safety_stock,
            "average_daily_demand": round(average_daily_demand, 2),
            "reorder_point": reorder_point,
        }

    @classmethod
    def generate_forecast(
        cls,
        store_id,
        item_id,
        days=30,
        lead_time_days=7,
    ):
        """Generate demand forecast and inventory recommendations."""

        if days not in (7, 14, 30):
            raise ValueError("Forecast days must be 7, 14, or 30.")

        data = cls.load_model()

        model = data["model"]
        features = data["features"]
        history = data["training_data"].copy()

        history["date"] = pd.to_datetime(history["date"])

        history = history[
            (history["store"] == store_id)
            & (history["item"] == item_id)
        ].sort_values("date").copy()

        if history.empty:
            raise ValueError(
                "No historical data found for this store and item."
            )

        if lead_time_days < 1:
            raise ValueError("Lead time must be at least 1 day.")

        last_date = history["date"].max()

        values = history["sales"].astype(float).tolist()
        predictions = []

        for step in range(1, days + 1):

            forecast_date = last_date + timedelta(days=step)

            row = {
                "store": store_id,
                "item": item_id,
                "day": forecast_date.day,
                "month": forecast_date.month,
                "day_of_week": forecast_date.dayofweek,
                "year": forecast_date.year,
                "day_of_year": forecast_date.dayofyear,
                "lag_1": values[-1],
                "lag_7": values[-7] if len(values) >= 7 else values[-1],
                "lag_14": values[-14] if len(values) >= 14 else values[-1],
                "rolling_mean_7": sum(values[-7:]) / min(7, len(values)),
            }

            X = pd.DataFrame([row])[features]

            prediction = max(
                0,
                float(model.predict(X)[0])
            )

            predictions.append(prediction)
            values.append(prediction)

        inventory_metrics = cls.calculate_safety_stock(
            history,
            lead_time_days,
        )

        return {
            "predicted_demand": int(round(sum(predictions))),
            "daily_predictions": [
                round(value, 2) for value in predictions
            ],
            "mae": round(float(data["mae"]), 4),
            "rmse": round(float(data["rmse"]), 4),
            "forecast_days": days,
            "last_historical_date": last_date.strftime("%Y-%m-%d"),
            "safety_stock": inventory_metrics["safety_stock"],
            "average_daily_demand": inventory_metrics[
                "average_daily_demand"
            ],
            "reorder_point": inventory_metrics["reorder_point"],
            "lead_time_days": lead_time_days,
        }
