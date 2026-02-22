import FreeCAD as App
import numpy as np
import warnings
import Part

from PyOpticL.beam_path import Lens, Reflection, Retarder, Dummy, Dump
from PyOpticL.icons import optic_icon, thorlabs_icon
from PyOpticL.layout import Component
from PyOpticL.layout import Dimension as dim
from PyOpticL.utils import (
    bolt_shape,
    bolt_slot_shape,
    box_shape,
    cylinder_shape,
    import_model,
    subcomponent,
)

from PyOpticL import settings

##########################
### Example Components ###
##########################


class example_component:
    """
    An example component class for reference on creating new components
    creates a simple cube which mounts using a single bolt

    Args:
        side_length (float): The side length of the cube
        height (float): The height of the cube
        drill_depth (float): The depth of the mounting hole
    """

    object_group = "example"
    object_icon = ""
    object_color = (0.5, 0.5, 0.5)

    def __init__(
        self,
        side_length: dim,
        height: dim,
        drill_depth: dim,
    ):
        """Initialize adjustable parameters"""
        self.side_length = side_length
        self.height = height
        self.drill_depth = drill_depth

    def subcomponents(self) -> list[subcomponent]:
        """Define any sub-components"""
        return [
            subcomponent(
                component=Component(
                    "Mounting Bolt",
                    bolt("8_32", length=self.height + self.drill_depth),
                ),
                position=(0, 0, self.height),
                rotation=(0, 0, 0),
            )
        ]

    def shape(self) -> Part.Shape:
        """Define the main shape of the component"""
        part = box_shape(
            dimensions=(self.side_length, self.side_length, self.height),
            position=(0, 0, 0),
            center=(0, 0, -1),
            fillet=1,
        )
        return part


############################
### Baseplate Components ###
############################


class baseplate:
    """
    Standard optical baseplate

    Args:
        dimensions (tuple): The (x, y, z) dimensions of the baseplate
        optical_height (dimension): beam height over baseplate
        mounting_holes (list): locations for counterbored holes for mounting to the optical table, in unit of
        1 in / 25mm depending on the system chosen in settings
    """

    object_group = "baseplate"
    object_icon = ""
    object_color = (0.5, 0.5, 0.5)

    def __init__(self, dimensions: tuple, optical_height: dim, mounting_holes: list = [], speedholes = False, speedholes_topsheet =12.5):
        """Initialize adjustable parameters"""
        self.dimensions = dimensions
        self.optical_height = optical_height
        self.mounting_holes = mounting_holes
        self.speedholes = speedholes
        self.speedholes_topsheet = speedholes_topsheet

    def shape(self):
        part = box_shape(
            dimensions=self.dimensions,
            position=(0, 0, -self.optical_height),
            center=(-1, -1, 1),
        )


        if self.speedholes:
            # reduce weight by cutting out part of the material from the bottom
            top_sheet = self.speedholes_topsheet
            ribs = 8 # rib wall thickness
            cutter = 25 # cutter diameter

            # work out relevant dimensions for mounting bolts
            if settings.metric_hardware:
                spacing = dim(25,'mm')
            else:
                spacing = dim(1, 'in')
            
            #need to work around mounting bolt positions
            boundaries_y = [self.dimensions[1]]
            boundaries_y.extend(np.unique([d[1]*spacing for d in self.mounting_holes]))
            boundaries_y = sorted(boundaries_y)

            start = 0
            for end in boundaries_y:
                #work out number of pockets
                length = end-start
                n_y = int(np.floor((length - ribs) / (ribs + cutter)))
                size_y = (length - ribs) / n_y   - ribs

                for i in range(n_y):
                    cutout = box_shape(
                        dimensions=(self.dimensions[0] - 2*ribs, size_y, self.dimensions[2] - top_sheet),
                        position=(ribs, start + ribs+ i*(ribs+size_y) , -self.optical_height - top_sheet),
                        center=(-1, -1, 1),
                        fillet = cutter/2,
                        fillet_direction=(0,0,1)
                    )
                    part = part.cut(cutout)
                start = end 
        return part

    def subcomponents(self):
        if settings.metric_hardware:
            bolt_type = 'M6'
            spacing = dim(25,'mm')
        else:
            bolt_type = "1/4_20"
            spacing = dim(1, 'in')
        components = []
        for position in self.mounting_holes:
            position = (position[0]*spacing,position[1]*spacing, -self.dimensions[2] - self.optical_height + 20)
            components.append(
                subcomponent(
                component=Component(
                    label="Mounting Bolt",
                    definition=bolt(
                        ["M6"],
                        length=30,
                        from_top=False,
                        extra_depth=0,
                        clearance=True,
                    ),
                ),
                position=position,
                rotation=(0, 0, 0),
            )
            )
        return components


