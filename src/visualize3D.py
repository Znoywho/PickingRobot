from gridMap import initilizeGridMap


import plotly.graph_objects as go
import numpy as np


stationMap, occupied, rack_positions = initilizeGridMap(10, 10, 50)

print(stationMap)

x = []
y = []
for i in rack_positions:
    x.append(i[0])
    y.append(i[1])
x = np.array(x)
y = np.array(y)
z = np.full(len(x), 10)
