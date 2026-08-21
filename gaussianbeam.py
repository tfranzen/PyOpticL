from PyOpticL.library import adapters, hardware, isomet, optics, thorlabs, Baseplate
from PyOpticL.beam_path import BeamPath
from PyOpticL.layout import Component, Layout
from PyOpticL import utils
from PyOpticL.utils import Dimension as dim
from PyOpticL import settings

utils.fix_relative_imports()

import os, sys; sys.path.append(os.path.dirname(os.path.realpath(__file__)))

sys.path.append("/Users/evazheng/Documents/GitHub/yqn_optics")

from library import realop, custom, vexlum, additional
import numpy as np

from importlib import reload

reload(realop)
reload(custom)
reload(vexlum)
reload(additional)

settings.set_measurement_system("metric")
reload(utils)

WAVELENGTH = 459
MFD=4.93e-3

layout = Layout("gaussianbeam")

baseplate = Component(
    label="Baseplate",
    definition=Baseplate(dimensions=(dim(200, "mm"), dim(500, "mm"), dim(50,'mm') - dim(.5, "in")),
        optical_height=dim(0.5, "in"),
        grid_offset=(0, 0),
        #mount_holes=[(2, 2), (2, 7)]
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
    position=(50, 0, 0),
    rotation=(0, 0, 90)
)

collimator = realop.fiber_collimator(
    diameter = 5,
    focal_length = 30,#110,
    mount_definition=realop.mirror_mount_zjb_05_2(drill_depth=dim(5,'mm'), alternate_orientation=True),
    stop = False,
)

collimator_component = Component(label="Fibre Collimator", definition=collimator)

beam_path.add(
    collimator_component,
    beam_index=0b1,
    distance=dim(collimator.focal_length, "mm"),
    rotation=(0, 0, 90)
)

aod = additional.aa_optoelectronic_aod(
    v_rf_frequencies = [76, 100, 126],
    h_rf_frequencies = [76, 100, 126],
    orders = [1],
    order_powers = [.7],
    rotate_beambend=False
)

aod_component = Component(label="AOD", definition=aod) # Allows beam properties to be measured

beam_path.add(
    aod_component,
    beam_index=0b1,
    distance=dim(70, "mm"),
    rotation=(0, 0, -90),
    offset=(1, 0),
)

""" # FOR TESTING
lens1 = optics.Spherical_Lens(
    diameter=dim(1, "in"),
    thickness=dim(4, "mm"),
    focal_length=50
)

beam_path.add(
    Component(label="Lens1", definition=lens1),
    beam_index=0b10101,
    distance=dim(100,"mm"),
    rotation=(0, 0, 90),
)

test_point = custom.test_point(
    diameter=dim(1, "in")
)

test_point_component = Component(label="Test Point", definition=test_point)

beam_path.add(
    test_point_component,
    beam_index=0b10101,
    distance=dim(60, "mm"),
    rotation=(0, 0, 90)
)

"""

# 001, 10101


mirror = optics.Circular_Mirror(
    diameter=dim(1, "in"),
    thickness=dim(4, "mm"),
    # mount_definition=realop.mirror_mount_zjb_05_2(drill_depth=dim(5, "mm"), alternate_orientation=False)
)
 
lens1 = optics.Spherical_Lens(
    diameter=dim(1, "in"),
    thickness=dim(4, "mm"),
    focal_length=70
)


lens2 = optics.Spherical_Lens(
    diameter=dim(1, "in"),
    thickness=dim(4, "mm"),
    focal_length=225
)

lens3 = optics.Spherical_Lens(
    diameter=dim(1, "in"),
    thickness=dim(4, "mm"),
    focal_length=120
)

#beam_path.add(
#Component(label="Lens1", definition=lens1),
#beam_index=0b001, #10101
#distance=dim(200-2*13.8, "mm"),
#rotation=(0, 0, 90),
#offset=(0, 0)
#)

beam_path.add(
    Component(label="Lens2", definition=lens2),
    beam_index=0b10101,
    distance=dim(-13.8*2+lens2.focal_length, "mm"),
    rotation=(0, 0, 90),
    offset=(0.5, 0)
)

beam_path.add(
    Component(label="Mirror1", definition=mirror),
    beam_index=0b10101,
    distance=dim(100, "mm"),
    rotation=(0, 0, -45)
)

beam_path.add(
    Component(label="Mirror2", definition=mirror),
    beam_index=0b10101,
    distance=dim(100, "mm"),
    rotation=(0, 0, -135)
)

beam_path.add(
    Component(label="Lens3", definition=lens3),
    beam_index=0b10101,
    distance=dim(lens2.focal_length+lens3.focal_length-200, "mm"),
    rotation=(0, 0, 90),
)

pbs = optics.Beamsplitter_Cube(
    side_length=dim(.5, "in"),
    ref_polarization=1, # CHECK: vertical polarisation
    rotate_cube=True,
    # mount_definition=custom.pbs_mount(drill_depth=dim(5, "mm")),
    # mount_offset=(-6, -2, -7)
)

beam_path.add(
    Component(label="PBS1", definition=pbs),
    beam_index=0b10101,
    distance=dim(30, "mm"),
    rotation=(0, 0, -90),
    offset=(0,-0.7)
)

beam_path.add(
    Component(label="PBS2", definition=pbs),
    beam_index=0b101010,
    distance=dim(30, "mm"),
    rotation=(0, 0, -90),
    offset=(0,-0.7)
)

#beam_path.add(
#Component(label="Mirror", definition=mirror),
#beam_index=0b0010,
#distance=dim(30, "mm"),
#rotation=(0, 0, -45)
#)

objective = additional.objective()

objective_component=Component(label="Objective", definition=objective)

beam_path.add(
    objective_component,
    beam_index=0b101010,
    distance=dim(15.4+60, "mm"),
    rotation=(0, 0, 90),
    offset=(0, 0),
)

if __name__ == "__main__":
    layout.recompute()
    
