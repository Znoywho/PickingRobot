import numpy as np


# INITILIZE
def initilizeGridMap(w, h, n_r):

    GRID_MAP = np.zeros((w, h), dtype=int)

    occupied = set()
    rack_positions = []

    while len(rack_positions) < n_r:
        x, y = np.random.randint(0, w - 1), np.random.randint(0, h - 1)
        if (x, y) not in occupied:
            occupied.add((x, y))
            rack_positions.append((x, y))

            GRID_MAP[x][y] = 1
    return GRID_MAP, occupied, rack_positions
