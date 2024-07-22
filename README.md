
# sens4

read the multi range gaugues from sens4.
Tested using:
 - https://sens4.com/vpm-5-smartpirani.html
 - USB to RS-232 converter with power supply and cable
 - Linux Ubuntu 20.04 (after adding user to *dialout* group)

```
# better to create a virtual environment ?
cd your_favourite_folder
python -m venv sens4_venv
source sens4_venv/bin/activate
```

## Install
```
pip install git+https://github.com/marcocamma/sens4.git
```

## Usage

```py
from sens4 import Sensor

s = Sensor("/dev/ttyUSB0") # use the right port !
s.read_temperature()
s.read_pressure()
s.set_pressure_unit("mbar")
s.set_temperature_unit("celsius")
s.query("MD") # ask for sensor model, see manual
```