class breadboard(baseplate):

    """
    Standard optical breadboard

    Args:
        dimensions (tuple): The (x, y, z) dimensions of the baseplate
        optical_height (dimension): beam height over baseplate
        mounting_holes (list): locations for counterbored holes for mounting to the optical table, in unit of
        1 in / 25mm depending on the system chosen in settings
        hole_spacing (dimension): spacing between holes
        render_holes (bool): switch holes on/off to improve render speed during design
    """

    object_color = (0.2, 0.2, 0.2)
    def __init__(self, dimensions: tuple, optical_height: dim, mounting_holes: list = [], holespacing: dim = dim(25,'mm'), render_holes = True):
        """Initialize adjustable parameters"""
        super().__init__(
            dimensions = dimensions,
            optical_height = optical_height,
            mounting_holes = mounting_holes
        )
        self.holespacing = 25
        self.render_holes = render_holes

    def shape(self):
        part = box_shape(
            dimensions=self.dimensions,
            position=(0, 0, -self.optical_height),
            center=(-1, -1, 1),
        )
        if self.render_holes:
            holes = []
            spacing = self.holespacing
            holes_x = int(self.dimensions[0] / spacing)
            holes_y = int(self.dimensions[1] / spacing)
            height = self.dimensions[2]
            for i in range(holes_x):
                for j in range(holes_y):
                    holes.append(
                        cylinder_shape(diameter=6,
                                    height =2*height, 
                                    position = ((.5+i) * spacing, (.5+j)*spacing, -self.optical_height ), 
                                    rotation = (0,0,0), 
                                    direction = (0,0,-1) )
                    )
            part = part.cut(holes)
        return part
###########################
### Hardware Components ###
###########################


class bolt:
    """
    Standard bolt

    Args:
        label (str): The label for the component
        type (string): Bolt type, supports "4_40", "8_32", "14_20"
        length (float): Length of the bolt including the head
        washer_diameter (float): Diameter of washer to include, None for no washer
        countersink (bool): Whether the bolt head is a countersink
        head_tolerance (float): Tolerance of the bolt head / washer diameter
        extra_depth (float): Extra depth to add to the drilled hole
        from_top (bool): Whether the origin is at the top or bottom of the bolt head
        slot_length (float): Length of slot drilling a slot, None for no slot
        clearance (bool): Drill clearance holes rather than tapped holes
    """

    bolt_dimensions = {
        "4_40": dict(
            tag = 'imperial',
            clear_diameter=dim(0.12, "in"),
            tap_diameter=dim(0.089, "in"),
            head_diameter=dim(5.5, "mm"),
            head_height=dim(2.5, "mm"),
        ),
        "8_32": dict(
            tag = 'imperial',
            clear_diameter=dim(0.172, "in"),
            tap_diameter=dim(0.136, "in"),
            head_diameter=dim(7, "mm"),
            head_height=dim(4.4, "mm"),
        ),
        "1/4_20": dict(
            tag = 'imperial',
            clear_diameter=dim(0.26, "in"),
            tap_diameter=dim(0.201, "in"),
            head_diameter=dim(9.8, "mm"),
            head_height=dim(8, "mm"),
        ),
        "M3": dict(
            tag = 'metric',
            clear_diameter=dim(3.4, "mm"),
            tap_diameter=dim(2.5, "mm"),
            head_diameter=dim(5.5, "mm"),
            head_height=dim(3, "mm"),
        ),

        "M4": dict(
            tag = 'metric',
            clear_diameter=dim(4.5, "mm"),
            tap_diameter=dim(3.3, "mm"),
            head_diameter=dim(7, "mm"),
            head_height=dim(4, "mm"),
        ),
        "M6": dict(
            tag = 'metric',
            clear_diameter=dim(6.6, "mm"),
            tap_diameter=dim(5, "mm"),
            head_diameter=dim(10, "mm"),
            head_height=dim(6, "mm"),
        ),
    }

    object_group = "hardware"
    object_icon = ""
    object_color = (0.8, 0.8, 0.8)

    def __init__(
        self,
        type: str | list[str],
        length: dim,
        washer_diameter: dim = None,
        countersink: bool = False,
        head_tolerance: dim = dim(1, "mm"),
        extra_depth: dim = dim(5, "mm"),
        from_top: bool = True,
        slot_length: dim = None,
        clearance: bool = False,
    ):

        self.length = length
        self.washer_diameter = washer_diameter
        self.countersink = countersink
        self.head_tolerance = head_tolerance
        self.extra_depth = extra_depth
        self.from_top = from_top
        self.slot_length = slot_length
        self.clearance = clearance
        
        # identify hardware matching the users preferences
        preferred_tag = settings.preferred_bolt_tag
        bolt_type = None
        if isinstance(type, list):
            for i in type:
                if self.bolt_dimensions[i]['tag'] == preferred_tag:
                    bolt_type = i
            if bolt_type is None:
                bolt_type = type[0]
        else:
            bolt_type = type

        if self.bolt_dimensions[bolt_type]['tag'] != preferred_tag:
            warnings.warn(f"No bolt type with tag '{preferred_tag}' available, defaulting to {bolt_type}")
        self.type = bolt_type

        if countersink and slot_length != None:
            raise ValueError("Bolt does not support both slot and countersink")

        if washer_diameter != 0 and countersink:
            raise ValueError("Bolt does not support both washer and countersink")

    def shape(self):
        dims = self.bolt_dimensions[self.type]
        part = bolt_shape(
            diameter=dims["tap_diameter"],
            height=self.length,
            head_diameter=dims["head_diameter"],
            head_height=dims["head_height"],
            position=(0, 0, 0),
            direction=(0, 0, -1),
            countersink=self.countersink,
            from_top=self.from_top,
        )
        return part

    def drill(self):
        dims = self.bolt_dimensions[self.type]
        if self.washer_diameter != None:
            head_diameter = self.washer_diameter
        else:
            head_diameter = dims["head_diameter"]
        head_diameter += self.head_tolerance
        if self.slot_length == None:
            part = bolt_shape(
                diameter=dims["clear_diameter"] if self.clearance else dims["tap_diameter"],
                height=self.length + self.extra_depth,
                head_diameter=head_diameter,
                head_height=dims["head_height"]+100, # pad height to allow for deep countersinks
                position=(0, 0, 0),
                direction=(0, 0, -1),
                countersink=self.countersink,
                from_top=self.from_top,
            )
        else:
            part = bolt_slot_shape(
                diameter=dims["clear_diameter"] if self.clearance else dims["tap_diameter"],
                height=self.length + self.extra_depth,
                head_diameter=head_diameter,
                head_height=dims["head_height"],
                slot_length=self.slot_length,
                position=(0, 0, 0),
                direction=(0, 0, -1),
                from_top=self.from_top,
            )
        return part


