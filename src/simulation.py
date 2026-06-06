import numpy as np

S_WIDTH = 5
S_HEIGHT = 5
station = np.array([[1, 0, 1, 1, 0],
                    [1, 1, 1, 0, 1],
                    [1, 0, 1, 1, 0],
                    [1, 0, 1, 1, 0],
                    [1, 1, 1, 0, 0]])


print("STATION MAP")
print(station)

racks = set()
occupied = []
for r in range(S_WIDTH):
    for j in range(S_HEIGHT):
        if station[r][j] == 1:
            racks.add((r, j))
            occupied.append((r, j))

print("Position of Racks")
print(racks)

print("Occupied Racks")
print(occupied)

MAX_ITEM_QUANTITY = 5
COLLECTION_OF_ITEMS = []

for r in racks:
    QUANTITY_OF_ITEM = np.random.randint(0, MAX_ITEM_QUANTITY + 1)
    items = []
    for _ in range(QUANTITY_OF_ITEM):
        item = np.random.randint(0, 80)
        if item not in items:
            items.append(item)
    COLLECTION_OF_ITEMS.append(items)

print("COLLECTION OF ITEMS")
print(COLLECTION_OF_ITEMS)
