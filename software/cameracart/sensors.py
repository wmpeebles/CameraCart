from PyQt5 import QtCore
import platform
import time
import ntplib
import gphoto2 as gp
import emulators
import re


def wait_for_time_sync():
    """
    By including this function at the front of the file, proper time synchronization with NTP will occur first,
    but requires use of internet. It's possible time could be obtained in another manner, such as through camera.
    """

    max_wait_time = 60  # seconds
    now = time.time()
    timeout = now + max_wait_time
    remaining = timeout - now
    print_connection_error = True
    synchronized = False

    while remaining >= 0:
        try:
            c = ntplib.NTPClient()
            response = c.request('pool.ntp.org', version=3)
        except Exception as e:
            print(f'Error connecting to pool.ntp.org: {e}')
        try:
            difference = response.tx_time - time.time()
            if abs(difference) < 10:
                print(f"System time is synchronized with an NTP server ({round(difference, 2)}s offset).")
                synchronized = True
                break
            elif abs(difference) > 10:
                print("System time is not yet synchronized with an NTP server. Please wait...")
        except NameError:
            if print_connection_error:
                print("Error checking NTP server. Are you connected to the internet?")
                print_connection_error = False
        remaining = timeout - time.time()
        print(f"Waiting for NTP synchronization. ({round(remaining)}s remaining)              ", end="\r")
        time.sleep(1)

    return synchronized

#wait_for_time_sync()

if platform.node() == 'cameracart':
    import RPi.GPIO as GPIO
    import adafruit_gps
    import serial
else:
    print(f'Simulating GPIO library because hostname is {platform.node()} and assumed not to be a raspberry pi!')
    GPIO = emulators.GPIOSimulator()
    adafruit_gps = emulators.GPSSimulator()
    serial = emulators.SerialSimulatior()


def gpio_setup(gpio_pin):
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)


class MovementSensor(QtCore.QObject):
    moved = QtCore.pyqtSignal()

    def __init__(self, gpio_pin, movement_distance):
        super().__init__()

        self.GPIO_PIN = gpio_pin
        gpio_setup(self.GPIO_PIN)

        self.movement_distance = movement_distance  # in centimeters

        self.cumulative_movements = 0
        self.cumulative_distance = 0

        # Magnet state refers to whether magnet was detected or not
        self.previous_magnet_state = self.detect_magnet()
        self.magnet_state = self.detect_magnet()

        #self.moved_q = multiprocessing.Queue()

    def detect_magnet(self):
        """
        Detect presence of magnet based on whether GPIO pin is high.
        :return: True/False
        """
        if GPIO.input(self.GPIO_PIN):
            return True
        else:
            return False

    @QtCore.pyqtSlot()
    def moved_(self):
        """
        Checks for change in magnet state (cart moved). If magnet state changed from False to True, self.cumulative_movements
        and self.cumulative_distance are updated.
        :return: True
        """
        self.previous_magnet_state = self.magnet_state
        magnet_state = self.detect_magnet()
        
        # Uncomment these two lines if magnet fails
        # Then set timer to run every 1 second or so (1000 ms)
        #self.previous_magnet_state = False
        #magnet_state = True

        if magnet_state:
            if not self.previous_magnet_state:
                print('\a', end='\r')
                self.cumulative_movements += 1
                self.cumulative_distance = self.cumulative_movements * self.movement_distance
                self.magnet_state = magnet_state
                print(f'Number of movements detected: {self.cumulative_movements}, '
                      f' Distance Traveled: {self.cumulative_distance / 100} meters')
                self.moved.emit()
        else:
            self.magnet_state = magnet_state


class GPS(QtCore.QObject):
    gps_lat = QtCore.pyqtSignal([float])
    gps_lon = QtCore.pyqtSignal([float])

    def __init__(self):
        super().__init__()

        uart = serial.Serial("/dev/ttyS0", baudrate=9600, timeout=3000)
        self.gps = adafruit_gps.GPS(uart, debug=False)

        self.gps.send_command(b'PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0')

        # 1000 = update every 1000 ms
        self.gps.send_command(b'PMTK220, 1000')

        self.current_lon = None
        self.current_lat = None

    @QtCore.pyqtSlot()
    def update(self):
        self.gps.update()

        if not self.gps.has_fix:
            pass
        else:
            self.current_lat = self.gps.latitude
            self.current_lon = self.gps.longitude

            self.gps_lat.emit(self.current_lat)
            self.gps_lon.emit(self.current_lon)


class IMU:
    def __init__(self):
        self.direction = None