class alignment_pin:
    """
    Standard alignment pin

    Args:
        diameter (float): Diameter of the pin
        length (float): Length of the pin
        hole_tolerance (float): Tolerance in the hole diameter
        depth_tolerance (float): Tolerance in the pin depth
    """

    object_group = "hardware"
    object_icon = ""
    object_color = (0.8, 0.8, 0.8)

    def __init__(
        self,
        diameter: dim,
        length: dim,
        hole_tolerance: dim = dim(0.05, "mm"),
        depth_tolerance: dim = dim(1, "mm"),
    ):
        self.diameter = diameter
        self.length = length
        self.hole_tolerance = hole_tolerance
        self.depth_tolerance = depth_tolerance

    def shape(self):
        part = cylinder_shape(
            diameter=self.diameter,
            height=self.length,
            position=(0, 0, -self.depth_tolerance / 2),
            direction=(0, 0, -1),
        )
        return part

    def drill(self):
        part = cylinder_shape(
            diameter=self.diameter + self.hole_tolerance,
            height=self.length + self.depth_tolerance,
            position=(0, 0, 0),
            direction=(0, 0, -1),
        )
        return part


##########################
### Optical Components ###
##########################


class circular_reflector:
    """
    A circular reflector component

    Args:
        diameter (float): The diameter of the reflector
        thickness (float): The thickness of the reflector
        mount_definition (object): The definition of the mount component
        mount_offset (tuple): The (x, y, z) offset of the mount relative to reflector origin
                              If None, defaults to (-thickness, 0, 0)
        ref_ratio (float): The ratio of reflected to transmitted light
        ref_polarization (float): The reflected polarization angle
        ref_wavelengths (list): A list of tuples representing the ranges of wavelengths to be reflected
                                 Use None for open-ended ranges
        refractive_index (float): refractive index of the substrate
    """

    object_group = "optic"
    object_icon = optic_icon
    object_color = (0.5, 0.5, 0.8)

    def __init__(
        self,
        diameter: dim,
        thickness: dim,
        mount_definition: object = None,
        mount_offset: tuple = None,
        ref_ratio: float = None,
        ref_polarization: float = None,
        ref_wavelengths: list = None,
        refractive_index: float = 1.5,
    ):
        self.diameter = diameter
        self.thickness = thickness
        self.mount_definition = mount_definition
        self.mount_offset = mount_offset
        self.ref_ratio = ref_ratio
        self.ref_polarization = ref_polarization
        self.ref_wavelengths = ref_wavelengths
        self.refractive_index = refractive_index

        if ref_ratio != None or ref_polarization != None or ref_wavelengths != None:
            self.bidirectional = True
            self.max_angle = 180
        else:
            self.bidirectional = False
            self.max_angle = 90

    def interfaces(self):
        interfaces = [
            Reflection(
                position=(0, 0, 0),
                rotation=(0, 0, 0),
                diameter=self.diameter,
                ref_ratio=self.ref_ratio,
                ref_polarization=self.ref_polarization,
                ref_wavelengths=self.ref_wavelengths,
                refractive_index_ratio=1 / self.refractive_index,
                max_angle=self.max_angle,
            ),
        ]

        if self.bidirectional:
            interfaces.append(
                Reflection(
                    position=(-self.thickness, 0, 0),
                    rotation=(0, 0, 180),
                    diameter=self.diameter,
                    ref_ratio=0,
                    refractive_index_ratio=1 / self.refractive_index,
                    max_angle=self.max_angle,
                )
            )

        return interfaces

    def subcomponents(self):
        if self.mount_definition != None:
            mount_offset = self.mount_offset
            if mount_offset is None:
                mount_offset = (-self.thickness, 0, 0)
            return [
                subcomponent(
                    component=Component(
                        label="Mount",
                        definition=self.mount_definition,
                    ),
                    position=mount_offset,
                    rotation=(0, 0, 0),
                )
            ]
        else:
            return []

    def shape(self):
        part = cylinder_shape(
            diameter=self.diameter,
            height=self.thickness,
            position=(-self.thickness, 0, 0),
            direction=(1, 0, 0),
        )
        return part


