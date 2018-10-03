import os

import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_resumable_upload
import plotly.graph_objs as go
import redis
from dash.dependencies import Input, Output, State
from flask_caching import Cache

import stormwater_harvesting

app = dash.Dash(__name__)
server = app.server
app.config['suppress_callback_exceptions']=True

dash_resumable_upload.decorate_server(server, "uploads")

DF = stormwater_harvesting.parse_dnrm_data(r"notebooks\data\143028A.csv")

CACHE_CONFIG = {
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_URL': os.environ.get('REDIS_URL', 'localhost:6379')
}
cache = Cache()
cache.init_app(server, config=CACHE_CONFIG)

r = redis.from_url(CACHE_CONFIG['CACHE_REDIS_URL'])

app.css.append_css({
    'external_url': 'https://codepen.io/chriddyp/pen/bWLwgP.css',
    # 'external_url': "https://codepen.io/rmarren1/pen/eMQKBW.css",
})
app.title = 'Stormwater Harvesting'

app.layout = html.Div([
    html.Div([
        html.Div([
            html.H2('Stormwater Harvesting'),
            dcc.Graph(id='harvesting'),
        ], className='nine columns'),
        html.Div([
            dcc.Tabs(id="tabs", value='inputs', children=[
                dcc.Tab(label='Inputs', value='inputs'),
                dcc.Tab(label='Results', value='results'),
            ]),
            html.Div(id='tabs-content')
        ], className='three columns'),
    ], className='row'),
])

@cache.memoize()
def do_calcs(demand, max_volume, start_volume, pump_flow):
    harvesting = stormwater_harvesting.harvesting_calcs(
        DF, float(demand), float(max_volume), float(start_volume), float(pump_flow))
    return harvesting

@app.callback(
    Output('harvesting', 'figure'),
    [Input('button', 'n_clicks')],
    [State('demand', 'value'),
     State('max-volume', 'value'),
     State('start-volume', 'value'),
     State('pump-flow', 'value'),
    ],
)
def update_chart(n_clicks, demand, max_volume, start_volume, pump_flow):

    harvesting = do_calcs(
        float(demand), float(max_volume), float(start_volume), float(pump_flow)
        )

    data = [
        go.Scatter(
            x=harvesting.index,
            y=harvesting.Tank_Volume,
            name='tank volume',
        ),
        go.Scatter(
            x=harvesting.index,
            y=harvesting.Demand,
            name='demand flow',
            yaxis='y2',
        ),
        go.Scatter(
            x=harvesting.index,
            y=harvesting.Harvest_Actual,
            name='harvest volume',
        ),
        go.Scatter(
            x=harvesting.index,
            y=harvesting.Discharge,
            name='stream discharge',
            yaxis='y2',
        ),
    ]

    return {
        'data': data,
        'layout': go.Layout(
            xaxis=dict(
                # title='Date',
            ),
            yaxis=dict(
                title='Volume (m3)',
            ),
            yaxis2=dict(
                title='Discharge (m3/s)',
                overlaying='y',
                side='right',
            ),
            margin={'l':50, 't': 20, 'r': 50},
            legend=dict(orientation="h"),
        )
    }

@app.callback(
    Output('tabs-content', 'children'),
    [Input('tabs', 'value')],
    [State('demand', 'value'),
     State('max-volume', 'value'),
     State('start-volume', 'value'),
     State('pump-flow', 'value'),
    ],)
def render_content(tab, demand, max_volume, start_volume, pump_flow):
    if tab == 'inputs':
        return html.Div([
            # html.H3('Inputs'),
            dcc.Markdown('Demand (cumecs):'),
            dcc.Input(
                id='demand',
                placeholder='Enter a value...',
                inputmode='numeric',
                value=0.001
            ),
            dcc.Markdown('Max Tank Volume (m3):'),
            dcc.Input(
                id='max-volume',
                placeholder='Enter a value...',
                inputmode='numeric',
                value=100
            ),
            dcc.Markdown('Starting Tank Volume (m3):'),
            dcc.Input(
                id='start-volume',
                placeholder='Enter a value...',
                inputmode='numeric',
                value=50
            ),
            dcc.Markdown('Pump Flow Rate (cumecs):'),
            dcc.Input(
                id='pump-flow',
                placeholder='Enter a value...',
                inputmode='numeric',
                value=0.05
            ),
            html.Button('Run Simulation', id='button'),
        ])
    elif tab == 'results':

        harvesting = do_calcs(
        float(demand), float(max_volume), float(start_volume), float(pump_flow)
        )
        results = stormwater_harvesting.summarise_results(harvesting)

        return html.Div([
            # html.H3('Results'),
            dcc.Markdown(str(results))
        ])

if __name__ == '__main__':
    app.run_server(debug=True)
