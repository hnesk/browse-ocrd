import unittest
from PIL import Image, ImageDraw
from gi.repository import GdkPixbuf

from tests import TestCase, ASSETS_PATH, data_provider
from ocrd_browser.util.image import pil_to_pixbuf, _pil_to_pixbuf_via_cv, _pil_to_pixbuf_via_pixbuf_loader
from timeit import timeit


def _image_modes():
    return (
        ('RGB',
         (0, 0, 0), (127, 127, 127), (255, 255, 255),
         (0, 0, 0), (127, 127, 127), (255, 255, 255)
         ),
        ('RGBA',
         (0, 0, 0, 128), (255, 0, 255, 255), (255, 255, 255, 255),
         (0, 0, 0, 128), (255, 0, 255, 255), (255, 255, 255, 255)
         ),
        ('1',
         (0,), (1,), (1,),
         (0, 0, 0), (255, 255, 255), (255, 255, 255)
         ),
        ('LA',
         (0, 127), (255, 255), (0, 127),
         (0, 0, 0, 127), (255, 255, 255, 255), (0, 0, 0, 127)
         ),
    )


class ImageUtilTestCase(TestCase):

    def test_pil_to_pixbuf_is_faster_via_opencv(self):
        self.skipTest('Slow test')
        files = [
            ASSETS_PATH / 'kant_aufklaerung_1784-binarized/data/OCR-D-IMG/OCR-D-IMG_0017.tif',
            ASSETS_PATH / 'kant_aufklaerung_1784-binarized/data/OCR-D-IMG-1BIT/OCR-D-IMG-1BIT_0017.png',
            ASSETS_PATH / 'kant_aufklaerung_1784-binarized/data/OCR-D-IMG-NRM/OCR-D-IMG-NRM_0017.png',
        ]
        for file in files:
            via_cv_time, via_pil_time = self._test_pil_to_pixbuf_performance_on_file(file)
            print('OpenCV({}s) vs. PIL({}s): {} for {}'.format(via_cv_time, via_pil_time, via_cv_time / via_pil_time,
                                                               file))
            self.assertLess(via_cv_time, via_pil_time, 'via_cv took longer for {}'.format(file))

    @data_provider(_image_modes)
    def test_image_modes(self, mode, bg, fg1, fg2, bg_test, fg1_test, fg2_test):
        pil = self._generate_test_image(mode, bg, fg1, fg2)
        pb = pil_to_pixbuf(pil)
        self.assertSequenceEqual(bg_test, self._get_pixbuf_pixel(pb, 0, 10))
        self.assertSequenceEqual(fg1_test, self._get_pixbuf_pixel(pb, 0, 0))
        self.assertSequenceEqual(fg2_test, self._get_pixbuf_pixel(pb, pil.size[0] - 1, 1))

    @staticmethod
    def _get_pixbuf_pixel(pb: GdkPixbuf.Pixbuf, x, y):
        bytes = pb.get_pixels()
        n_channels = pb.get_n_channels()
        rowstride = pb.get_rowstride()
        bps = pb.get_bits_per_sample()

        bytes_per_pixel = int(n_channels * bps / 8)
        offset = y * rowstride + x * bytes_per_pixel

        return list(bytes[offset:offset + bytes_per_pixel])

    @staticmethod
    def _generate_test_image(mode, bg, fg1, fg2):
        im = Image.new(mode, (50, 30), bg)
        draw = ImageDraw.Draw(im)
        w, h = im.size
        draw.line((0, 0, w, h), fill=fg1)
        draw.line((0, h, w, 0), fill=fg2)
        return im

    @staticmethod
    def _test_pil_to_pixbuf_performance_on_file(file, number: int = 10):
        image: Image.Image = Image.open(file)
        image.load()

        via_cv_time = timeit(lambda: _pil_to_pixbuf_via_cv(image), number=number)
        via_pil_time = timeit(lambda: _pil_to_pixbuf_via_pixbuf_loader(image), number=number)

        return via_cv_time, via_pil_time


if __name__ == '__main__':
    unittest.main()
