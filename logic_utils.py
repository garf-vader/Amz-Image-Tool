import re

def natural_key(name: str):
	"""Return a key for natural sorting where numbers are ordered numerically."""
	return [int(s) if s.isdigit() else s.lower() for s in re.split(r"(\d+)", name)]
