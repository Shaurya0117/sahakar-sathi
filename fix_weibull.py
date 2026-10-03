import re

with open('backend/app/config/constants.py', 'a', encoding='utf-8') as f:
    f.write("\n# Weibull Parameters per Appliance (Characteristic Life in days, Shape factor)\n")
    f.write("# assumed values, not from real data.\n")
    f.write("WEIBULL_PARAMS = {\n")
    f.write("    'Air Conditioner': {'eta': 2500, 'beta': 1.5},\n")
    f.write("    'Ceiling Fan': {'eta': 3600, 'beta': 1.2},\n")
    f.write("    'Plumbing System': {'eta': 4000, 'beta': 2.0},\n")
    f.write("    'Refrigerator': {'eta': 3000, 'beta': 1.5},\n")
    f.write("    'Washing Machine': {'eta': 2000, 'beta': 1.8},\n")
    f.write("    'Electrical Board': {'eta': 5000, 'beta': 1.1},\n")
    f.write("    'General Appliance': {'eta': 3000, 'beta': 1.5}\n")
    f.write("}\n")

with open('backend/app/services/predictive_logistics.py', 'r', encoding='utf-8') as f:
    c = f.read()

c = re.sub(r'# Weibull Parameters per Appliance.*?\"General Appliance\": {\"eta\": 3000, \"beta\": 1.5}\n\}', 'from app.config.constants import WEIBULL_PARAMS', c, flags=re.DOTALL)

with open('backend/app/services/predictive_logistics.py', 'w', encoding='utf-8') as f:
    f.write(c)
print("Done")
