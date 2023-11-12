from PyQt5 import QtCore, QtWidgets
from ui.main_window import Ui_MainWindow
import sensors
import datetime


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)


class CameraCart:
    def __init__(self, field_name):
        app = QtWidgets.QApplication([])
        app.setStyle('Fusion')
        self.app = app
        self.window = MainWindow()

        # Colons in time replaced with hyphen due to colon being a prohibited character in file names in Windows
        self.time = datetime.datetime.now().strftime("T%H-%M-%SZ")

        self.movement_sensor = sensors.MovementSensor(gpio_pin=10, movement_distance=19.5)
        self.moved = False

        # Might want to also include ability to set camera time so Pi and cameras are synchronized
        self.d3500_config = {'capturetarget': 1,  # 'Memory card'
                             'autofocus': 1,  # 'Off'
                             'focusmode': 0,  # Off (But does not change autofocus to manual)
                             'focusmode2': 4,  # MF (selection) - this does work!
                             'capturemode': 1,  # 'Burst'
                             'whitebalance': 1,  # Daylight
                             'iso': 0,  # 100
                             'imagesize': 0,  # 6000x4000
                             'isoauto': 1,  # Off
                             'autoiso': 1,  # Off
                             'shutterspeed': 9,  # 1/640s -- to disable, turn camera wheel to A and all other settings should still work
                             'f-number': 7,  # 7 = f/8
                             'assistlight': 1  # Turn off assist light
                             }

        self.d3300_config = {'capturetarget': 1,  # 'Memory card'
                             'autofocus': 1,  # 'Off'
                             'focusmode': 0,
                             'focusmode2': 4,
                             'capturemode': 1,  # 'Burst'
                             'iso': 0,  # 100
                             'imagesize': 0,  # 6000x4000
                             'isoauto': 0,  # Off
                             'shutterspeed': 9,  # 1/500s
                             'f-number': 7  # 7 = f/8
                             }

        self.camera0 = sensors.Camera(name='Nikon DSC D3500', location='left', config=self.d3500_config,
                                      serial_number=3534517)
        self.camera1 = sensors.Camera(name='Nikon DSC D3300', location='center', config=self.d3300_config,
                                      serial_number=3804012)
        self.camera2 = sensors.Camera(name='Nikon DSC D3500', location='right', config=self.d3500_config,
                                      serial_number=3534475)

        # May get the following error:
        # gphoto2.GPhoto2Error: [-53] Could not claim the USB device
        # Was resolved by turning camera off and back on again

        self.window.ui.time_label.setText('')
        self.window.ui.solar_elevation_label.setText('')
        self.window.ui.solar_azimuth_label.setText('')
        self.window.ui.latitude_label.setText('')
        self.window.ui.longitude_label.setText('')
        self.window.ui.compass_label.setText('')
        self.window.ui.distance_traveled_label.setText('')

        self.movement_thread = QtCore.QThread()
        self.movement_sensor.moveToThread(self.movement_thread)

        self.movement_check_timer = QtCore.QTimer(interval=50, timeout=self.movement_sensor.moved_)
        # Uncomment this line if magnet fails, adjust timing between 500 and 1000 ms
        # self.movement_check_timer = QtCore.QTimer(interval=1000, timeout=self.movement_sensor.moved_)

        self.camera0_thread = QtCore.QThread()
        self.camera0.moveToThread(self.camera0_thread)
        self.camera1_thread = QtCore.QThread()
        self.camera1.moveToThread(self.camera1_thread)
        self.camera2_thread = QtCore.QThread()
        self.camera2.moveToThread(self.camera2_thread)

        self.camera0_thread.start()
        self.camera1_thread.start()
        self.camera2_thread.start()

        self.movement_sensor.moved.connect(self.movement_check_timer.stop)
        self.movement_sensor.moved.connect(self.camera0.trigger)
        self.movement_sensor.moved.connect(self.camera1.trigger)
        self.movement_sensor.moved.connect(self.camera2.trigger)
        self.movement_sensor.moved.connect(self.update_window)
        self.movement_sensor.moved.connect(self.movement_check_timer.start)

        self.movement_thread.start()

        self.movement_check_timer.start()  # Don't see a need to stop/start this elsewhere

        self.window.ui.focus_cameras_btn.clicked.connect(self.focus_cameras)

        self.window.ui.reset_1_btn.clicked.connect(self.reset_left_camera)
        self.window.ui.reset_2_btn.clicked.connect(self.reset_center_camera)
        self.window.ui.reset_3_btn.clicked.connect(self.reset_right_camera)

    @staticmethod
    def setup_app():
        app = QtWidgets.QApplication([])
        app.setStyle('Fusion')

        return app

    def update_window(self):
        self.window.ui.time_label.setText(datetime.datetime.now().strftime("%H:%M:%S"))
        self.window.ui.distance_traveled_label.setText(str(self.movement_sensor.cumulative_distance))
        self.window.ui.photos_taken_1.setText(str(self.camera0.triggers))
        self.window.ui.photos_taken_2.setText(str(self.camera1.triggers))
        self.window.ui.photos_taken_3.setText(str(self.camera2.triggers))
        self.window.ui.latitude_label.setText('')
        self.window.ui.longitude_label.setText('')

    def focus_cameras(self):
        CameraCart.focus(self.camera0)
        CameraCart.focus(self.camera1)
        CameraCart.focus(self.camera2)

    @staticmethod
    def focus(camera):
        
        af_config = {'focusmode2': 0#,  # Set to AF-S
                     #'autofocusdrive': 1  # Toggle autofocus drive
                     }

        camera.set_config(af_config)
        
        camera.trigger()

        mf_config = {'focusmode2': 4  # Set back to MF
                     }

        camera.set_config(mf_config)

    def reset_left_camera(self):
        try:
            self.camera0 = sensors.Camera(name='Nikon DSC D3500', location='left', config=self.d3500_config,
                                          serial_number=3534517)
            self.update_window()
        except Exception as e:
            print(f'Could not reset camera: {e}')

    def reset_center_camera(self):
        try:
            self.camera1 = sensors.Camera(name='Nikon DSC D3300', location='center', config=self.d3300_config,
                                          serial_number=3804012)
            self.update_window()
        except Exception as e:
            print(f'Could not reset camera: {e}')

    def reset_right_camera(self):
        try:
            self.camera2 = sensors.Camera(name='Nikon DSC D3500', location='right', config=self.d3500_config,
                                          serial_number=3534475)
            self.update_window()
        except Exception as e:
            print(f'Could not reset camera: {e}')


if __name__ == '__main__':
    cart = CameraCart('Test')
    cart.window.show()
    cart.app.exec_()
