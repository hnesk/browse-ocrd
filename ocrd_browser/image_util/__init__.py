import io

import cv2
import gi
from PIL.Image import Image
from numpy import array as ndarray

gi.require_version('GdkPixbuf', '2.0')
from gi.repository import GdkPixbuf

__all__ = ['cv_scale', 'cv_to_pixbuf', 'pil_to_pixbuf', 'pil_scale']


def cv_to_pixbuf(cv_image: ndarray) -> GdkPixbuf:
    ret, byte_array = cv2.imencode('.jpg', cv_image)
    return bytes_to_pixbuf(byte_array.tobytes())


def pil_to_pixbuf(im: Image) -> GdkPixbuf:
    bytes_io = io.BytesIO()
    im.save(bytes_io, "PNG" if im.mode in ("LA", "RGBA") else "JPEG")
    return bytes_to_pixbuf(bytes_io.getvalue())


def bytes_to_pixbuf(bytes_: bytes) -> GdkPixbuf:
    loader = GdkPixbuf.PixbufLoader()
    loader.write(bytes_)
    loader.close()
    return loader.get_pixbuf()


def cv_scale(orig: ndarray, w=None, h=None) -> ndarray:
    """
    Scale a cv2 image
    :param orig: ndarray Original cv2 image
    :param w: New width
    :param h: New height
    :return: ndarray
    """
    height, width, depth = orig.shape
    new_width, new_height = _calculate_scale(width, height, w, h)
    return cv2.resize(orig, (new_width, new_height))


def pil_scale(orig: Image, w=None, h=None) -> ndarray:
    """
    Scale a Pillow image
    :param orig: ndarray Original cv2 image
    :param w: New width
    :param h: New height
    :return: ndarray
    """
    new_width, new_height = _calculate_scale(orig.width, orig.height, w, h)
    thumb = orig.copy()
    thumb.thumbnail((new_width, new_height))
    return thumb


def _calculate_scale(old_width, old_height, new_width: None, new_height: None):
    """
    Calculate scaled image size, while keeping the aspect ratio
    :param old_height:int
    :param old_width:int
    :param new_width:int New width
    :param new_height:int New height
    :return: ndarray
    """
    if new_width and new_height:
        raise RuntimeError('Cant scale both width and height')
    if new_height:
        # noinspection PyUnresolvedReferences
        image_scale = new_height / old_height
    elif new_width:
        # noinspection PyUnresolvedReferences
        image_scale = new_width / old_width
    else:
        image_scale = 1

    return int(old_width * image_scale), int(old_height * image_scale)