class Camera(QtCore.QObject):
    def __init__(self, name=None, location=None, config=None, serial_number=None):
        super().__init__()

        self.camera, self.name, self.address = self.load_camera_from_serial_number(name, serial_number)
        self.location = location
        self.photos_df = None
        self.config = config
        self.trigger_lock = False  # Prevent camera from being retriggered before prior trigger finished
        self.triggers = 0

        if self.config is not None:
            self.set_config(self.config)

    def set_config(self, dict_):
        for key, value in dict_.items():
            # get camera's config
            config = gp.check_result(gp.gp_camera_get_config(self.camera))

            # find the config item
            config_item = gp.check_result(gp.gp_widget_get_child_by_name(config, key))

            # check if value is in range
            count = gp.check_result(gp.gp_widget_count_choices(config_item))
            if value < 0 or value >= count:
                print('Parameter out of range')

            # set value
            value = gp.check_result(gp.gp_widget_get_choice(config_item, value))
            gp.check_result(gp.gp_widget_set_value(config_item, value))

            # set config
            gp.check_result(gp.gp_camera_set_config(self.camera, config))

            print(f'{self.location} camera {key} set to {value}.')
            
    def set_config2(self, dict_):
        for key, value in dict_.items():
            # get camera's config
            config = gp.check_result(gp.gp_camera_get_config(self.camera))

            # find the config item
            config_item = gp.check_result(gp.gp_widget_get_child_by_name(config, key))

            # check if value is in range
            #count = gp.check_result(gp.gp_widget_count_choices(config_item))
            #if value < 0 or value >= count:
            #    print('Parameter out of range')

            # set value
            #value = gp.check_result(gp.gp_widget_get_choice(config_item, value))
            gp.check_result(gp.gp_widget_set_value(config_item, value))

            # set config
            gp.check_result(gp.gp_camera_set_config(self.camera, config))

            print(f'{self.location} camera {key} set to {value}.')

    def load_camera_from_serial_number(self, name, serial_number):
        # camera_list = read_cameras()
        global camera_list
        for camera in camera_list:
            name_ = camera[0]
            address_ = camera[1]
            serial_number_ = camera[2]
            if name_ == name and serial_number_ == serial_number:
                camera_ = self.load_camera(name_, address_)
                print(name_, address_)
                return camera_, name_, address_
        raise ValueError(f'{name} with serial number {serial_number} could not be loaded!')

    @staticmethod
    def load_camera(name, address):
        if name is not None and address is not None:
            port_info_list = gp.PortInfoList()
            port_info_list.load()
            abilities_list = gp.CameraAbilitiesList()
            abilities_list.load()

            camera = gp.Camera()
            idx = port_info_list.lookup_path(address)
            camera.set_port_info(port_info_list[idx])
            idx = abilities_list.lookup_model(name)
            camera.set_abilities(abilities_list[idx])

            # print(camera.get_summary())

            return camera

    def trigger(self):
        self.trigger_lock = True
        try:
            self.camera.trigger_capture()
            self.triggers += 1
        except Exception as e:  # gphoto error
            print(f'{self.location} camera could not trigger, error: {e}.')
        self.trigger_lock = False

    def take_and_transfer_photo(self):
        pass

    def save(self, **kwargs):
        pass

    @staticmethod
    def detect_cameras():
        cameras = gp.Camera.autodetect()

        if len(cameras) == 0:
            print('No cameras detected! :(')
        for n, (name, value) in enumerate(cameras):
            print('camera number', n)
            print('===============')
            print(name)
            print(value)
            # assign a camera id to each detected camera and return each cameras as Camera objects
            # Therefore, one could do camera1, camera2, camera3 = Camera.detect_cameras()
            # On the other hand, it may be best to not return anything and assign cameras
            # based on IDs


def read_cameras():
    cameras = list(gp.Camera.autodetect())
    camera_info = []
    for i, info in enumerate(cameras):
        name = info[0]
        address = info[1]
        serial_number = get_camera_serial_number(name, address)
        camera_info.append((name, address, serial_number))

    return camera_info


def get_camera_serial_number(name, address):
    camera = gp.Camera()

    port_info_list = gp.PortInfoList()
    port_info_list.load()
    abilities_list = gp.CameraAbilitiesList()
    abilities_list.load()

    idx = port_info_list.lookup_path(address)
    camera.set_port_info(port_info_list[idx])
    idx = abilities_list.lookup_model(name)
    camera.set_abilities(abilities_list[idx])

    # camera.set_config

    summary = str(camera.get_summary())
    sn_pattern = 'Serial Number: [0-9]{32}'
    sn_text = re.findall(sn_pattern, summary)[0]
    serial_number = int(re.findall('[0-9]{32}', sn_text)[0])

    camera.exit()

    return serial_number


camera_list = read_cameras()

if __name__ == '__main__':
    print('This file is not intended to be executed on its own!')
