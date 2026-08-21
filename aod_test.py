"""
Notes:

- The distance between the first two bolts on the AOD is 40.5mm as per the data sheet but in reality is 41mm.
- If 3D printing with PLA, set mirror mount drill depth to be the height of the baseplate so it can be mounted by screwing from the bottom. 
- Check the mounting holes are the right distance as sometimes the grid units fail to change to metric. (IF APPROVED ON DISCORD, WORK ON IMPLEMENTING IT EVERYWHERE BY CHANGING IMPORT STATEMENTS.)
"""

from PyOpticL.library import adapters, hardware, isomet, optics, thorlabs, Baseplate
from PyOpticL.beam_path import BeamPath
from PyOpticL.layout import Component, Layout
from PyOpticL import utils
from PyOpticL.settings import Dimension as dim
from PyOpticL import settings

utils.fix_relative_imports()

import os, sys; sys.path.append(os.path.dirname(os.path.realpath(__file__)))

sys.path.append("/Users/evazheng/Documents/GitHub/yqn_optics")

from library import realop, custom, additional
from modules import half_inch_optics as opt

import numpy as np

from importlib import reload

reload(realop)
reload(custom)
reload(additional)

#print(settings.conversion_factors)

settings.set_measurement_system("metric")

print(settings.get_measurement_system())

#print(settings.conversion_factors)

WAVELENGTH = 459
MFD=4.93e-3

layout = Layout("AOD_Test")

baseplate = Component(
    label="Baseplate",
    definition=Baseplate(
        dimensions=(dim(200, "mm"), dim(200, "mm"), dim(25,"mm")),
        optical_height=dim(0.5, "in"),
        grid_offset=(0, 0),
        mount_holes=[(0.5, 1), (7.5, 1), (0.5, 6), (7.5, 6)]
    )
)

layout.add(baseplate, (0, 0, 0), (0, 0, 0))

beam_path = baseplate.add(
    BeamPath(
        label="Beam Path",
        waist=dim(MFD, "mm"),
        waist_position=dim(1, "mm"),
        wavelength=WAVELENGTH,
        polarization=((1, 0), (1, 0))
    ),
    position=(25+12.5, 0, 0),
    rotation=(0, 0, 90)
)

cage_plate = realop.cage_plate_sp02(
    bolt=False,
    drill_depth=dim(0, "mm")
)

baseplate.add(
    Component(label="Cage Plate", definition=cage_plate),
    position=(25+12.5, 1.5, 0),
    rotation=(0, 0, 90)
)

lens = opt.lens(
    focal_length=dim(100, "mm"),
    mount_definition=opt.cage_segment(
        overhang=95,
        bracket_positions=[-107.5+25*i for i in range(1, 6)],
        length=dim(5, "in"),
    ),
)

beam_path.add(
    Component(label="Lens1", definition=lens),
    beam_index=0b1,
    distance=dim(lens.focal_length, "mm"),
    rotation=(0, 0, 90)
)

mirror = optics.Circular_Mirror(
    diameter=dim(0.5, "in"),
    thickness=dim(4, "mm"),
    mount_definition=realop.mirror_mount_zjb_05_2(drill_depth=dim(8, "mm"), alternate_orientation=False) # 5mm not deep enough- needs to be like at least 7mm.
)

beam_path.add(
    Component(label="Mirror1", definition=mirror),
    beam_index=0b1,
    distance=dim(75, "mm"),
    rotation=(0, 0, -45)
)

beam_path.add(
    Component(label="Mirror2", definition=mirror),
    beam_index=0b1,
    distance=dim(125, "mm"),
    rotation=(0, 0, -135)
)

aod = additional.aa_optoelectronic_aod(
    rf_frequencies = [96,101,106], #[96, 106],
    orders = [1],
    order_powers = [.7],
    rotate_beambend = True
)

beam_path.add(
    Component(label="AOD", definition=aod),
    beam_index=0b1,
    distance=dim(50, "mm"),
    rotation=(0, 0, 90),
    offset=(1, 0)
)

stop = custom.beam_block(
    diameter=dim(10, "mm")
)

beam_path.add(
    Component(label="Stop", definition=stop),
    beam_index=0b10101,
    distance=dim(83.6, "mm"),
    rotation=(0, 0, 90),
    offset=(1, 0)
)

if __name__ == "__main__":
    layout.recompute()

# fix mounting holes 