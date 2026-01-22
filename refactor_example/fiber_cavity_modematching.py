from PyOpticL import optomech
from PyOpticL.beam_path import Beam_Path
from PyOpticL.layout import Component
from PyOpticL.layout import Dimension as dim
from PyOpticL.layout import Layout


import FreeCAD as App

"""
Optimise an optical setup for mode matching between an optical fiber and an optical cavity

The focal length of the fiber collimator is selected to enable a match between cavity mode and fibre mode at a sensible distance. 
We'll construct the optical setup building backwards from the cavity mode. This is advantageous as the cavity is fixed in space, while we don't care about the exact position of the waist on the fiber side as the collimator is adjustable.
To optimise the mode matching we vary the spacing between the last mirror and the fiber collimator. 
Outputs are a plot of the beam waist on the fiber vs spacing and the optical layout at the optimised distance.

 """

fiber_MFD = 6.6 # Fiber Mode Field Diameter in um
f_collimator = 5

def clean_document():
    # Remove all components from document in between iterations
    for i in App.ActiveDocument.Objects:
            App.ActiveDocument.removeObject(i.Name)

def build_layout(spacing):
    # Build the optical layout for a given spacing and return the beam waist
    layout = Layout("ULE Cavity")

    beam_path = layout.add(
        Beam_Path(
            label="Beam Path",
            waist=dim(0.23, "mm"), # beam geometry from cavity mode calculation
            wavelength=1156,
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
        distance=dim(50, "mm"),
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

    fibre_beam = beam_path.add(
        Component(
            label="Fiber collimator",
            definition=optomech.spherical_lens(
                diameter=dim(10, "mm"),
                thickness=dim(2, "mm"),
                focal_length=dim(f_collimator, "mm"),
            ),
        ),
        beam_index=0b1,
        distance=dim(spacing, "mm"),
        rotation=(0, 0, 90),
    )


    
    layout.recompute()

    # get the object representing the focussed beam - need to find a better solution for this
    n= layout.get_object().Children[0].Children[-1].Children[0].Children[0].Children[0].Children[0].Children[0]
    waist = n.BeamWaist.Value

    return waist

    


import numpy as np
X_ = np.linspace(50,200, 10)
Y_ = []
for spacing in X_:
    waist = build_layout(spacing)
    print("Focussed beam waits at %.0f mm spacing: %.2f um" % (spacing, waist*1000))
    Y_.append(waist)
    clean_document()



from matplotlib import pyplot as plt
xopt = np.mean(X_)
from scipy.optimize import fsolve
try:
    f = lambda x: np.interp(x, X_, Y_) - fiber_MFD/2/1000
    xopt = fsolve(f, np.mean(X_) )[0]
    print( "Interpolated optimum waist at spacing of %.1f mm" % xopt)
except Exception as e:
    print ("Couldn't find optimum waist from data: %s" % e)



waist = build_layout(xopt)
print( "Actual waist at optimised spacing: %.2f um" % (waist*1000))

plt.figure()
plt.plot(X_,np.array(Y_)*1000, label = "Focussed beam")
plt.hlines([fiber_MFD/2],50,200, label = "Fiber mode", colors='k')
plt.vlines(xopt,0,4, label = "Optimised spacing", colors='k')
plt.xlabel("Length of last leg (mm)")
plt.ylabel("Beam waist (um)")
plt.legend()
plt.show()
