from PyOpticL.library import adapters, hardware, isomet, optics, thorlabs, Baseplate
from PyOpticL.beam_path import BeamPath
from PyOpticL.layout import Component, Layout
from PyOpticL import settings
from PyOpticL import utils
from PyOpticL.utils import Dimension as dim

utils.fix_relative_imports()

import os, sys; sys.path.append(os.path.dirname(os.path.realpath(__file__)))

sys.path.append("/Users/evazheng/Documents/GitHub/yqn_optics")

from library import realop, custom, vexlum, additional
import numpy as np

from importlib import reload

settings.set_measurement_system("metric")
reload(utils)

reload(realop)
reload(custom)
reload(vexlum)
reload(additional)


WAVELENGTH = 459
MFD=4.93e-3

layout = Layout("mirror_contraption")

baseplate = Component(
    label="Baseplate",
    definition=Baseplate(
        dimensions=(dim(300, "mm"), dim(500, "mm"), dim(25,"mm")),
        optical_height=dim(0.5, "in"),
        grid_offset=(0, 0),
    )
)

stage = Component(
    label="Stage",
    definition=Baseplate(
        dimensions=(dim(90, "mm"), dim(110, "mm"), dim(25, "mm")),
        optical_height=dim(0.5, "in"),
        grid_offset=(0, 0)
    )
)

stage_baseplate = Component(
    label="Stage_Baseplate",
    definition=Baseplate(
        dimensions=(dim(75, "mm"), dim(100, "mm"), dim(25, "mm")),
        optical_height=dim(0.5, "in"),
        grid_offset=(0, 0)
    )
)
    
layout.add(baseplate, (0, 0, 0), (0, 0, 0))
baseplate.add(stage, (200, -225, 0), (0, 0, 0))
baseplate.add(stage_baseplate, (200, -225, 25), (0, 0, 0))

beam_path = baseplate.add(
    BeamPath(
        label="Beam Path",
        waist=dim(MFD, "mm"),
        waist_position=dim(1, "mm"),
        wavelength=WAVELENGTH,
        polarization=((1, 0), (1, 0))
    ),
    position=(50, -100, 0),
    rotation=(0, 0, 90)
)

collimator = realop.fiber_collimator(
    diameter = 5,
    focal_length = 110,#110,
    mount_definition=realop.mirror_mount_zjb_05_2(drill_depth=dim(5,'mm'), alternate_orientation=True),
    stop = False,
)

Fibre_Collimator = Component(label="Fibre_Collimator", definition=collimator)

beam_path.add(
    Fibre_Collimator,
    beam_index=0b1,
    distance=dim(collimator.focal_length, "mm"),
    rotation=(0, 0, 90)
)

aod = additional.aa_optoelectronic_aod(rf_frequencies = [101], #[96, 106],
    orders = [1],
    order_powers = [.7],
    rotate_beambend=False
)

AOD = Component(label="AOD", definition=aod) # Allows beam properties to be measured

beam_path.add(
    AOD,
    beam_index=0b1,
    distance=dim(70, "mm"),
    rotation=(0, 0, -90),
    offset=(1, 0),
)

mirror = optics.Circular_Mirror(
    diameter=dim(0.5, "in"),
    thickness=dim(4, "mm"),
    mount_definition=realop.mirror_mount_zjb_05_2(drill_depth=dim(5, "mm"), alternate_orientation=False)
)


lens1 = optics.Spherical_Lens(
    diameter=dim(0.5, "in"),
    thickness=dim(4, "mm"),
    focal_length=75
)

lens2 = optics.Spherical_Lens(
    diameter=dim(0.5, "in"),
    thickness=dim(4, "mm"),
    focal_length=40
)

lens3=optics.Spherical_Lens(
    diameter=dim(0.5, "in"),
    thickness=dim(4, "mm"),
    focal_length=300 
)

beam_path.add(
    Component(label="Lens1", definition=lens1),
    beam_index=0b001,
    distance=dim(-13.8*2+lens1.focal_length, "mm"),
    rotation=(0, 0, 90),
    offset=(0.5, 0)
)