class circular_mirror(circular_reflector):
    """
    A circular mirror component

    Args:
        diameter (float): The diameter of the mirror
        thickness (float): The thickness of the mirror
        mount_definition (object): The definition of the mount component
        mount_offset (tuple): The (x, y, z) offset of the mount relative to mirror origin
                              If None, defaults to (-thickness, 0, 0)
    """

    def __init__(
        self,
        diameter: dim,
        thickness: dim,
        mount_definition: object = None,
        mount_offset: tuple = None,
    ):
        super().__init__(
            diameter=diameter,
            thickness=thickness,
            mount_definition=mount_definition,
            mount_offset=mount_offset,
        )


class circular_sampler(circular_reflector):
    """
    A circular sampler component

    Args:
        diameter (float): The diameter of the sampler
        thickness (float): The thickness of the sampler
        ref_ratio (float): The ratio of reflected to transmitted light
        mount_definition (object): The definition of the mount component
        mount_offset (tuple): The (x, y, z) offset of the mount relative to sampler origin
                              If None, defaults to (-thickness, 0, 0)
    """

    def __init__(
        self,
        diameter: dim,
        thickness: dim,
        ref_ratio: float,
        mount_definition: object = None,
        mount_offset: tuple = None,
    ):
        super().__init__(
            diameter=diameter,
            thickness=thickness,
            mount_definition=mount_definition,
            mount_offset=mount_offset,
            ref_ratio=ref_ratio,
        )

        self.object_transparency = int(100 * ref_ratio)


class circular_dichroic_mirror(circular_reflector):
    """
    A circular dichroic mirror component

    Args:
        diameter (float): The diameter of the dichroic mirror
        thickness (float): The thickness of the dichroic mirror
        ref_wavelengths (list): A list of tuples representing the ranges of wavelengths to be reflected
                                 Use None for open-ended ranges
        mount_definition (object): The definition of the mount component
        mount_offset (tuple): The (x, y, z) offset of the mount relative to the mirror origin
                              If None, defaults to (-thickness, 0, 0)
    """

    object_transparency = 25

    def __init__(
        self,
        diameter: dim,
        thickness: dim,
        ref_wavelengths: list,
        mount_definition: object = None,
        mount_offset: tuple = None,
    ):
        super().__init__(
            diameter=diameter,
            thickness=thickness,
            mount_definition=mount_definition,
            mount_offset=mount_offset,
            ref_wavelengths=ref_wavelengths,
        )


class spherical_lens:
    """
    A spherical lens component

    Args:
        diameter (float): The diameter of the lens
        thickness (float): The thickness of the lens
        focal_length (float): The focal length of the lens
        mount_definition (object): The definition of the mount component
        mount_offset (tuple): The (x, y, z) offset of the mount relative to lens origin
                              If None, defaults to (0, 0, 0)
    """

    object_group = "optic"
    object_icon = optic_icon
    object_color = (0.5, 0.5, 0.8)
    object_transparency = 75

    def __init__(
        self,
        diameter: dim,
        thickness: dim,
        focal_length: dim,
        mount_definition: object = None,
        mount_offset: tuple = None,
    ):
        self.diameter = diameter
        self.thickness = thickness
        self.focal_length = focal_length
        self.mount_definition = mount_definition
        self.mount_offset = mount_offset

    def interfaces(self):
        return [
            Lens(
                position=(0, 0, 0),
                rotation=(0, 0, 0),
                diameter=self.diameter,
                focal_length=self.focal_length,
            )
        ]

    def subcomponents(self):
        if self.mount_definition != None:
            mount_offset = self.mount_offset
            if mount_offset is None:
                mount_offset = (0, 0, 0)
            return [
                subcomponent(
                    component=Component(
                        label="Mount",
                        definition=self.mount_definition,
                    ),
                    position=mount_offset,
                    rotation=(0, 0, 0),
                )
            ]
        else:
            return []

    def shape(self):
        part = cylinder_shape(
            diameter=self.diameter,
            height=self.thickness,
            position=(-self.thickness / 2, 0, 0),
            direction=(1, 0, 0),
        )
        return part


