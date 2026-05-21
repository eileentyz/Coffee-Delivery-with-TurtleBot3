"""
Named map-frame waypoints used by the coffee delivery workflow.

Each entry is a position (x, y) and a 2D orientation as a quaternion (z, w).
Retune these to match your own map.
"""

WAYPOINTS = {
    'coffee_station': {
        'x': 8.611273765563965,
        'y': 3.054003953933716,
        'z': 0.0,
        'w': 1.0,
    },
    'delivery_point': {
        'x': -2.029632806777954,
        'y': 2.441532850265503,
        'z': 0.0,
        'w': 1.0,
    },
    'home': {
        'x': 8.405553817749023,
        'y': -3.751394748687744,
        'z': 0.0,
        'w': 1.0,
    },
}
