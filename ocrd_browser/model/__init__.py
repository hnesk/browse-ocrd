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
    def __init__(self, workspace: Workspace, resolver: Resolver = None, file_group='OCR-D-IMG'):
        self.current_file: OcrdFile = None
        self.workspace: Workspace = workspace
        self.resolver: Resolver = resolver if resolver else Resolver()
        self.file_group: str = file_group

    @property
    def page_ids(self) -> list:
        return self.workspace.mets.physical_pages

    @property
    def file_groups(self) -> list:
        return self.workspace.mets.file_groups

    @classmethod
    def create(cls, directory=None, resolver: Resolver = None) -> 'Document':
        resolver = resolver if resolver else Resolver()
        workspace = resolver.workspace_from_nothing(directory=directory, mets_basename='mets.xml')
        return cls(workspace, resolver)

    @classmethod
    def load(cls, mets_url=None, resolver: Resolver = None) -> 'Document':
        if not mets_url:
            return cls.create(None, resolver)
        resolver = resolver if resolver else Resolver()
        workspace = resolver.workspace_from_url(mets_url, download=True)
        doc = cls(workspace, resolver)
        return doc

    def page_for_id(self, page_id: str, file_group: str = None) -> Optional['Page']:
        page_file = self.file_for_page_id(page_id, file_group)
        if not page_file:
            return None
        pcgts = self.page_for_file(page_file)
        page = pcgts.get_Page()
        image, info, exif = self.workspace.image_from_page(page, page_id)
        return Page(page_id, page_file, pcgts, image, exif)

    def file_for_page_id(self, page_id, file_group=None) -> Optional[OcrdFile]:
        with pushd_popd(self.workspace.directory):
            files = self.workspace.mets.find_files(fileGrp=file_group if file_group else self.file_group,
                                                   pageId=page_id)
            if not files:
                return None
            return self.workspace.download_file(files[0])

    @property
    def directory(self) -> Path:
        return Path(self.workspace.directory)

    def path(self, other) -> Path:
        if isinstance(other, OcrdFile):
            return self.directory / other.local_filename
        elif isinstance(other, Path):
            return self.directory / other
        elif isinstance(other, str):
            return self.directory / other

    def page_for_file(self, page_file: OcrdFile) -> PcGtsType:
        with pushd_popd(self.workspace.directory):
            return page_from_file(page_file)

    def save(self):
        self.workspace.save_mets()

    def add_image(self, image, page_nr, dpi: int = 300) -> 'OcrdFile':
        retval, image_bytes = cv2.imencode(".png", image)
        image_bytes = self._add_dpi_to_png_buffer(image_bytes, dpi)
        file_group = 'OCR-D-IMG'
        file_id = '{}_{:04d}'.format(file_group, page_nr)
        page_id = 'PAGE_{:04d}'.format(page_nr)

        extension = '.png'
        mime_type = 'image/png'
        local_filename = Path(file_group, '%s%s' % (file_id, extension))
        url = Path(self.workspace.directory) / local_filename
        self.current_file = self.workspace.add_file(file_group, ID=file_id, mimetype=mime_type, force=True,
                                                    content=image_bytes, url=str(url),
                                                    local_filename=str(local_filename), pageId=page_id)
        return self.current_file

    @staticmethod
    def _add_dpi_to_png_buffer(image_bytes, dpi=300):
        """
        adds dpi information to a png image

        :param image_bytes:
        :param dpi:
        :return:
        """
        if isinstance(dpi, (int, float)):
            dpi = (dpi, dpi)
        s = image_bytes.tostring()

        # Find start of IDAT chunk
        idat_offset = s.find(b'IDAT') - 4

        # Create our lovely new pHYs chunk - https://www.w3.org/TR/2003/REC-PNG-20031110/#11pHYs
        phys_chunk = b'pHYs' + struct.pack('!IIc', int(dpi[0] / 0.0254), int(dpi[1] / 0.0254), b"\x01")
        phys_chunk = struct.pack('!I', 9) + phys_chunk + struct.pack('!I', zlib.crc32(phys_chunk))

        return s[0:idat_offset] + phys_chunk + s[idat_offset:]

    def add_page(self, page_image, page_nr):
        file_id = '{}_{:04d}'.format(self.file_group, page_nr)
        page_id = 'PAGE_{:04d}'.format(page_nr)
        mime_type = 'image/png'
        basename = file_id + '.png'
        local_filename = self.resolver.download_to_directory(self.workspace.directory, str(page_image), basename,
                                                             subdir=self.file_group, if_exists='overwrite')
        self.workspace.add_file(self.file_group, ID=file_id, mimetype=mime_type, force=True, url=local_filename,
                                local_filename=local_filename, pageId=page_id)


class Page:
    def __init__(self, id_: str, file: OcrdFile, pc_gts: PcGtsType, image: Image, exif: OcrdExif):
        self.id: str = id_
        self.file: OcrdFile = file
        self.pc_gts: PcGtsType = pc_gts
        self.image: Image = image
        self.exif: OcrdExif = exif

    @property
    def page(self) -> PageType:
        return self.pc_gts.get_Page()

    @property
    def meta(self) -> MetadataType:
        return self.pc_gts.get_Metadata()
