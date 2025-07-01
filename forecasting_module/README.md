# Forecasting Module for Odoo 18

A module to upload CSV files and generate time-series forecasts using Prophet, integrated with Odoo 18.

## Setup Instructions

### GitHub Codespaces
1. Create a GitHub repository and clone it in Codespaces.
2. Install Odoo 18:
   ```bash
   sudo apt update
   sudo apt install -y python3-pip
   pip install -r requirements.txt
   wget https://nightly.odoo.com/18.0/nightly/deb/odoo_18.0.latest_all.deb
   sudo dpkg -i odoo_18.0.latest_all.deb
cat << 'EOF' > forecasting_module/__manifest__.py
{
    'name': 'Forecasting Module',
    'version': '1.0',
    'summary': 'Future Trend Forecasting Tool for Odoo 18',
    'description': 'A module to upload CSV files and generate time-series forecasts using Prophet.',
    'category': 'Tools',
    'author': 'Your Name',
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
