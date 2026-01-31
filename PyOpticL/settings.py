metric_hardware = False
preferred_bolt_tag = "imperial"

def set_hardware_preference(system: str):
    global metric_hardware

    if system.lower() == "metric":
        metric_hardware = True
        preferred_bolt_tag = "metric"
    elif system.lower() == "imperial":
        metric_hardware = False
        preferred_bolt_tag = "imperial"
    else:
        raise ValueError("Invalid system preference. Use 'metric' or 'imperial'.")