class polarizing_beam_splitter_cube:
    """
    A polarizing beam splitter cube component

    Args:
        size (float): The side length of the cube
        thickness (float): The thickness of the beam splitter interface
        mount_definition (object): The definition of the mount component
        mount_offset (tuple): The (x, y, z) offset of the mount relative to the cube origin
                              If None, defaults to (0, 0, -size/2)
    """

    object_group = "optic"
    object_icon = optic_icon
    object_color = (0.5, 0.5, 0.8)
    object_transparency = 75

    def __init__(
        self,
        size: dim,
        ref_polarization: float = 0.0,
        mount_definition: object = None,
        mount_offset: tuple = None,
        mount_rotation: tuple = None,
    ):
        self.size = size
        self.ref_polarization = ref_polarization
        self.mount_definition = mount_definition
        self.mount_offset = mount_offset
        self.mount_rotation = mount_rotation

    def interfaces(self):
        return [
            Reflection(
                position=(0, 0, 0),
                rotation=(0, 0, 45),
                width=self.size * np.sqrt(2),
                height=self.size * np.sqrt(2),
                ref_polarization=self.ref_polarization,
            )
        ]

    def subcomponents(self):
        if self.mount_definition != None:
            mount_offset = self.mount_offset
            if mount_offset is None:
                mount_offset = (0, 0, -self.size / 2)
            mount_rotation = self.mount_rotation
            if mount_rotation is None:
                mount_rotation = (0,0,0)
            return [
                subcomponent(
                    component=Component(
                        label="Mount",
                        definition=self.mount_definition,
                    ),
                    position=mount_offset,
                    rotation=mount_rotation,
                )
            ]
        else:
            return []

    def shape(self):
        part = box_shape(
            dimensions=(self.size, self.size, self.size),
            position=(0, 0, 0),
            center=(0, 0, 0),
        )
        diag = self.size * np.sqrt(2)
        part = part.cut(
            box_shape(
                dimensions=(0.1, diag, diag),
                position=(0, 0, 0),
                rotation=(0, 0, 45),
                center=(0, 0, 0),
            )
        )
        return part


class waveplate:
    """
    A waveplate - currently does absolutely nothing to the polarisation

    Args:
        diameter (float): The diameter of the waveplate
        thickness (float): The thickness of the waveplate
        mount_definition (object): The definition of the mount component
        mount_offset (tuple): The (x, y, z) offset of the mount relative to waveplate origin
                              If None, defaults to (-thickness, 0, 0)
        retardance (float): The retardance in waves
        angle (float): The angle in degrees
    """

    object_group = "optic"
    object_icon = optic_icon
    object_color = (0.5, 0.5, 0.8)

    def __init__(
        self,
        diameter: dim,
        thickness: dim,
        mount_definition: object = None,
        mount_offset: tuple = None,
        retardance: float = None,
        angle: float = None,
    ):
        self.diameter = diameter
        self.thickness = thickness
        self.mount_definition = mount_definition
        self.mount_offset = mount_offset
        self.retardance = retardance
        self.angle = angle


    def interfaces(self):
        interfaces = [
            Retarder(
                position=(0, 0, 0),
                rotation=(0, 0, 0),
                diameter=self.diameter,
                retardance=self.retardance,
                angle = self.angle,
                max_angle=90,
            ),
        ]
        return interfaces

    def subcomponents(self):
        if self.mount_definition != None:
            mount_offset = self.mount_offset
            if mount_offset is None:
                mount_offset = (-self.thickness, 0, 0)
            return [
                subcomponent(
                    component=Component(
                        label="Mount",
                        definition=self.mount_definition,
                    ),
                    position=mount_offset,
                    rotation=(0, 0, 0),
                )
            ]
        else:
            return []

    def shape(self):
        part = cylinder_shape(
            diameter=self.diameter,
            height=self.thickness,
            position=(-self.thickness, 0, 0),
            direction=(1, 0, 0),
        )
        return part
    
################################
### Custom Adapters / Mounts ###
################################

