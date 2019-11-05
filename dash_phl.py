# -*- coding: utf-8 -*-

import dash
import pandas as pd

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
-RPS precent by year (table)?
"""