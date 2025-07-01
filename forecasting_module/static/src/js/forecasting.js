odoo.define('forecasting_module.forecasting', function (require) {
    "use strict";

    var publicWidget = require('web.public.widget');

    publicWidget.registry.ForecastingWidget = publicWidget.Widget.extend({
        selector: '.container',
        start: function () {
            var self = this;
            var record_id = this.$el.find('#forecast-chart').closest('.container').data('record-id');
            if (record_id) {
                this._rpc({
                    route: '/forecasting/forecast/' + record_id,
                    params: {}
                }).then(function (result) {
                    if (result.error) {
                        alert(result.error);
                        return;
                    }
                    self.renderCharts(result);
                    self.renderTable(result);
                });
            }
            return this._super.apply(this, arguments);
        },

        renderCharts: function (data) {
            var plotType = this.$el.find('#forecast-chart').closest('.container').data('plot-type') || 'line';
            var plotTheme = this.$el.find('#forecast-chart').closest('.container').data('plot-theme') || 'plotly_white';
            var period = this.$el.find('#forecast-chart').closest('.container').data('period') || 'quarterly';
            var fiveYear = this.$el.find('#forecast-chart').closest('.container').data('five-year') === 'true';

            // Forecast Chart
            var forecastTrace = {
                x: data.forecast.map(d => new Date(d.ds)),
                y: data.forecast.map(d => d.yhat),
                mode: plotType === 'line' ? 'lines' : 'none',
                name: 'Future Forecast',
                line: {color: 'red'}
            };
            if (plotType === 'bar') {
                forecastTrace.type = 'bar';
                forecastTrace.marker = {color: 'red'};
            }
            var historicalTrace = {
                x: data.historical.map(d => new Date(d.ds)),
                y: data.historical.map(d => d.y),
                mode: plotType === 'line' ? 'lines' : 'none',
                name: 'Historical',
                line: {color: 'blue'}
            };
            if (plotType === 'bar') {
                historicalTrace.type = 'bar';
                historicalTrace.marker = {color: 'blue'};
            }
            var upperTrace = {
                x: data.forecast.map(d => new Date(d.ds)),
                y: data.forecast.map(d => d.yhat_upper),
                mode: 'lines',
                line: {color: 'rgba(255,0,0,0.2)'},
                name: 'Upper CI',
                showlegend: plotType === 'line'
            };
            var lowerTrace = {
                x: data.forecast.map(d => new Date(d.ds)),
                y: data.forecast.map(d => d.yhat_lower),
                mode: 'lines',
                fill: 'tonexty',
                line: {color: 'rgba(255,0,0,0.2)'},
                name: 'Lower CI',
                showlegend: plotType === 'line'
            };
            Plotly.newPlot('forecast-chart', [historicalTrace, forecastTrace, upperTrace, lowerTrace], {
                title: `Future ${period.charAt(0).toUpperCase() + period.slice(1)} Trend Forecast ${fiveYear ? '(5 Years)' : ''}`,
                xaxis: {title: 'Date'},
                yaxis: {title: 'Value'},
                template: plotTheme,
                hovermode: 'x unified'
            });

            // Bar Chart
            var barData = {};
            data.forecast.forEach(d => {
                var periodKey = new Date(d.ds).toISOString().slice(0, period === 'yearly' ? 4 : 7);
                if (!barData[periodKey]) barData[periodKey] = [];
                barData[periodKey].push(d.yhat);
            });
            var barTrace = {
                x: Object.keys(barData),
                y: Object.values(barData).map(vals => vals.reduce((a, b) => a + b) / vals.length),
                type: 'bar',
                name: 'Forecast Mean',
                marker: {color: 'red'}
            };
            Plotly.newPlot('bar-chart', [barTrace], {
                title: `Mean Forecast per ${period.charAt(0).toUpperCase() + period.slice(1)} Period ${fiveYear ? '(5 Years)' : ''}`,
                xaxis: {title: 'Period'},
                yaxis: {title: 'Value'},
                template: plotTheme
            });

            // Full Forecast Chart
            var trainTrace = {
                x: data.train.map(d => new Date(d.ds)),
                y: data.train.map(d => d.y),
                mode: plotType === 'line' ? 'lines' : 'none',
                name: 'Train',
                line: {color: 'blue'}
            };
            if (plotType === 'bar') {
                trainTrace.type = 'bar';
                trainTrace.marker = {color: 'blue'};
            }
            var testTrace = {
                x: data.test.map(d => new Date(d.ds)),
                y: data.test.map(d => d.y),
                mode: plotType === 'line' ? 'lines' : 'none',
                name: 'Test',
                line: {color: 'green hills
            };
            if (plotType === 'bar') {
                testTrace.type = 'bar';
                testTrace.marker = {color: 'green'};
            }
            var fullForecastTrace = {
                x: data.full_forecast.map(d => new Date(d.ds)),
                y: data.full_forecast.map(d => d.yhat),
                mode: plotType === 'line' ? 'lines' : 'none',
                name: 'Forecast',
                line: {color: 'red'}
            };
            if (plotType === 'bar') {
                fullForecastTrace.type = 'bar';
                fullForecastTrace.marker = {color: 'red'};
            }
            var fullUpperTrace = {
                x: data.full_forecast.map(d => new Date(d.ds)),
                y: data.full_forecast.map(d => d.yhat_upper),
                mode: 'lines',
                line: {color: 'rgba(0,100,80,0.2)'},
                name: 'Upper CI',
                showlegend: plotType === 'line'
            };
            var fullLowerTrace = {
                x: data.full_forecast.map(d => new Date(d.ds)),
                y: data.full_forecast.map(d => d.yhat_lower),
                mode: 'lines',
                fill: 'tonexty',
                line: {color: 'rgba(0,100,80,0.2)'},
                name: 'Lower CI',
                showlegend: plotType === 'line'
            };
            Plotly.newPlot('full-forecast-chart', [trainTrace, testTrace, fullForecastTrace, fullUpperTrace, fullLowerTrace], {
                title: `Full ${period.charAt(0).toUpperCase() + period.slice(1)} Forecast (RMSE: ${data.metrics.rmse || 'N/A'}, MAE: ${data.metrics.mae || 'N/A'}, MAPE: ${data.metrics.mape || 'N/A'}%)`,
                xaxis: {title: 'Date'},
                yaxis: {title: 'Value'},
                template: plotTheme,
                hovermode: 'x unified'
            });

            // Trend Components Chart
            var trendTrace = {
                x: data.full_forecast.map(d => new Date(d.ds)),
                y: data.full_forecast.map(d => d.trend),
                mode: 'lines',
                name: 'Trend',
                line: {color: 'blue'}
            };
            var traces = [trendTrace];
            if (data.yearly_seasonality.length) {
                traces.push({
                    x: data.yearly_seasonality.map(d => new Date(d.ds)),
                    y: data.yearly_seasonality.map(d => d.yearly),
                    mode: 'lines',
                    name: 'Yearly Seasonality',
                    line: {color: 'green'}
                });
            }
            if (data.holidays.length) {
                traces.push({
                    x: data.holidays.map(d => new Date(d.ds)),
                    y: data.holidays.map(d => d.holidays),
                    mode: 'lines',
                    name: 'Holidays',
                    line: {color: 'orange'}
                });
            }
            Plotly.newPlot('trend-components-chart', traces, {
                title: 'Trend and Seasonality Components',
                xaxis: {title: 'Date'},
                yaxis: {title: 'Value'},
                template: plotTheme
            });
        },

        renderTable: function (data) {
            var tbody = this.$el.find('#forecast-table');
            tbody.empty();
            data.forecast.forEach(function (row) {
                tbody.append(
                    `<tr>
                        <td>${new Date(row.ds).toISOString().slice(0, 10)}</td>
                        <td>${row.yhat.toFixed(2)}</td>
                        <td>${row.yhat_lower.toFixed(2)}</td>
                        <td>${row.yhat_upper.toFixed(2)}</td>
                    </tr>`
                );
            });
            var csvContent = 'Date,Forecast,Lower CI,Upper CI\n' + data.forecast.map(row =>
                `${new Date(row.ds).toISOString().slice(0, 10)},${row.yhat.toFixed(2)},${row.yhat_lower.toFixed(2)},${row.yhat_upper.toFixed(2)}`
            ).join('\n');
            var downloadLink = this.$el.find('#download-csv');
            downloadLink.attr('href', 'data:text/csv;charset=utf-8,' + encodeURIComponent(csvContent));
            downloadLink.attr('download', `future_${this.$el.find('#forecast-chart').closest('.container').data('period')}_forecast${this.$el.find('#forecast-chart').closest('.container').data('five-year') === 'true' ? '_5years' : ''}.csv`);
        }
    });

    return publicWidget.registry.ForecastingWidget;
});
