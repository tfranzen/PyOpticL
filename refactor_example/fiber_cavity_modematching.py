from PyOpticL import optomech
from PyOpticL.beam_path import Beam_Path
from PyOpticL.layout import Component
from PyOpticL.layout import Dimension as dim
from PyOpticL.layout import Layout

from matplotlib import pyplot as plt
import numpy as np
import FreeCAD as App

"""
Optimise an optical setup for mode matching between an optical fiber and an optical cavity

The focal length of the fiber collimator is selected to enable a match between cavity mode and fibre mode at a sensible distance. 
We'll construct the optical setup building backwards from the cavity mode. This is advantageous as the cavity is fixed in space, while we don't care about the exact position of the waist on the fiber side as the collimator is adjustable.
To optimise the mode matching we vary the spacing between the last mirror and the fiber collimator. 
Outputs are a plot of the beam waist on the fiber vs spacing and the optical layout at the optimised distance.

 """

fiber_MFD = 6.6 # Fiber Mode Field Diameter in um
f_collimator = 5 # mm
cavity_waist = .283 # mm
wavelength = 1156 # nm

spacing = 175 # initial spacing
optimize_spacing = True # Toggle optimization

# Build the optical layout for a given spacing and return the beam waist
layout = Layout("ULE Cavity")

beam_path = layout.add(
    Beam_Path(
        label="Beam Path",
        waist=dim(cavity_waist, "mm"), # beam geometry from cavity mode calculation
        wavelength=wavelength,
        polarization=45,
    ),
    position=(0, 0, 0),
    rotation=(0, 0, 90),
)
beam_path.add(
    Component(
        label="Outcoupling mirror",
        definition=optomech.spherical_lens(
            diameter=dim(1, "in"),
            thickness=dim(2, "mm"),
            focal_length=dim(np.inf, "mm"), # just need to render a glass plate here to represent the plane mirror
        ),
    ),
    beam_index=0b1,
    distance=dim(1, "mm"),
    rotation=(0, 0, 90),
)

beam_path.add(
    Component(
        label="Incoupling mirror",
        definition=optomech.spherical_lens(
            diameter=dim(1, "in"),
            thickness=dim(2, "mm"),
            focal_length=dim(-2000, "mm"), # the shape of the curved mirror creates a (very weak) lens
        ),
    ),
    beam_index=0b1,
    distance=dim(50, "mm"),
    rotation=(0, 0, 90),
)


beam_path.add(
    Component(
        label="Steering mirror 1",
        definition=optomech.circular_mirror(
            
            thickness=dim(6, "mm"),
            diameter=dim(.5, "in"),
        ),
    ),
    beam_index=0b1,
    distance=dim(150/2 - 25 + 1.5*25, "mm"),
    rotation=(0, 0, -45),
)


beam_path.add(
    Component(
        label="Steering mirror 2",
        definition=optomech.circular_mirror(
            
            thickness=dim(6, "mm"),
            diameter=dim(.5, "in"),
        ),
    ),
    beam_index=0b1,
    distance=dim(50, "mm"),
    rotation=(0, 0, 135),
)

pbs = beam_path.add(
    Component(
        label="PBS",
        definition=optomech.polarizing_beam_splitter_cube(
            size=dim(.5, "in"), ref_polarization=0
        ),
    ),
    beam_index=0b1,
    distance=dim(25, "mm"),
    rotation=(0, 0, 180),
)

pd_path = pbs.reflected()
fiber_path = pbs.transmitted()

beam_path.add(
    Component(
        label="Photodiode mirror",
        definition=optomech.circular_mirror(
            
            thickness=dim(6, "mm"),
            diameter=dim(.5, "in"),
        ),
    ),
    beam_index=pd_path,
    distance=dim(50, "mm"),
    rotation=(0, 0, 45),
)


pd_lens = beam_path.add(
    Component(
        label="Photodiode lens",
        definition=optomech.spherical_lens(
            diameter=dim(.5, "in"),
            thickness=dim(2, "mm"),
            focal_length=dim(25, "mm"),
        ),
    ),
    beam_index=pd_path,
    distance=dim(10, "mm"),
    rotation=(0, 0, 90),
)

focus =  pd_lens.get_beam_after().WaistPosition.Value
print("Distance from photodiode lens to focus: %.1f mm" % focus)

beam_path.add(
    Component(
        label="Photodiode",
        definition=optomech.spherical_lens(
            diameter=dim(1, "mm"),
            thickness=dim(.2, "mm"),
            focal_length=dim(np.inf, "mm"),
        ),
    ),
    beam_index=pd_path,
    distance=dim(focus, "mm"),
    rotation=(0, 0, 90),
)

print("Place collimator")
fiber_collimator = beam_path.add(
    Component(
        label="Fiber collimator",
        definition=optomech.spherical_lens(
            diameter=dim(10, "mm"),
            thickness=dim(2, "mm"),
            focal_length=dim(f_collimator, "mm"),
        ),
    ),
    beam_index=fiber_path,
    distance=dim(spacing, "mm"),
    rotation=(0, 0, 90),
)

if optimize_spacing:
    # Scan spacing over a range of values for plot
    X_ = np.linspace(50,200, 10)
    Y_ = []

    for spacing in X_:
        # modify layout and determine beam waist and coupling efficiency for each
        fiber_collimator.distance = spacing
        layout.recompute() # need to recompute (should make it so changing distance resets placed)
        beam = fiber_collimator.get_beam_after()
        waist = beam.BeamWaist.Value

        print("Focussed beam waits at %.0f mm spacing: %.2f um" % (spacing, waist*1000))

        coupling_efficiency = beam.Proxy.get_beam_overlap(fiber_MFD/2/1000)
        Y_.append([waist,coupling_efficiency])
    Y_ = np.array(Y_)

    #Use data from previous step to estimate the optimal spacing
    xopt = np.mean(X_)
    from scipy.optimize import fsolve
    try:
        f = lambda x: np.interp(x, X_, Y_[:,0]) - fiber_MFD/2/1000
        xopt = fsolve(f, np.mean(X_) )[0]
        print( "Interpolated optimum waist at spacing of %.1f mm" % xopt)
    except Exception as e:
        print ("Couldn't find optimum waist from data: %s" % e)


    #Plot
    
    Y1_ = Y_[:,0]*1000
    Y2_ = Y_[:,1]*100

    fig, ax1 = plt.subplots()

    ax2 = ax1.twinx()  
    a, = ax1.plot(X_,np.array(Y1_), label = "Focussed beam", color = 'C1')
    b = ax1.hlines([fiber_MFD/2],np.min(X_),xopt, label = "Fiber mode", colors='k')
    c = ax1.vlines(xopt,0,fiber_MFD/2, label = "Optimised spacing", colors='k')
    ax1.set_xlim(np.min(X_), np.max(X_))
    ax1.set_ylim(0, np.max(Y1_))

    ax1.set_xlabel("Length of last leg (mm)")
    ax1.set_ylabel("Beam waist (um)")
    ax2.set_ylabel("Coupling efficiency (%)")

    d, = ax2.plot(X_,Y2_, color='C2', label = "Coupling efficiency")
    ax2.set_ylim(90,100)

    ax1.legend(handles = [a,d], loc = "lower left")
    plt.show()
else: 
     xopt = 133 # value from previous optimisation run



#Build layout with optimised spacing and check final beam waist
fiber_collimator.distance = xopt
layout.recompute()
beam = fiber_collimator.get_beam_after()
waist = beam.BeamWaist.Value
print( "Actual waist at optimised spacing: %.2f um" % (waist*1000))
