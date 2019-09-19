# -*- coding: utf-8 -*-

import dash
import dash_table
import dash_daq as daq
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Output, Input, State
import plotly.graph_objs as go
import pandas as pd
import plotly.tools as tls
import json as json_func

# --- Module Imports ---
import resources
import functions

# --- Hide SettingWithCopy Warnings --- 
pd.set_option('chained_assignment',None)

# --- Server ---
server = functions.app.server

# --- Run on Import ---
if __name__ == "__main__":
    functions.app.run_server(debug=False)

"""
TODO:
-Revisit Incremental purchase requirement
-Clean up layout
-RPS precent by year (table)?
-Remove FIT percent input
-Add FiT to Table RE PCT requirement
"""