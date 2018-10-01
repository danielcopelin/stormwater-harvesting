import os

import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go
import redis
from dash.dependencies import Input, Output, State
from flask_caching import Cache

import stormwater_harvesting

app = dash.Dash(__name__)
server = app.server

DF = stormwater_harvesting.parse_dnrm_data(r"notebooks\data\143028A.csv")

CACHE_CONFIG = {
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_URL': os.environ.get('REDIS_URL', 'localhost:6379')
}
cache = Cache()
cache.init_app(server, config=CACHE_CONFIG)

r = redis.from_url(CACHE_CONFIG['CACHE_REDIS_URL'])

app.css.append_css({
    'external_url': 'https://codepen.io/chriddyp/pen/bWLwgP.css'
})
app.title = 'Stormwater Harvesting'

app.layout = html.Div([
                dcc.Graph(
                    id='harvesting',
                ),
                dcc.Markdown('Demand (cumecs):'),
                dcc.Input(
                    id='demand',
                    placeholder='Enter a value...',
                    inputmode='numeric',
                    # type='number',
                    value=0.001
                ),
                dcc.Markdown('Max Tank Volume (m3):'),
                dcc.Input(
                    id='max-volume',
                    placeholder='Enter a value...',
                    inputmode='numeric',
                    # type='number',
                    value=100
                ),
                dcc.Markdown('Starting Tank Volume (m3):'),
                dcc.Input(
                    id='start-volume',
                    placeholder='Enter a value...',
                    inputmode='numeric',
                    # type='number',
                    value=50
                ),   
                dcc.Markdown('Pump Flow Rate (cumecs):'),
                dcc.Input(
                    id='pump-flow',
                    placeholder='Enter a value...',
                    inputmode='numeric',
                    # type='number',
                    value=0.05
                ),                
])

@app.callback(
    dash.dependencies.Output('harvesting', 'figure'),
    [dash.dependencies.Input('demand', 'value'),
     dash.dependencies.Input('max-volume', 'value'),
     dash.dependencies.Input('start-volume', 'value'),
     dash.dependencies.Input('pump-flow', 'value'),
    ],
    )
def update_chart(demand, max_volume, start_volume, pump_flow):
    harvesting = stormwater_harvesting.harvesting_calcs(
        DF, float(demand), float(max_volume), float(start_volume), float(pump_flow))

    data = [
        go.Scatter(
            x=harvesting.index, 
            y=harvesting.Tank_Volume, 
            name='tank volume')
    ]

    return {
        'data': data,
        'layout': go.Layout(
            xaxis=dict(
                # range=[0,max_time/np.timedelta64(1, 'm')],
                title='Date',
                # domain=[0,1],
                position=0
            ),
            yaxis=dict(
                # range=[0,max_flow*1.1],
                title='Tank Volume (m3)',
                # domain=[0.0,1]
            ),
            # legend=go.Legend(
            #     orientation='h'
            #     # x=0.5, y=0.9
            #     ),
            # margin={'l':65, 'b': 40, 't': 10, 'r': 0},
            # height=600
        )
        }

if __name__ == '__main__':
    app.run_server(debug=True)
