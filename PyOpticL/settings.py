from PyOpticL.layout import Dimension as dim

metric_hardware = False
preferred_bolt_tag = "imperial"

def set_hardware_preference(system: str):
    global metric_hardware
    global preferred_bolt_tag
    if system.lower() == "metric":
        metric_hardware = True
        preferred_bolt_tag = "metric"
    elif system.lower() == "imperial":
        metric_hardware = False
        preferred_bolt_tag = "imperial"
    else:
        raise ValueError("Invalid system preference. Use 'metric' or 'imperial'.")

def grid_spacing():
    global metric_hardware
    if metric_hardware:
        return dim(25,'mm')
    else:
        return dim(1, 'in')