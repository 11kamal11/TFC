from odoo import models, fields, api
from prophet import Prophet
import pandas as pd
import base64
import io
from odoo.exceptions import ValidationError

class ForecastingData(models.Model):
    _name = 'forecasting.data'
    _description = 'Forecasting Data'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Name", required=True)
    file = fields.Binary(string="Upload CSV")
    file_name = fields.Char(string="File Name")
    date_column = fields.Char(string="Date Column")
    target_column = fields.Char(string="Target Column")
    period = fields.Integer(string="Period", default=12)
    horizon = fields.Integer(string="Forecast Horizon", default=12)
    five_year_forecast = fields.Boolean(string="5-Year Forecast")
    plot_type = fields.Selection([('line', 'Line'), ('bar', 'Bar')], string="Plot Type", default='line')
    plot_theme = fields.Selection([('light', 'Light'), ('dark', 'Dark')], string="Plot Theme", default='light')
    yearly_seasonality = fields.Boolean(string="Yearly Seasonality", default=True)
    include_holidays = fields.Boolean(string="Include Holidays", default=False)
    forecast_result = fields.Html(string="Forecast Result")
    state = fields.Selection([('draft', 'Draft'), ('processed', 'Processed')], default='draft')

    @api.model
    def _detect_columns(self, file_content, file_name):
        df = pd.read_csv(io.StringIO(file_content.decode()))
        date_cols = [col for col in df.columns if pd.api.types.is_datetime64_any_dtype(df[col])]
        numeric_cols = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]
        return {'date_column': date_cols[0] if date_cols else '', 'target_column': numeric_cols[0] if numeric_cols else ''}

    def load_data(self):
        if not self.file:
            raise ValidationError("Please upload a CSV file.")
        file_content = base64.b64decode(self.file)
        column_info = self._detect_columns(file_content, self.file_name)
        self.date_column = column_info['date_column']
        self.target_column = column_info['target_column']
        self.state = 'processed'

    def generate_forecast(self):
        if not self.file or not self.date_column or not self.target_column:
            raise ValidationError("Please ensure a CSV file is uploaded and date/target columns are set.")
        file_content = base64.b64decode(self.file)
        df = pd.read_csv(io.StringIO(file_content.decode()))
        model = Prophet(yearly_seasonality=self.yearly_seasonality, holidays=None if not self.include_holidays else None)
        model.fit(df.rename(columns={self.date_column: 'ds', self.target_column: 'y'}))
        future = model.make_future_dataframe(periods=self.horizon)
        forecast = model.predict(future)
        plot_html = forecast.to_html()
        self.forecast_result = plot_html
        return {
            'type': 'ir.actions.client',
            'tag': 'display_forecast',
            'target': 'new',
            'params': {'record_id': self.id}
        }

    def download_csv(self):
        if not self.file or not self.file_name:
            raise ValidationError("No CSV file available for download.")
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%d?download=true' % (self.id),
            'target': 'self',
        }
