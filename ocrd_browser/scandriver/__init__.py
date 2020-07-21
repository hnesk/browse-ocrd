import os
from ppadb.client import Client as AdbClient
from time import sleep, clock
from PIL import Image
from retrying import retry
from pathlib import Path

class AbstractScanDriver:

    def setup(self):
        raise NotImplementedError('Please override setup() in your driver')

    def scan(self, timeout=1):
        raise NotImplementedError('Please override scan() in your driver')

    @staticmethod
    def verify_image_file(image_file):
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

    def __init__(self, host="127.0.0.1", port=5037):
        self.host = host
        self.port = port
        self.client = None
        self.device = None

        self.camera_path = None
        self.newest_photo = None

    def setup(self):
        self.client = self._connect()
        self.device = self._get_device()
        self.device.input_keyevent('KEYCODE_WAKEUP')
        self.device.input_keyevent('KEYCODE_MENU')
        self.device.shell('am start -a android.media.action.STILL_IMAGE_CAMERA')
        self.camera_path = self.device.shell('echo $EXTERNAL_STORAGE/DCIM/Camera').strip()
        self.newest_photo = self._get_newest_photo()

    def scan(self, timeout=1):
        previous_photo = self._get_newest_photo()
        self.device.input_keyevent('KEYCODE_CAMERA')

        self.newest_photo = self._wait_for_image_file(previous_photo, timeout)
        local_file, remote_file = self._pull_image_file()

        self._delete_remote_file(remote_file)

        return local_file

    def _wait_for_image_file(self, previous_photo, timeout=1):
        start = clock()
        newest_photo = previous_photo
        while previous_photo == self._get_newest_photo():
            if (clock() - start > timeout):
                raise TimeoutError('Waited {0} seconds, still no image', str(timeout))
            sleep(0.1)
            newest_photo = self._get_newest_photo()

        return self._get_newest_photo()

    @retry(wait_fixed=50, stop_max_delay=2000)
    def _pull_image_file(self):
        local_file = '/tmp/{0}'.format(self.newest_photo)
        remote_file = '{0}/{1}'.format(self.camera_path, self.newest_photo)

        self.device.pull(remote_file, local_file)
        self._stat(remote_file)

        remote_size = int(self._stat(remote_file))
        local_size = int(os.path.getsize(local_file))
        if (remote_size != local_size):
            # display('{0} - {1}'.format(remote_size, local_size))
            raise IOError('Image not there yet')

        if not self.verify_image_file(local_file):
            raise IOError('Image is broken')

        return (local_file, remote_file)

    def _get_newest_photo(self):
        return self.device.shell("ls -t1b {0} | head -n1".format(self.camera_path)).strip()

    def _stat(self, file, format_string='%s'):
        return self.device.shell("stat -c{0} {1}".format(format_string, file)).strip()

    def _delete_remote_file(self, remote_file):
        self.device.shell('rm {0}'.format(remote_file))

    def _get_device(self):
        for dev in self.client.devices():
            if dev.get_state() == 'device':
                return dev
        raise RuntimeError('No device found')

    def _connect(self, tries=1):
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
    def __init__(self, directory='/home/jk/Projekte/archive-tools/projects/sym-mach/orig'):
        self.directory = directory
        self.files = None

    def setup(self):
        self.files = iter(sorted(Path(self.directory).glob('*.jpg')))

    def scan(self, timeout=1):
        return next(self.files)


