from ocrd import Workspace, Resolver
from pathlib import Path
import cv2
import struct
import zlib
import magic

class Document:
    def __init__(self, workspace: Workspace, resolver: Resolver = None):
        self.workspace = workspace
        self.resolver = resolver if resolver else Resolver()
        self.current_file = None
        self.count = 0

    @classmethod
    def create(cls, directory = None, resolver: Resolver = None) -> 'Document':
        resolver = resolver if resolver else Resolver()
        workspace = resolver.workspace_from_nothing(directory=directory,mets_basename='mets.xml')
        return cls(workspace, resolver);

    def save(self):
        self.workspace.save_mets()

    def add_image(self, image, dpi = 300):
        retval, imagebytes = cv2.imencode(".png", image)
        imagebytes = self._add_dpi_to_cv_image(imagebytes, dpi)
        file_group = 'OCR-D-IMG'
        file_id = '{}_{:04d}'.format(file_group, self.count)
        page_id = 'PAGE_{:04d}'.format(self.count)

        extension = '.png'
        mimetype = 'image/png'
        basename = file_id + extension
        local_filename = str(Path(file_group, '%s%s' % (file_id, extension)))
        self.current_file = self.workspace.add_file(file_group, ID=file_id, mimetype=mimetype, force=True, content=imagebytes, local_filename=local_filename, pageId=page_id)
        print(self.current_file)
        self.count += 1



    def _add_dpi_to_cv_image(self, imagebytes, dpi = 300):
        if isinstance(dpi, (int,float)):
            dpi = (dpi, dpi)
        s = imagebytes.tostring()

        # Find start of IDAT chunk
        IDAToffset = s.find(b'IDAT') - 4

        # Create our lovely new pHYs chunk - https://www.w3.org/TR/2003/REC-PNG-20031110/#11pHYs
        pHYs = b'pHYs' + struct.pack('!IIc', int(dpi[0] / 0.0254), int(dpi[1] / 0.0254), b"\x01")
        pHYs = struct.pack('!I', 9) + pHYs + struct.pack('!I', zlib.crc32(pHYs))


        return s[0:IDAToffset] + pHYs + s[IDAToffset:]

    def add_page(self, page_image):
        file_group = 'OCR-D-IMG'
        file_id = '{}_{:04d}'.format(file_group, self.count)
        page_id = 'PAGE_{:04d}'.format(self.count)
        mimetype = 'image/png'
        basename = file_id + '.png'
        local_filename = self.resolver.download_to_directory(self.workspace.directory, str(page_image), basename, subdir=file_group, if_exists='overwrite')
        print(local_filename)
        self.workspace.add_file(file_group, ID=file_id, mimetype=mimetype, force=True, url=local_filename,
                                local_filename=local_filename, pageId=page_id)
        self.workspace.save_image_file()
        self.count += 1


