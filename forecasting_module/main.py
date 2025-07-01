from odoo import http
from odoo.http import request
import json
import base64

class ForecastingController(http.Controller):

    @http.route('/forecasting/forecast/<int:record_id>', auth='user', type='json')
    def generate_forecast(self, record_id, **kwargs):
        record = request.env['forecasting.data'].browse(record_id)
        if not record.exists():
            return {'error': 'Record not found'}
        result = record.generate_forecast()
        return result

    @http.route('/forecasting/view/<int:record_id>', auth='user', type='http')
    def view_forecast(self, record_id, **kwargs):
        record = request.env['forecasting.data'].browse(record_id)
        if not record.exists():
            return request.render('forecasting_module.error_template', {'error': 'Record not found'})
        return request.render('forecasting_module.forecast_template', {
            'record': record,
            'plotly_js': '/forecasting_module/static/lib/plotly/plotly.min.js'
        })
