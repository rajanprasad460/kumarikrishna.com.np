import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

#%% Importing modules 

try:
    from nepse import Nepse
except ImportError:
    import sys
    sys.path.append("../")
    from nepse import Nepse


#%% Get today prices
nepse = Nepse()

# Disable TLS verification
nepse.setTLSVerification(False)
# This is market depth analysis
market_data = nepse.getPriceVolumeHistory()

    
    
#%% Get Floorsheet
floorsheet = nepse.getFloorSheet()

# floorsheet = nepse.getFloorSheet(Type='xlsx')

#%%
import gzip
import json

file_path = "Data/floorsheet/2026-05-12.json.gz"

with gzip.open(file_path, "rt", encoding="utf-8") as f:
    data = json.load(f)

print(len(data))