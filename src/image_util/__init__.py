import cv2
import gi
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import GdkPixbuf

__all__ = ['scale','cv_to_pixbuf']

def cv_to_pixbuf(cvimage):
    loader = GdkPixbuf.PixbufLoader()
    ret, byte_array = cv2.imencode('.jpg', cvimage)
    loader.write(byte_array.tobytes())
    loader.close()
    return loader.get_pixbuf()


#def img_to_pix_buf(img):
#    gbytes = GLib.Bytes.new(img.as_blob())
#    stream = Gio.MemoryInputStream.new_from_bytes(gbytes)
#    return GdkPixbuf.Pixbuf.new_from_stream(stream, None)



def scale(orig, w=None, h=None):
    """
    Scale a cv2 image
    :param orig: ndarray Original cv2 image
    :param w: New width
    :param h: New height
    :return: ndarray
    """
    if w and h:
        raise RuntimeError('Cant scale both width and height')

    height, width, depth = orig.shape
    if h:
        imgScale = h / height
    elif w:
        imgScale = w / width
    else:
        imgScale = 1

    newWidth, newHeight = int(width * imgScale), int(height * imgScale)
    return cv2.resize(orig, (newWidth,newHeight))

