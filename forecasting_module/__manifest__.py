{
    'name': 'Forecasting Module',
    'version': '18.0.1.0',
    'summary': 'Future Trend Forecasting Tool for Odoo 18',
    'description': 'A module to upload CSV files and generate time-series forecasts using Prophet.',
    'category': 'Tools',
    'author': 'Your Name',
    'license': 'LGPL-3',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/forecasting_views.xml',
        'views/templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'forecasting_module/static/src/js/forecasting.js',
            'forecasting_module/static/src/css/forecasting.css',
            'forecasting_module/static/lib/plotly/plotly.min.js',
        ],
    },
    'installable': True,
    'application': True,
}
