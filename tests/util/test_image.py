import unittest
from PIL import Image
from tests import TestCase, ASSETS_PATH
from ocrd_browser.util.image import pil_to_pixbuf, _pil_to_pixbuf_via_cv, _pil_to_pixbuf_via_pixbuf_loader
from timeit import timeit


class ImageUtilTestCase(TestCase):

    def test_pil_to_pixbuf_is_faster_via_opencv(self):
        files = [
            ASSETS_PATH / 'kant_aufklaerung_1784-binarized/data/OCR-D-IMG/OCR-D-IMG_0017.tif',
            ASSETS_PATH / 'kant_aufklaerung_1784-binarized/data/OCR-D-IMG-1BIT/OCR-D-IMG-1BIT_0017.png',
            ASSETS_PATH / 'kant_aufklaerung_1784-binarized/data/OCR-D-IMG-NRM/OCR-D-IMG-NRM_0017.png',
        ]
        for file in files:
            via_cv_time, via_pil_time = self._test_pil_to_pixbuf_performance_on_file(file)
            print('OpenCV({}s) vs. PIL({}s): {} for {}'.format(via_cv_time, via_pil_time, via_cv_time/via_pil_time, file))
            self.assertLess(via_cv_time, via_pil_time, 'via_cv took longer for {}'.format(file))

    @staticmethod
    def _test_pil_to_pixbuf_performance_on_file(file, number: int = 5):
        image: Image.Image = Image.open(file)
        image.load()

        via_cv_time = timeit(lambda : _pil_to_pixbuf_via_cv(image), number=number)
        via_pil_time = timeit(lambda : _pil_to_pixbuf_via_pixbuf_loader(image), number=number)

        return via_cv_time,via_pil_time


if __name__ == '__main__':
    unittest.main()
