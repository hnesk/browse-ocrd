import io
import cv2
import struct
import zlib

from typing import Tuple, Union
from PIL.Image import Image, fromarray
from numpy import (
    ndarray,
    dtype as np_dtype,
    array as np_array,
    uint8 as np_uint8,
    bool as np_bool,
    stack as np_stack
)
from gi.repository import GdkPixbuf, GLib

__all__ = ['cv_scale', 'cv_to_pixbuf', 'pil_to_pixbuf', 'pil_scale', 'add_dpi_to_png_buffer']


def _bytes_to_pixbuf(bytes_: bytes) -> GdkPixbuf.Pixbuf:
    loader = GdkPixbuf.PixbufLoader()
    loader.write(bytes_)
    loader.close()
    return loader.get_pixbuf()


def _cv_to_pixbuf_via_cv(z: ndarray) -> GdkPixbuf.Pixbuf:
    if z.dtype == np_bool:
        z = (z * 255).astype(np_uint8)
    if z.ndim == 2:
        z = np_stack((z, z, z), axis=2)
    assert z.ndim == 3
    h, w, c = z.shape
    assert c == 3 or c == 4
    if c == 3:
        z = cv2.cvtColor(z, cv2.COLOR_BGR2RGB)
    else:
        z = cv2.cvtColor(z, cv2.COLOR_BGRA2RGBA)
    args = {'colorspace': GdkPixbuf.Colorspace.RGB, 'has_alpha': c == 4, 'bits_per_sample': 8, 'width': w, 'height': h}
    rowstride = w * c
    pb = GdkPixbuf.Pixbuf.new_from_bytes(data=GLib.Bytes(z.tobytes()), rowstride=rowstride, **args)
    return pb


def _cv_to_pixbuf_via_pixbuf_loader(cv_image: ndarray) -> GdkPixbuf:
    ret, byte_array = cv2.imencode('.jpg', cv_image)
    return _bytes_to_pixbuf(byte_array.tobytes())


def _pil_to_pixbuf_via_cv(im: Image) -> GdkPixbuf.Pixbuf:
    if im.mode == 'LA':
        bgra = cv2.cvtColor(np_array(im.convert('L'), dtype=np_uint8), cv2.COLOR_GRAY2BGRA)
        bgra[:, :, 3] = np_array(im.getchannel('A'), dtype=np_uint8)
        im = bgra
    elif im.mode == 'RGBA':
        bgra = cv2.cvtColor(np_array(im.convert('RGB'), dtype=np_uint8), cv2.COLOR_RGB2BGRA)
        bgra[:, :, 3] = np_array(im.getchannel('A'), dtype=np_uint8)
        im = bgra
    else:
        im = cv2.cvtColor(np_array(im.convert('RGB'), dtype=np_uint8), cv2.COLOR_RGB2BGR)
    return _cv_to_pixbuf_via_cv(im)


def _pil_to_pixbuf_via_pixbuf_loader(im: Image) -> GdkPixbuf.Pixbuf:
    bytes_io = io.BytesIO()
    im.save(bytes_io, "PNG" if im.mode in ("LA", "RGBA") else "JPEG")
    return _bytes_to_pixbuf(bytes_io.getvalue())


def cv_scale(orig: ndarray, w: int = None, h: int = None) -> ndarray:
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


def pil_scale(orig: Image, w: int = None, h: int = None) -> Image:
    """
    Scale a Pillow image
    :param orig: ndarray Original cv2 image
    :param w: New width
    :param h: New height
    :return: ndarray
    """
    new_width, new_height = _calculate_scale(orig.width, orig.height, w, h)
    # thumb = orig.copy()
    # thumb.thumbnail((new_width, new_height))
    # also allows enlarging:
    if orig.mode.startswith('I'):
        # workaround for Pillow#4402:
        arr = np_array(orig)
        if arr.dtype.kind == 'i':
            # signed integer is *not* trustworthy in this context
            # (usually a mistake in the array interface)
            arr.dtype = np_dtype('u' + arr.dtype.name)
        if arr.dtype.kind == 'u':
            # integer needs to be scaled linearly to 8 bit
            # of course, an image might actually have some lower range
            # (e.g. 10-bit in I;16 or 20-bit in I or 4-bit in L),
            # but that would be guessing anyway, so here don't
            # make assumptions on _scale_, just reduce _precision_
            arr = arr >> 8 * (arr.dtype.itemsize - 1)
            arr = arr.astype(np_uint8)
        elif arr.dtype.kind == 'f':
            # float needs to be scaled from [0,1.0] to [0,255]
            arr *= 255
            arr = arr.astype(np_uint8)
        orig = fromarray(arr)
    thumb = orig.resize((new_width, new_height))
    return thumb


def add_dpi_to_png_buffer(image_bytes: bytes, dpi: Union[int, Tuple[int, int]] = 300) -> bytes:
    """
    adds dpi information to a png image

    see https://stackoverflow.com/questions/57553641/how-to-save-dpi-info-in-py-opencv/57555123#57555123

    """
    if isinstance(dpi, (int, float)):
        dpi = (dpi, dpi)

    # Find start of IDAT chunk
    idat_offset = image_bytes.find(b'IDAT') - 4

    # Create our lovely new pHYs chunk - https://www.w3.org/TR/2003/REC-PNG-20031110/#11pHYs
    phys_chunk = b'pHYs' + struct.pack('!IIc', int(dpi[0] / 0.0254), int(dpi[1] / 0.0254), b"\x01")
    phys_chunk = struct.pack('!I', 9) + phys_chunk + struct.pack('!I', zlib.crc32(phys_chunk))

    return image_bytes[0:idat_offset] + phys_chunk + image_bytes[idat_offset:]


def _calculate_scale(old_width: int, old_height: int, new_width: int = None, new_height: int = None) -> Tuple[int, int]:
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


pil_to_pixbuf = _pil_to_pixbuf_via_cv
cv_to_pixbuf = _cv_to_pixbuf_via_cv

# pil_to_pixbuf = _pil_to_pixbuf_via_pixbuf_loader
# cv_to_pixbuf = _cv_to_pixbuf_via_pixbuf_loader
