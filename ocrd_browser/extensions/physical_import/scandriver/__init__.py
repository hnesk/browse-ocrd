import os
from time import sleep, process_time
from typing import Tuple, Iterator

from PIL import Image
from pathlib import Path
from ppadb.client import Client as AdbClient
from ppadb.device import Device
from retrying import retry


class AbstractScanDriver:

    def setup(self) -> None:
        raise NotImplementedError('Please override setup() in your driver')

    def scan(self, timeout: float = 1) -> Path:
        raise NotImplementedError('Please override scan() in your driver')

    @staticmethod
    def verify_image_file(image_file: str) -> bool:
        try:
            if os.path.getsize(image_file) < 10000:
                raise RuntimeError('Too small, thumbnail? ({0}B)'.format(os.path.getsize(image_file)))
            image = Image.open(image_file)
            if image.width < 1000 or image.height < 1000:
                raise RuntimeError('Looks like a thumbnail ({0}x{1})'.format(image.width, image.height))
            image.verify()
            image.close()
            image = Image.open(image_file)
            image.thumbnail((1, 1))
            image.close()
            return True
        except Exception as e:
            return False


class AndroidADBDriver(AbstractScanDriver):

    def __init__(self, host: str = "127.0.0.1", port: int = 5037):
        self.host = host
        self.port = port
        self.client: AdbClient = None
        self.device: Device = None

        self.camera_path: str = None
        self.newest_photo: str = None

    def setup(self) -> None:
        self.client = self._connect()
        self.device = self._get_device()
        self.device.input_keyevent('KEYCODE_WAKEUP')
        self.device.input_keyevent('KEYCODE_MENU')
        self.device.shell('am start -a android.media.action.STILL_IMAGE_CAMERA')
        self.camera_path = self.device.shell('echo $EXTERNAL_STORAGE/DCIM/Camera').strip()
        self.newest_photo = self._get_newest_photo()

    def scan(self, timeout: float = 1) -> Path:
        previous_photo = self._get_newest_photo()
        self.device.input_keyevent('KEYCODE_CAMERA')

        self.newest_photo = self._wait_for_image_file(previous_photo, timeout)
        local_file, remote_file = self._pull_image_file()

        self._delete_remote_file(remote_file)

        return Path(local_file)

    def _wait_for_image_file(self, previous_photo: str, timeout: float = 1) -> str:
        start = process_time()
        newest_photo = previous_photo
        while previous_photo == self._get_newest_photo():
            if process_time() - start > timeout:
                raise TimeoutError('Waited {0} seconds, still no image', str(timeout))
            sleep(0.1)
            newest_photo = self._get_newest_photo()

        return self._get_newest_photo()

    @retry(wait_fixed=50, stop_max_delay=2000)
    def _pull_image_file(self) -> Tuple[str, str]:
        local_file = '/tmp/{0}'.format(self.newest_photo)
        remote_file = '{0}/{1}'.format(self.camera_path, self.newest_photo)

        self.device.pull(remote_file, local_file)
        self._stat(remote_file)

        remote_size = int(self._stat(remote_file))
        local_size = int(os.path.getsize(local_file))
        if remote_size != local_size:
            # display('{0} - {1}'.format(remote_size, local_size))
            raise IOError('Image not there yet')

        if not self.verify_image_file(local_file):
            raise IOError('Image is broken')

        return local_file, remote_file

    def _get_newest_photo(self) -> str:
        return str(self.device.shell("ls -t1b {0} | head -n1".format(self.camera_path))).strip()

    def _stat(self, file: str, format_string: str = '%s') -> str:
        return str(self.device.shell("stat -c{0} {1}".format(format_string, file))).strip()

    def _delete_remote_file(self, remote_file: str) -> None:
        self.device.shell('rm {0}'.format(remote_file))

    def _get_device(self) -> Device:
        for dev in self.client.devices():
            if dev.get_state() == 'device':
                return dev
        raise RuntimeError('No device found')

    def _connect(self, tries: int = 1) -> AdbClient:
        try:
            client = AdbClient(host=self.host, port=self.port)
            client.version()
            return client
        except RuntimeError as e:
            if isinstance(e.__context__, ConnectionRefusedError) and tries > 0:
                os.system('adb start-server')
                return self._connect(tries - 1)
            else:
                raise e


class DummyDriver(AbstractScanDriver):
    def __init__(self, directory: str = '/home/jk/Projekte/archive-tools/projects/sym-mach/orig'):
        self.directory: str = directory
        self.files: Iterator[Path] = None

    def setup(self) -> None:
        self.files = iter(sorted(Path(self.directory).glob('*.jpg')))

    def scan(self, timeout: float = 1) -> Path:
        return next(self.files)
