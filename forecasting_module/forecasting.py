from odoo import models, fields, api
import pandas as pd
import numpy as np
from prophet import Prophet
from sklearn.metrics import mean_squared_error, mean_absolute_error
import chardet
import base64
import io
import json
import logging

_logger = logging.getLogger(__name__)

class ForecastingData(models.Model):
    _name = 'forecasting.data'
    _description = 'Forecasting Data'

    name = fields.Char(string='Name', required=True)
    file = fields.Binary(string='CSV File')
    file_name = fields.Char(string='File Name')
    date_column = fields.Char(string='Date Column')
    target_column = fields.Char(string='Target Column')
    period = fields.Selection([
        ('quarterly', 'Quarterly'),
        ('half_yearly', 'Half-Yearly'),
        ('yearly', 'Yearly')
    ], string='Forecast Period', default='quarterly')
    horizon = fields.Integer(string='Forecast Horizon', default=2)
    five_year_forecast = fields.Boolean(string='5-Year Forecast')
    plot_type = fields.Selection([
        ('line', 'Line'),
        ('bar', 'Bar')
    ], string='Plot Type', default='line')
    plot_theme = fields.Selection([
        ('plotly_white', 'Light'),
        ('plotly_dark', 'Dark')
    ], string='Plot Theme', default='plotly_white')
    yearly_seasonality = fields.Boolean(string='Include Yearly Seasonality', default=True)
    include_holidays = fields.Boolean(string='Include US Holidays')
    forecast_result = fields.Text(string='Forecast Result (JSON)')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('processed', 'Processed'),
        ('forecasted', 'Forecasted')
    ], string='State', default='draft')

    @api.model
    def load_data(self, file_content, file_name):
        try:
            raw_data = base64.b64decode(file_content)
            encoding = chardet.detect(raw_data)['encoding'] or 'utf-8'
            delimiters = [',', ';', '\t', '|', ' ', ':']
            for delimiter in delimiters:
                try:
                    df = pd.read_csv(io.BytesIO(raw_data), delimiter=delimiter, encoding=encoding, on_bad_lines='skip', low_memory=False)
                    if len(df.columns) >= 2:
                        return df, f"Loaded CSV with delimiter '{delimiter}'"
                except Exception as e:
                    continue
            return None, "Could not parse CSV with common delimiters."
        except Exception as e:
            return None, f"Error reading CSV: {str(e)}"

    def is_date_column(self, series):
        try:
            sample = series.dropna().head(100).astype(str).str.strip()
            if len(sample) < 5:
                return False
            date_formats = [
                '%Y-%m-%d', '%Y%m%d', '%Y/%m/%d', '%d/%m/%Y', '%d-%m-%Y',
                '%Y-%m', '%Y%m', '%m/%Y', '%b %Y', '%Y', '%d %b %Y', '%m-%d-%Y',
                '%Y/%m', '%d.%m.%Y', '%m-%d-%Y', '%Y.%m.%d', '%b-%d-%Y',
                '%Y-%b-%d', '%d/%b/%Y', '%Y/%b/%d', '%m.%d.%Y'
            ]
            if sample.str.match(r'^\d{6}$').sum() >= len(sample) * 0.8:
                return True
            for fmt in date_formats:
                parsed = pd.to_datetime(sample, format=fmt, errors='coerce')
                if parsed.notna().sum() >= len(sample) * 0.8:
                    return True
            parsed = pd.to_datetime(sample, errors='coerce')
            if parsed.notna().sum() >= len(sample) * 0.8:
                return True
            return False
        except:
            return False

    def preprocess_time_series(self, df, date_col, target_col, freq):
        try:
            if date_col == target_col:
                return None, "Date and target columns must be different."
            df = df.copy()
            df[date_col] = df[date_col].astype(str).str.strip()
            if df[date_col].str.match(r'^\d{6}$').any():
                df[date_col] = pd.to_datetime(df[date_col], format='%Y%m', errors='coerce')
            else:
                df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
            if df[date_col].isna().any():
                df = df.dropna(subset=[date_col])
            if df.empty:
                return None, "No valid dates remain."
            df[target_col] = pd.to_numeric(df[target_col], errors='coerce')
            if df[target_col].isna().all():
                return None, f"Target '{target_col}' contains no valid numeric values."
            df = df[[date_col, target_col]].set_index(date_col)
            df = df.resample(freq).mean().reset_index()
            if df[target_col].isna().any():
                df[target_col] = df[target_col].fillna(df[target_col].mean())
            df = df.rename(columns={date_col: 'ds', target_col: 'y'})
            df['ds'] = pd.to_datetime(df['ds'])
            df = df.sort_values('ds')
            if len(df['ds'].unique()) < 2:
                return None, f"Only {len(df['ds'].unique())} unique date(s) found."
            return df, "Data preprocessed successfully."
        except Exception as e:
            return None, f"Preprocessing failed: {str(e)}"

    def generate_forecast(self):
        try:
            freq_map = {'quarterly': 'Q', 'half_yearly': '6M', 'yearly': 'Y'}
            freq = freq_map[self.period]
            df, message = self.load_data(self.file, self.file_name)
            if df is None:
                return {'error': message}
            processed_df, message = self.preprocess_time_series(df, self.date_column, self.target_column, freq)
            if processed_df is None:
                return {'error': message}
            train_size = int(len(processed_df) * 0.8)
            if train_size < 2:
                return {'error': "Need at least 2 rows for training."}
            train = processed_df[:train_size]
            test = processed_df[train_size:]
            model = Prophet(
                yearly_seasonality=self.yearly_seasonality and len(processed_df) >= 4 if freq != 'Y' else False,
                weekly_seasonality=False,
                daily_seasonality=False
            )
            if self.include_holidays:
                model.add_country_holidays(country_name='US')
            model.fit(train)
            horizon = 20 if self.five_year_forecast and self.period == 'quarterly' else 10 if self.five_year_forecast and self.period == 'half_yearly' else 5 if self.five_year_forecast and self.period == 'yearly' else self.horizon
            future = model.make_future_dataframe(periods=horizon, freq=freq)
            forecast = model.predict(future)
            test_df = test[['ds', 'y']].merge(forecast[['ds', 'yhat']], on='ds', how='left')
            y_pred = test_df['yhat'].values
            y_true = test_df['y'].values
            if len(y_pred) == 0 or np.any(np.isnan(y_pred)):
                rmse, mae, mape = None, None, None
            else:
                rmse = np.sqrt(mean_squared_error(y_true, y_pred))
                mae = mean_absolute_error(y_true, y_pred)
                mape = np.mean(np.abs((y_true - y_pred) / (y_true + 1e-10))) * 100
            future_forecast = forecast[forecast['ds'] > processed_df['ds'].max()]
            result = {
                'historical': processed_df[['ds', 'y']].to_dict(orient='records'),
                'forecast': future_forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].to_dict(orient='records'),
                'metrics': {'rmse': rmse, 'mae': mae, 'mape': mape},
                'train': train[['ds', 'y']].to_dict(orient='records'),
                'test': test[['ds', 'y']].to_dict(orient='records'),
                'full_forecast': forecast[['ds', 'yhat', 'yhat_upper', 'yhat_lower', 'trend']].to_dict(orient='records'),
                'yearly_seasonality': forecast[['ds', 'yearly']].to_dict(orient='records') if self.yearly_seasonality and len(processed_df) >= 4 and freq != 'Y' else [],
                'holidays': forecast[['ds', 'holidays']].to_dict(orient='records') if self.include_holidays and 'holidays' in forecast.columns else []
            }
            self.forecast_result = json.dumps(result)
            self.state = 'forecasted'
            return result
        except Exception as e:
            return {'error': f"Forecasting failed: {str(e)}"}
