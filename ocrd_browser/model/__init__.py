from typing import Optional

from PIL.Image import Image
from ocrd import Workspace, Resolver
from ocrd_modelfactory import page_from_file
from ocrd_models import OcrdFile, OcrdExif
from pathlib import Path
import cv2
import struct
import zlib

from ocrd_models.ocrd_page_generateds import PcGtsType, PageType, MetadataType
from ocrd_utils import pushd_popd

class Document:
    def __init__(self, workspace: Workspace, resolver: Resolver = None, file_group = 'OCR-D-IMG'):
        self.current_file:OcrdFile = None
        self.workspace: Workspace = workspace
        self.resolver: Resolver = resolver if resolver else Resolver()
        self.file_group: str = file_group

    @property
    def page_ids(self) -> list:
        return self.workspace.mets.physical_pages

    @classmethod
    def create(cls, directory = None, resolver: Resolver = None) -> 'Document':
        resolver = resolver if resolver else Resolver()
        workspace = resolver.workspace_from_nothing(directory=directory,mets_basename='mets.xml')
        return cls(workspace, resolver)

    @classmethod
    def load(cls, mets_url = None, resolver: Resolver = None) -> 'Document':
        if not mets_url:
            return cls.create(None, resolver)
        resolver = resolver if resolver else Resolver()
        workspace = resolver.workspace_from_url(mets_url, download=True)
        doc = cls(workspace, resolver)
        return doc

    def page_for_id(self, page_id:str, file_group: str = None) -> Optional['Page']:
        page_file = self.file_for_page_id(page_id, file_group)
        if not page_file:
            return None
        pcgts = self.page_for_file(page_file)
        page = pcgts.get_Page()
        image, info, exif = self.workspace.image_from_page(page, page_id)
        return Page(page_id, page_file, pcgts, image, exif)


    def file_for_page_id(self, page_id, file_group = None) -> Optional[OcrdFile]:
        with pushd_popd(self.workspace.directory):
            files = self.workspace.mets.find_files(fileGrp=file_group if file_group else self.file_group, pageId=page_id)
            if not files:
                return None
            return self.workspace.download_file(files[0])

    def page_for_file(self, page_file: OcrdFile) -> PcGtsType:
        with pushd_popd(self.workspace.directory):
            return page_from_file(page_file)


    def save(self):
        self.workspace.save_mets()

    def add_images(self, images, dpi = 300):
        if len(images) % self.pages_at_once != 0:
            raise Exception('len(images)({0}) % self.pages_at_one({1}) != 0'.format(len(images), self.pages_at_once))
        for image in images:
            self.add_image(image, dpi)

    def add_image(self, image, dpi:int = 300) -> 'OcrdFile':
        retval, imagebytes = cv2.imencode(".png", image)
        imagebytes = self._add_dpi_to_png_buffer(imagebytes, dpi)
        file_group = 'OCR-D-IMG'
        file_id = '{}_{:04d}'.format(file_group, self.position)
        page_id = 'PAGE_{:04d}'.format(self.position)

        extension = '.png'
        mimetype = 'image/png'
        local_filename = Path(file_group, '%s%s' % (file_id, extension))
        url = Path(self.workspace.directory) / local_filename
        self.current_file = self.workspace.add_file(file_group, ID=file_id, mimetype=mimetype, force=True, content=imagebytes, url=str(url), local_filename=str(local_filename), pageId=page_id)
        return self.current_file

    @staticmethod
    def _add_dpi_to_png_buffer(imagebytes, dpi = 300):
        """
        adds dpi information to a png image

        :param imagebytes:
        :param dpi:
        :return:
        """
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
        file_id = '{}_{:04d}'.format(self.file_group, self.count)
        page_id = 'PAGE_{:04d}'.format(self.count)
        mimetype = 'image/png'
        basename = file_id + '.png'
        local_filename = self.resolver.download_to_directory(self.workspace.directory, str(page_image), basename, subdir=self.file_group, if_exists='overwrite')
        #print(local_filename)
        self.workspace.add_file(self.file_group, ID=file_id, mimetype=mimetype, force=True, url=local_filename,
                                local_filename=local_filename, pageId=page_id)



class Page:
    def __init__(self, id: str, file: OcrdFile, pcGts: PcGtsType, image: Image, exif: OcrdExif):
        self.id:str = id
        self.file:OcrdFile = file
        self.pcGts: PcGtsType = pcGts
        self.image: Image = image
        self.exif: OcrdExif = exif

    @property
    def page(self) -> PageType:
        return self.pcGts.get_Page()

    @property
    def meta(self) -> MetadataType:
        return self.pcGts.get_Metadata()