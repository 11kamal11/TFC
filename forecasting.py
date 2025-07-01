from odoo import models, fields, api
from odoo.exceptions import ValidationError
import base64
import io
import pandas as pd
from prophet import Prophet
import numpy as np
from sklearn.preprocessing import StandardScaler
import chardet
import plotly.graph_objects as go
from odoo.http import request

class ForecastingData(models.Model):
    _name = 'forecasting.data'
    _description = 'Forecasting Data'

    name = fields.Char(string="Name", required=True)
    file = fields.Binary(string="Upload CSV", required=True)
    file_name = fields.Char(string="File Name")
    date_column = fields.Char(string="Date Column")
    target_column = fields.Char(string="Target Column")
    period = fields.Integer(string="Period", default=12)
    horizon = fields.Integer(string="Horizon", default=12)
    five_year_forecast = fields.Boolean(string="Five Year Forecast")
    plot_type = fields.Selection([('line', 'Line'), ('bar', 'Bar')], default='line')
    plot_theme = fields.Selection([('plotly', 'Plotly'), ('seaborn', 'Seaborn')], default='plotly')
    yearly_seasonality = fields.Boolean(string="Yearly Seasonality", default=True)
    include_holidays = fields.Boolean(string="Include Holidays", default=False)
    forecast_result = fields.Text(string="Forecast Result")
    state = fields.Selection([('draft', 'Draft'), ('processed', 'Processed')], default='draft')

    @api.model
    def _detect_columns(self, file_content, file_name):
        raw_data = base64.b64decode(file_content)
        result = chardet.detect(raw_data)
        encoding = result['encoding']
        df = pd.read_csv(io.StringIO(raw_data.decode(encoding)), nrows=5)
        return {'date_columns': df.select_dtypes(include=['datetime64']).columns.tolist(),
                'numeric_columns': df.select_dtypes(include=['int64', 'float64']).columns.tolist()}

    @api.onchange('file')
    def _onchange_file(self):
        if self.file:
            column_info = self._detect_columns(self.file, self.file_name)
            self.date_column = column_info['date_columns'][0] if column_info['date_columns'] else False
            self.target_column = column_info['numeric_columns'][0] if column_info['numeric_columns'] else False
            self.state = 'processed'

    def generate_forecast(self):
        if not self.file or not self.date_column or not self.target_column:
            raise ValidationError("Please upload a CSV file and select date and target columns.")
        raw_data = base64.b64decode(self.file)
        result = chardet.detect(raw_data)
        encoding = result['encoding']
        df = pd.read_csv(io.StringIO(raw_data.decode(encoding)))
        df[self.date_column] = pd.to_datetime(df[self.date_column])
        df = df[[self.date_column, self.target_column]].rename(columns={self.date_column: 'ds', self.target_column: 'y'})
        model = Prophet(yearly_seasonality=self.yearly_seasonality, holidays=self.include_holidays)
        model.fit(df)
        future = model.make_future_dataframe(periods=self.horizon if not self.five_year_forecast else 60)
        forecast = model.predict(future)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=forecast['ds'], y=forecast['yhat'], mode='lines', name='Forecast'))
        fig.update_layout(title='Forecast', xaxis_title='Date', yaxis_title=self.target_column)
        plot_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
        self.forecast_result = plot_html
        return {
            'type': 'ir.actions.act_url',
            'url': f'/forecasting/view/{self.id}',
            'target': 'self',
        }

    def download_csv(self):
        if not self.file:
            raise ValidationError("No file uploaded to download.")
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self.id}?download=true&field=file&filename={self.file_name or "forecast_data.csv"}',
            'target': 'self',
        }
