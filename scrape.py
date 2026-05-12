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

# import shutil
# from pathlib import Path

# BASE_DIR = Path(__file__).resolve().parent
# today = market_data[1].get("businessDate")

# today_file = BASE_DIR / "Data" / "floorsheet" / f"{today}.json.gz"
# latest_file = BASE_DIR / "Data" / "latest.json.gz"

# if today_file.exists():
#     shutil.copyfile(today_file, latest_file)
#     print(f"Created {latest_file}")
# else:
#     print(f"Could not find {today_file}")