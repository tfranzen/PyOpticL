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

def clean_document():
    """
        Remove all components from document in between iterations
    """
     
    for i in App.ActiveDocument.Objects:
            App.ActiveDocument.removeObject(i.Name)

def find_beam_after_element(label, obj = None):
        """
        Find the beam immediately following the object with the specified label

        Args:
            label (str): Label of object
            obj (FreeCAD object): Starting point for search, if None will search active document

        Returns:
            beamsegment: The beam segment immediately following the object with the specified label
        """

        # recursively look for the beam after the element with the specified label
        if obj is None:
             #First call, start with all objects in the active document
             for child in App.ActiveDocument.Objects:
                  return find_beam_after_element(label, child)
             
        if hasattr(obj, 'ChildObject') and obj.ChildObject is not None:
                # Is the object at the end of the current beam the object we are looking for?
                if obj.ChildObject.Label == label:
                    # if so, grab the beam segment after this
                    return obj.Children[0]
        for child in obj.Children:
            # recursively look at all children of current object
            recurse = find_beam_after_element(label, child)
            if recurse is not None:
                return recurse
            
        return None

def coupling_efficiency(w1,w2, wavelength = 1064, dz=0):
    """
        Estimate coupling efficiency between mismatched Gaussian modes assuming perfect transverse and angular alignment

        Args:
            w1 (float): Beam waist of first mode in um
            w2 (float): Beam waist of second mode in um
            wavelength (float): Optical wavelength in nm
            dz (float): longitudinal offset between the two modes
        Returns:
            coupling_efficiency (float): Estimated coupling efficiency

        """
    # estimate coupling effiency between mismatched modes 
    if np.isclose(dz,0):
        return np.square( 2 * (w1*w2) / (w1**2 + w2**2))
    else:
        # bring everything to um
         dz = dz*1000
         wavelength = wavelength /1000
         return 1/( (w1**2 + w2**2)**2 / (4*w1**2 *w2**2) + (wavelength * dz / (2*np.pi*w1*w2))**2 ) 


def build_layout(spacing):
    """
        Build the optical layout with a specified spacing

        Args:
            spacing (float): Spacing in mm

        Returns:
            beam_waist (float): beam waist in mm
        """
    # Build the optical layout for a given spacing and return the beam waist
    layout = Layout("ULE Cavity")

    beam_path = layout.add(
        Beam_Path(
            label="Beam Path",
            waist=dim(cavity_waist, "mm"), # beam geometry from cavity mode calculation
            wavelength=wavelength,
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
    
    # find and return beam waist after the collimator lens
    beam = find_beam_after_element("Fiber collimator")
    return beam.BeamWaist.Value


# Scan spacing over a range of values for plot
X_ = np.linspace(50,200, 10)
Y_ = []

for spacing in X_:
    waist = build_layout(spacing)
    print("Focussed beam waits at %.0f mm spacing: %.2f um" % (spacing, waist*1000))
    Y_.append(waist)
    clean_document()


#Use data from previous step to estimate the optimal spacing
xopt = np.mean(X_)
from scipy.optimize import fsolve
try:
    f = lambda x: np.interp(x, X_, Y_) - fiber_MFD/2/1000
    xopt = fsolve(f, np.mean(X_) )[0]
    print( "Interpolated optimum waist at spacing of %.1f mm" % xopt)
except Exception as e:
    print ("Couldn't find optimum waist from data: %s" % e)

#Build layout with optimised spacing and check final beam waist
waist = build_layout(xopt)
print( "Actual waist at optimised spacing: %.2f um" % (waist*1000))


#Plot
Y2_ = coupling_efficiency(fiber_MFD/2, np.array(Y_)*1000) *100
fig, ax1 = plt.subplots()


ax2 = ax1.twinx()  
a, = ax1.plot(X_,np.array(Y_)*1000, label = "Focussed beam", color = 'C1')
b = ax1.hlines([fiber_MFD/2],np.min(X_),xopt, label = "Fiber mode", colors='k')
c = ax1.vlines(xopt,0,fiber_MFD/2, label = "Optimised spacing", colors='k')
ax1.set_xlim(np.min(X_), np.max(X_))
ax1.set_ylim(0, 1000*np.max(Y_))

ax1.set_xlabel("Length of last leg (mm)")
ax1.set_ylabel("Beam waist (um)")
ax2.set_ylabel("Coupling efficiency (%)")

d, = ax2.plot(X_,Y2_, color='C2', label = "Coupling efficiency")
ax2.set_ylim(90,100)

ax1.legend(handles = [a,d], loc = "lower left")
plt.show()



