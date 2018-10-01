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

])

if __name__ == '__main__':
    app.run_server(debug=True)