# class skate_mount:
#     """
#     A simple glue-on mount for rectangular optics

#     Args:
#         height (float): The height of the mount
#         min_width (float): The minimum width of the mount
#         bolt_spacing (float): The spacing between the two mount holes of the adapter
#         bolt_walls (float): The minimum thickness of the walls around the bolt holes
#         recess_depth (float): The depth of the recess for the optic
#         slot_length (float): The length of the slot for the bolts, 0 for no slot
#     """

#     object_group = "adapter"
#     object_color = (0.25, 0.25, 0.25)

#     def __init__(
#         self,
#         height: dim,
#         min_width: dim,
#         bolt_spacing: dim,
#         bolt_walls: dim = dim(2, "mm"),
#         recess_depth: dim = dim(2, "mm"),
#         slot_length: dim = dim(0, "mm"),
#     ):
#         self.height = height
#         self.min_width = min_width
#         self.bolt_spacing = bolt_spacing
#         self.bolt_walls = bolt_walls
#         self.recess_depth = recess_depth
#         self.slot_length = slot_length

#     def shape(self):
#         width = self.bolt_spacing + 2 * self.bolt_walls
#         length = min(self.min_width


###########################
### Thorlabs Components ###
###########################



class thumbscrew:
    """
    Thumbscrew

    """

    object_group = "mount"
    object_icon = thorlabs_icon
    object_color = (0.4, 0., 0.)

    mesh = import_model("thumbscrew")

    def drill(self):
        part = box_shape(
                dimensions=(dim(30,'mm'),dim(20,'mm'),dim(20,'mm')), 
                position= (4,0,0),
                center=(1, 0, 0),
                fillet = 5,
        )
        return part
        


class mirror_mount_k05s1:
    """
    Mirror mount, model K05S1

    Args:
        drill_depth (float): The depth of the mounting hole
    """

    object_group = "mount"
    object_icon = thorlabs_icon
    object_color = (0.25, 0.25, 0.25)

    mesh = import_model("polaris-k05s1")
    mount_position = (-8.017, 0.000, -12.700)
    bolt_position = (-8.017, 0.000, -7.112)
    pin_positions = [(-8.017, 5.000, -10.795), (-8.017, -5.000, -10.795)]

    def __init__(self, drill_depth: dim):
        self.drill_depth = drill_depth

    def subcomponents(self):
        extra_length = self.bolt_position[2] - self.mount_position[2]
        components = [
            subcomponent(
                component=Component(
                    label="Mounting Bolt",
                    definition=bolt(
                        ["8_32","M4"],
                        length=self.drill_depth + extra_length,
                        from_top=False,
                        extra_depth=0,
                    ),
                ),
                position=self.bolt_position,
                rotation=(0, 0, 0),
            )
        ]
        for position in self.pin_positions:
            components.append(
                subcomponent(
                    component=Component(
                        label="Alignment Pin",
                        definition=alignment_pin(
                            diameter=dim(1.9, "mm"), length=dim(4, "mm")
                        ),
                    ),
                    position=position,
                    rotation=(0, 0, 0),
                )
            )
        return components


class cage_plate_sp02:
    """
    16mm Cage plate, model Thorlabs SP02

    Args:
        drill_depth (float): The depth of the mounting hole
    """

    object_group = "mount"
    object_icon = thorlabs_icon
    object_color = (0.25, 0.25, 0.25)

    mesh = import_model("thorlabs_sp02")
    bolt_position = (1.524, 0.000, -12.497)

    def __init__(self, drill_depth: dim):
        self.drill_depth = drill_depth

    def subcomponents(self):
        position = (self.bolt_position[0],self.bolt_position[1],self.bolt_position[2]-8)
        components = [
            subcomponent(
                component=Component(
                    label="Mounting Bolt",
                    definition=bolt(
                        ["M3", "4_40"],
                        length=self.drill_depth,
                        from_top=False,
                        extra_depth=0,
                        clearance=True,
                    ),
                ),
                position=position,
                rotation=(180, 0, 0),
            )
        ]
        
        return components