beam_path.add(
    Component(label="Lens2", definition=lens2),
    beam_index=0b001,
    distance=dim(lens1.focal_length+lens2.focal_length, "mm"),
    rotation=(0, 0, 90),
)

beam_path.add(
    Component(label="Mirror1", definition=mirror),
    beam_index=0b001,
    distance=dim(200, "mm"),
    rotation=(0, 0, -45)
)

Lens3 = Component(label="Lens3", definition=lens3)

beam_path.add(
    Lens3,
    beam_index=0b001,
    distance=dim(140, "mm"),
    rotation=(0, 0, 0),
)

beam_path.add(
    Component(label="Mirror2", definition=mirror),
    beam_index=0b001,
    distance=dim(35, "mm"),
    rotation=(0, 0, -135)
)

beam_path.add(
    Component(label="Lens4", definition=lens3),
    beam_index=0b001,
    distance=dim(600-35, "mm"),
    rotation=(0, 0, 90),
)

# STAGE
"""
bare_mirror = optics.Circular_Mirror(
    diameter=dim(0.5, "in"),
    thickness=dim(4, "mm"),
)

peri = additional.periscope(
    vertical_displacement=dim(25, "mm"),
    mirror_height=dim(25, "mm"),
    mirror_width=dim(75, "mm")
)

Bare_Mirror1 = Component(label="Bare_Mirror1", definition=bare_mirror)

beam_path.add(
    Bare_Mirror1,
    beam_index=0b001,
    distance=dim(50, "mm"),
    rotation=(0, 0, 150)
)

Periscope = Component(label="Periscope", definition=peri)

beam_path.add(
    Periscope,
    beam_index=0b001,
    distance=dim(75, "mm"),
    rotation=(0, 0, 30),
    offset=(0, 0)
)

#baseplate.add(
#    Periscope,
#    position=(165, -170, 0),
#    rotation=(0, 0, 30)
#)
    
Bare_Mirror2 = Component(label="Bare_Mirror2", definition=bare_mirror)

beam_path.add(
    Bare_Mirror2,
    beam_index=0b001,
    distance=dim(75.1, "mm"),
    rotation=(0, 0, -120)
)

Bare_Mirror3 = Component(label="Bare_Mirror3", definition=mirror)

beam_path.add(
    Bare_Mirror3,
    beam_index=0b001,
    distance=dim(50, "mm"),
    rotation=(0, 0, 45)
) 

objective = additional.objective()

objective_component=Component(label="Objective", definition=objective)

beam_path.add(
    objective_component,
    beam_index=0b001,
    distance=dim(25+15.4, "mm"),
    rotation=(0, 0, 180),
    offset=(0, 0)
)
"""
stage_baseplate.add(
    Component(
        label="hole",
        definition=additional.baseplate_hole(
            dim(25, "mm"),
            dim(25, "mm"),
            dim(23, "mm")
        )
    ),
    position=(10, 75, -28),
    rotation=(0, 0, 0)
)

stage_baseplate.add(
    Component(
        label="hole",
        definition=additional.baseplate_hole(
            dim(25, "mm"),
            dim(75, "mm"),
            dim(23, "mm")
        )
    ),
    position=(25, 100, -28),
    rotation=(0, 0, 0)
)

stage_beam_path = baseplate.add(
    BeamPath(
        label="Beam Path",
        waist=dim(MFD, "mm"),
        waist_position=dim(1, "mm"),
        wavelength=WAVELENGTH,
        polarization=((1, 0), (1, 0)),     
    ),
    position=(0, 0, 0),
    rotation=(0, 0, 90)
)

#path_length=sum([beam_path.measure_properties(Lens3).segment_length, 
#    beam_path.measure_properties(Bare_Mirror1).segment_length*2, 
#    peri.vertical_displacement, 
#    beam_path.measure_properties(Bare_Mirror2).segment_length,
#    beam_path.measure_properties(Bare_Mirror3).segment_length
#    ])
    
#print(path_length)

#120

if __name__ == "__main__":
    layout.recompute()
    
