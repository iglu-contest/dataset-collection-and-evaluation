"""Default world changes for an IGLU tasks.

Each variable defines a change that will be placed on top of the generated world. There
are two types of changes: block addition or player attributes change.

A block is defined by its x,y,z coordinates and block type. Pitch and way coordinates
are also included for compatibility.

In this case, the building zone with the partially built structure is placed in the
center of the grid. The agent (builder) spans in the 0, 0 coordinate.

The x coordinate increases towards east.
The y coordinate increases towards the sky.
The z coordinate increases towards south.
"""

from types import MappingProxyType


CARDINAL_LETTERS_BLOCK_CHANGES = MappingProxyType({
    # West cardinal letter
    "[-10.0,0.0,-3.0,0.0,0.0]": { "type": 11 },
    "[-10.0,0.0,-2.0,0.0,0.0]": { "type": 11 },
    "[-10.0,0.0,-1.0,0.0,0.0]": { "type": 11 },
    "[-10.0,0.0,0.0,0.0,0.0]": { "type": 11 },
    "[-11.0,0.0,1.0,0.0,0.0]": { "type": 11 },
    "[-11.0,0.0,0.0,0.0,0.0]": { "type": 11 },
    "[-12.0,0.0,-1.0,0.0,0.0]": { "type": 11 },
    "[-13.0,0.0,0.0,0.0,0.0]": { "type": 11 },
    "[-13.0,0.0,1.0,0.0,0.0]": { "type": 11 },
    "[-14.0,0.0,0.0,0.0,0.0]": { "type": 11 },
    "[-14.0,0.0,-1.0,0.0,0.0]": { "type": 11 },
    "[-14.0,0.0,-2.0,0.0,0.0]": { "type": 11 },
    "[-14.0,0.0,-3.0,0.0,0.0]": { "type": 11 },

    # East cardinal letter
    "[10.0,0.0,-3.0,0.0,0.0]": { "type": 11 },
    "[10.0,0.0,-2.0,0.0,0.0]": { "type": 11 },
    "[10.0,0.0,-1.0,0.0,0.0]": { "type": 11 },
    "[10.0,0.0,0.0,0.0,0.0]": { "type": 11 },
    "[10.0,0.0,1.0,0.0,0.0]": { "type": 11 },
    "[12.0,0.0,-3.0,0.0,0.0]": { "type": 11 },
    "[13.0,0.0,-3.0,0.0,0.0]": { "type": 11 },
    "[11.0,0.0,-3.0,0.0,0.0]": { "type": 11 },
    "[11.0,0.0,-1.0,0.0,0.0]": { "type": 11 },
    "[12.0,0.0,-1.0,0.0,0.0]": { "type": 11 },
    "[11.0,0.0,1.0,0.0,0.0]": { "type": 11 },
    "[12.0,0.0,1.0,0.0,0.0]": { "type": 11 },
    "[13.0,0.0,1.0,0.0,0.0]": { "type": 11 },

    # North cardinal letter
    "[0.0,0.0,-13.0,0.0,0.0]": { "type": 11 },
    "[-1.0,0.0,-14.0,0.0,0.0]": { "type": 11 },
    "[2.0,0.0,-12.0,0.0,0.0]": { "type": 11 },
    "[-2.0,0.0,-15.0,0.0,0.0]": { "type": 11 },
    "[-2.0,0.0,-14.0,0.0,0.0]": { "type": 11 },
    "[-2.0,0.0,-13.0,0.0,0.0]": { "type": 11 },
    "[-2.0,0.0,-12.0,0.0,0.0]": { "type": 11 },
    "[-2.0,0.0,-11.0,0.0,0.0]": { "type": 11 },
    "[2.0,0.0,-15.0,0.0,0.0]": { "type": 11 },
    "[2.0,0.0,-14.0,0.0,0.0]": { "type": 11 },
    "[2.0,0.0,-13.0,0.0,0.0]": { "type": 11 },
    "[2.0,0.0,-11.0,0.0,0.0]": { "type": 11 },
    "[1.0,0.0,-12.0,0.0,0.0]": { "type": 11 },

    # South cardinal letter
    "[0.0,0.0,14.0,0.0,0.0]": { "type": 11 },
    "[-2.0,0.0,14.0,0.0,0.0]": { "type": 11 },
    "[0.0,0.0,12.0,0.0,0.0]": { "type": 11 },
    "[1.0,0.0,10.0,0.0,0.0]": { "type": 11 },
    "[0.0,0.0,10.0,0.0,0.0]": { "type": 11 },
    "[-1.0,0.0,10.0,0.0,0.0]": { "type": 11 },
    "[-2.0,0.0,11.0,0.0,0.0]": { "type": 11 },
    "[-1.0,0.0,12.0,0.0,0.0]": { "type": 11 },
    "[1.0,0.0,13.0,0.0,0.0]": { "type": 11 },
    "[-1.0,0.0,14.0,0.0,0.0]": { "type": 11 },
})

# Floor is a grid from -5 to 5 in x and z direction composed of blocks with id 71
FLOOR_BLOCK_CHANGES = MappingProxyType({f"[{float(x)},0.0,{float(z)},0.0,0.0]": {"type": 71}
    for x in range(-5,6)
    for z in range(-5,6)})


ARCHITECT_ATTRIBUTES = MappingProxyType({
    "spawnLocation": {
        "x": -12.0,
        "z": 14.0,
        "y": 1.0,
        "pitch": 0.0,
        "yaw": -180.0
    }
})


BUILDER_ATTRIBUTES = MappingProxyType({
    "spawnLocation": {
        "x": -6,
        "z": 6,
        "y": 1.0,
        "pitch": 0.0,
        "yaw": -180.0
    },
    "movementRegion": {
        "origin": {
            "x": -7.0,
            "z": -7.0,
            "y": 0.0,
            "pitch": 0.0,
            "yaw": 0.0
        },
        "size": {
            "x": 15.0,
            "z": 15.0,
            "y": 100.0,
            "pitch": 0.0,
            "yaw": 0.0
        }
    }
})