class fiber_collimator:
    """
    A spherical lens component

    Args:
        diameter (float): The optical diameter of the collimator
        focal_length (float): The focal length of the collimator
        mount_definition (object): The definition of the mount component
        mount_offset (tuple): The (x, y, z) offset of the mount relative to lens origin
                              If None, defaults to (0, 0, 0)
    """

    object_group = "optic"
    object_icon = optic_icon
    object_color = (0.25, 0.25, 0.25)
    object_transparency = 75

    def __init__(
        self,
        diameter: dim,
        focal_length: dim,
        mount_definition: object = None,
        mount_offset: tuple = None,
        style: str = 'Thorlabs'
    ):
        self.diameter = diameter
        self.focal_length = focal_length
        self.mount_definition = mount_definition
        self.mount_offset = mount_offset
        if style == 'Thorlabs':
            self.mesh = import_model("TL_collimator_APC")

    def interfaces(self):
        return [
            Lens(
                position=(0, 0, 0),
                rotation=(0, 0, 0),
                diameter=self.diameter,
                focal_length=self.focal_length,
            ),
            Dump(
                position=(self.focal_length, 0, 0),
                rotation=(0, 0, 0),
                diameter=self.diameter,
            )

        ]

    def subcomponents(self):
        if self.mount_definition != None:
            mount_offset = self.mount_offset
            if mount_offset is None:
                mount_offset = (0, 0, 0)
            return [
                subcomponent(
                    component=Component(
                        label="Mount",
                        definition=self.mount_definition,
                    ),
                    position=mount_offset,
                    rotation=(0, 0, 0),
                )
            ]
        else:
            return []






class isolator_thorlabs_io4vlp:
    """
    Thorlas IO-4-xxxx-VLP isolator

    Args:
        diameter (float): The optical diameter of the collimator
        mount_definition (object): The definition of the mount component
        mount_offset (tuple): The (x, y, z) offset of the mount relative to lens origin
                              If None, defaults to (0, 0, 0)
    """

    object_group = "optic"
    object_icon = optic_icon
    object_color = (0.25, 0.25, 0.25)
    object_transparency = 0

    mount_position = (-7.620, -0.013, -17.145)

    def __init__(
        self,
        diameter: dim = 4,
        mount_definition: object = None,
        mount_offset: tuple = None,
        style: str = 'Thorlabs'
    ):
        self.diameter = diameter
        self.mount_definition = mount_definition
        self.mount_offset = mount_offset
        self.mesh = import_model("thorlabs_io_4_xxx_vlp")

    def interfaces(self):
        return [
            Dummy(
                position=(0, 0, 0),
                rotation=(0, 0, 0),
                diameter=self.diameter,
            )

        ]

    def subcomponents(self):
        components = [
            subcomponent(
                component=Component(
                    label="Mounting Bolt",
                    definition=bolt(
                        ["8_32","M4"],
                        length=16,
                        from_top=False,
                        extra_depth=0,
                        clearance=True,
                    ),
                ),
                position=(self.mount_position[0],self.mount_position[1], self.mount_position[2]-6),
                rotation=(180, 0, 0),
            )
        ]

        return components
    
    def drill(self):
        part = box_shape(
                dimensions=(dim(15,'mm'),dim(30,'mm'),dim(20,'mm')), 
                position= self.mount_position,
                center=(0, 0, -1),
                fillet = 5,
        )
        
        return part




class thorlabs_hca3_sm05:
    """
    Thorlabs fiber bench cage plate adapter 

    Args:
        diameter (float): The diameter of the reflector
        mount_definition (object): The definition of the mount component
        mount_offset (tuple): The (x, y, z) offset of the mount relative to reflector origin
                              If None, defaults to (-thickness, 0, 0)
    """

    object_group = "optic"
    object_icon = optic_icon
    object_color = (0.25, 0.25, 0.25)

    mesh = import_model("thorlabs_hca3_sm05")

    bolt_positions = [  (-2.235, 12.700, -20.700),
                        (-2.235, 0.000, -20.700),
                        (-2.235, -12.700, -20.700),
    ]

    pin_positions = [  (-2.235, 12.700/2, -20.700),
                        (-2.235, -12.700/2, -20.700),
    ]

    def __init__(
        self,
        diameter: dim = 16,
        mount_definition: object = None,
        mount_offset: tuple = None,
    ):
        self.diameter = diameter
        self.mount_definition = mount_definition
        self.mount_offset = mount_offset


    def interfaces(self):
        interfaces = [
            Dump(
                position=(0, 0, 0),
                rotation=(0, 0, 0),
                diameter=self.diameter,
                max_angle=180,
            ),
        ]
        return interfaces

    def subcomponents(self):
        components = []
        for position in self.bolt_positions:
            components.append(
                subcomponent(
                component=Component(
                    label="Mounting Bolt",
                    definition=bolt(
                        ["8_32","M4"],
                        length=20,
                        from_top=False,
                        extra_depth=0,
                    ),
                ),
                position=position,
                rotation=(0, -90, 0),
            )
            )
        for position in self.pin_positions:
            components.append(
                subcomponent(
                    component=Component(
                        label="Alignment Pin",
                        definition=alignment_pin(
                            diameter=dim(4, "mm"), length=dim(3, "mm")
                        ),
                    ),
                    position=position,
                    rotation=(0, -90, 0),
                )
            )
        return components

    






   # (-3.175, 0.000, -2.845)

   
