import serial
import pathlib
import time
from time import sleep
import datetime
import socket


BAUDRATES = [4_800, 9_600, 19_000, 38_400, 57_600, 115_200]
UNITS_P = "MBAR", "PASCAL", "TORR"
UNITS_T = "CELSIUS", "FAHRENHEIT", "KELVIN"
TIME_BEFORE_QUERY = 0.5

DEBUG = False

FOLDER = pathlib.Path(__file__).parent


class SocketConnection:
    def __init__(self, host="129.20.76.100", port=9002):
        port = int(port) # in case a string is passed
        self.host = host
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect((host, port))
        self.s.settimeout(5)
        self.f = self.s.makefile("rb")

    def write(self, msg):
        if DEBUG:
            print("Writing", msg)
        self.s.send(msg)

    def read_all(self):
        """
        Return a message from the scope.
        """
        reply = self.s.recv(1024)
        return reply


def write(connection, sensor=254, command="MD", command_par=None, value=None):
    # sensors answer when addressed via 254
    cmd = f"@{sensor}{command}"
    cmd += "?" if value is None else "!"
    if command_par is not None:
        cmd += str(command_par)
    if value is not None:
        if command_par is not None:
            cmd = cmd + ","
        cmd = cmd + str(value)
    cmd = cmd + "\\"
    if DEBUG:
        print(f"writing: {cmd}")
    return connection.write(cmd.encode("ascii"))


def read(connection, cast=None):
    data = connection.read_all()
    s = data.decode("ascii")
    if DEBUG:
        print(f"read: {s}")
    if s == "":
        return ""
    # remove @253ACK
    idx = s.find("ACK") + 3
    v = s[idx:]
    # remove termination
    v = v[:-1]
    if cast is not None:
        v = cast(v)
    return v


def query(connection, sensor=254, command="MD", command_par=None, cast=None):
    write(connection, sensor=sensor, command=command, command_par=command_par)
    sleep(TIME_BEFORE_QUERY)
    return read(connection, cast=cast)


def setvalue(connection, command=None, command_par=None, value=None, sensor=254):
    if value is not None:
        write(
            connection,
            sensor=sensor,
            command=command,
            command_par=command_par,
            value=value,
        )
        sleep(TIME_BEFORE_QUERY)
    query(connection, sensor=sensor, command=command, command_par=command_par)


class Sensor:
    def __init__(self, port="/dev/ttyUSB0", host=None):
        # if host is not None, it is assumed to be connected to a serial/ethernet box
        # such as a Brainbox
        if host is None:
            self.port = port
            self.connection = None
            self.baudrate = self.find_baudrate()
            self.connection = self._connect(self.baudrate)
            self._connection_string = port
        else:
            self.connection = SocketConnection(host=host, port=port)
            self.port = port
            self._connection_string = f"{host}:{port}"
        self.pressure_unit = self.query("U", command_par="P").lower()
        self.temperature_unit = self.query("U", command_par="T").lower()
        self.model = self.query("MD")
        self.last_temperature = None
        self.last_pressure = None

    def _connect(self, baudrate=9600):
        if self.connection is not None:
            self.connection.close()
        self.connection = serial.Serial(port=self.port, baudrate=baudrate)
        return self.connection

    def find_baudrate(self):
        baudrate_found = None
        for baud in BAUDRATES:
            c = self._connect(baud)
            ans = query(c, command="MD")
            if ans != "":
                baudrate_found = baud
                break
        return baudrate_found

    def query(self, command, command_par=None, cast=None):
        return query(
            self.connection, command=command, command_par=command_par, cast=cast
        )

    def set(self, command=None, command_par=None, value=None):
        setvalue(self.connection, command=command, command_par=command_par, value=value)
        sleep(TIME_BEFORE_QUERY)
        return self.query(command=command, command_par=command_par)

    def set_baudrate(self, baudrate):
        if baudrate not in BAUDRATES:
            raise ValueError(f"available baudrates are {BAUDRATES}")
        setvalue(self.connection, "BAUD", baudrate)
        self._connect(baudrate=baudrate)
        # first query after baudrate change usually fails
        try:
            self.query("MD")
        except Exception:
            pass

    #        if baudrate == 115_200:
    #            globals()["TIME_BEFORE_QUERY"] = 0.02
    #        else:
    #            globals()["TIME_BEFORE_QUERY"] = 0.05

    def set_pressure_unit(self, value):
        if value.upper() not in UNITS_P:
            raise ValueError(f"Pressure unit must be one of {UNITS_P}")
        self.set(command="U", command_par="P", value=value.upper())
        self.pressure_unit = self.query("U", command_par="P").lower()

    def set_temperature_unit(self, value):
        if value.upper() not in UNITS_T:
            raise ValueError(f"Temperature unit must be one of {UNITS_T}")
        self.set(command="U", command_par="T", value=value.upper())
        self.temperature_unit = self.query("U", command_par="T").lower()

    def read_pressure(self):
        P = self.query("P", cast=float)
        self.last_pressure = P
        return P

    def read_pirani_pressure(self):
        return self.query("P", command_par="MP", cast=float)

    def read_diaphragm_pressure(self):
        return self.query("P", command_par="PZ", cast=float)

    def read_temperature(self):
        T = self.query("T", cast=float)
        self.last_temperature = T
        return T

    def __str__(self):
        P = self.read_pressure()
        T = self.read_temperature()
        return f"{self.model} (@ {self._connection_string}), P = {P} {self.pressure_unit}, T = {T} {self.temperature_unit}"

    def __repr__(self):
        return self.__str__()


def display_and_record(port="/dev/ttyUSB0", host=None,dt_display=1, dt_saving=10):
    s = Sensor(host=host,port=port)
    t_last_save = 0
    folder = FOLDER / "data"
    folder.mkdir(exist_ok=True)
    P = []
    T = []
    while True:
        t0 = time.time()
        pressure = s.read_pressure()
        temperature = s.read_temperature()
        P.append(pressure)
        T.append(temperature)
        print(f"{datetime.datetime.now()} {pressure} {temperature}")
        if time.time() - t_last_save > dt_saving:
            today_string = datetime.datetime.today().strftime("%Y%m%d")
            fname = folder / f"{today_string}.txt"
            # check if new file, add header
            if not fname.is_file():
                with open(fname, "w") as f:
                    print(f"Recording in file {fname}")
                    f.write(f"# time P({s.pressure_unit}) T({s.temperature_unit})")
                    f.write(f"# {s}")  # to have name of device and port
            with open(fname, "a") as f:
                time_string = datetime.datetime.now().strftime("%H%M%S")
                pressure = sum(P) / len(P)
                temperature = sum(T) / len(T)
                str_to_write = f"\n{time_string} {pressure:8.3e} {temperature:6.3f}"
                print(f"writing {str_to_write[1:]} to file")
                f.write(str_to_write)
                t_last_save = time.time()
                P = []
                T = []
        wait_time = dt_display - (time.time() - t0)
        if wait_time > 0:
            time.sleep(wait_time)


if __name__ == "__main__":
    import sys

    print("usage python sens4.py port time_between_reads time_between_saving")
    port = "/dev/ttyUSB0" if len(sys.argv) < 2 else sys.argv[1]
    if port.find(",") > 0:
        host,port = port.split(",")
    else:
        host = None
    dt_display = 1 if len(sys.argv) < 3 else float(sys.argv[2])
    dt_saving = 10 if len(sys.argv) < 4 else float(sys.argv[3])
    display_and_record(host=host, port=port, dt_display=dt_display, dt_saving=dt_saving)