class cage_rod:
    """
    Cage rod

    Args:
        diameter (float): Diameter of the pin
        length (float): Length of the pin
    """

    object_group = "hardware"
    object_icon = ""
    object_color = (0.8, 0.8, 0.8)
    hole_tolerance = .5
    depth_tolerance =2

    def __init__(
        self,
        length: dim,
        diameter: dim = dim(4,'mm'),
    ):
        self.diameter = diameter
        self.length = length
       

    def shape(self):
        part = cylinder_shape(
            diameter=self.diameter,
            height=self.length,
            position=(0, 0, 0),
            direction=(1, 0, 0),
        )
        return part

    def drill(self):
        part = cylinder_shape(
            diameter=self.diameter + self.hole_tolerance,
            height=self.length + self.depth_tolerance,
            position=(0, 0, 0),
            direction=(1, 0, 0),
        )
        return part
    

    
class thorlabs_smb1:
    """
    16 mm Cage Mounting Bracket

    """

    object_group = "mounts"
    object_icon = ""
    object_color = (0.25, 0.25, 0.25)
    bolt_positions = [(-3.175, 0.000, -2.845),]
    mesh = import_model("thorlabs_smb1")

    def subcomponents(self):
        components = []
        for position in self.bolt_positions:
            components.append(
                subcomponent(
                component=Component(
                    label="Mounting Bolt",
                    definition=bolt(
                        ["4_40","M3"],
                        length=16,
                        from_top=False,
                        extra_depth=0,
                    ),
                ),
                position=position,
                rotation=(0, 0, 0),
            )
            )
            return components


    

class cage_segment:

    """
    Segment of 16mm cage system, mounted using SMB1.
    Use this component as mount for the first element, place any subsequent elements in cage plates

    Args:
        length (dim): Length of the cage rods
        overhang (dim): length of cage rod before the first mount
    """
    object_group = "mount"
    object_icon = thorlabs_icon
    object_color = (0.25, 0.25, 0.25)

    bolt_position = (1.524, 0.000, -12.497)

    def __init__(self, length:dim, overhang:dim = 0, drill_depth: dim=dim(6,'mm'), bracket_positions: list[float] = None):
        self.length = length
        self.overhang = overhang
        self.drill_depth = drill_depth
        if bracket_positions is None:
            bracket_positions = [15, length-15]
        self.bracket_positions = bracket_positions
        

    def subcomponents(self):
        components = [
            subcomponent(
                component=Component(
                    label="Cage plate",
                    definition=cage_plate_sp02(drill_depth=self.drill_depth,bolt=False),
                ),
                position=(0,0,0),
                rotation=(0, 0, 0),
            ),
            subcomponent(
                component=Component(
                    label="Cage rod",
                    definition=cage_rod(self.length),
                ),
                position=(-self.overhang -5,-8,-8),
                rotation=(0, 0, 0),
            ),
            subcomponent(
                component=Component(
                    label="Cage rod",
                    definition=cage_rod(self.length),
                ),
                position=(-self.overhang -5,8,-8),
                rotation=(0, 0, 0),
            ),
            subcomponent(
                component=Component(
                    label="Cage rod",
                    definition=cage_rod(self.length),
                ),
                position=(-self.overhang -5,-8,8),
                rotation=(0, 0, 0),
            ),
            subcomponent(
                component=Component(
                    label="Cage rod",
                    definition=cage_rod(self.length),
                ),
                position=(-self.overhang -5,8,8),
                rotation=(0, 0, 0),
            ),
        ]

        for pos in self.bracket_positions:
            components.append(subcomponent(
                component=Component(
                    label="Cage bracket",
                    definition=thorlabs_smb1(),
                ),
                position=(pos,0,-8),
                rotation=(0, 0, 0),
            ))

        return components





class cage_plate_sp02:
    """
    16mm Cage plate, model Thorlabs SP02

    Args:
        drill_depth (float): The depth of the mounting hole
    """

    object_group = "mount"
    object_icon = thorlabs_icon
    object_color = (0.25, 0.25, 0.25)

    mesh = import_model("thorlabs_sp02")
    bolt_position = (1.524, 0.000, -12.497)

    def __init__(self, drill_depth: dim, bolt: bool = True):
        self.drill_depth = drill_depth
        self.bolt = bolt

    def subcomponents(self):
        if not self.bolt:
            return []
        position = (self.bolt_position[0],self.bolt_position[1],self.bolt_position[2]-8)
        components = [
            subcomponent(
                component=Component(
                    label="Mounting Bolt",
                    definition=bolt(
                        ["M3", "4_40"],
                        length=self.drill_depth,
                        from_top=False,
                        extra_depth=0,
                        clearance=True,
                    ),
                ),
                position=position,
                rotation=(180, 0, 0),
            )
        ]
        
        return components
