from ocrd import Workspace, Resolver
from ocrd_browser.model import Page
from ocrd_modelfactory import page_from_file
from ocrd_models import OcrdFile
from ocrd_models.ocrd_page_generateds import PcGtsType
from ocrd_models.constants import NAMESPACES as NS
from ocrd_utils import pushd_popd
from ocrd_utils.constants import MIME_TO_EXT
from . import DEFAULT_FILE_GROUP

from typing import Optional, Tuple, List, Set, Union
from collections import OrderedDict
from pathlib import Path
from urllib.parse import urlparse
from lxml.etree import ElementBase as Element

import cv2
import struct
import zlib


class Document:

    def __init__(self, window, workspace: Workspace, mets_url=None, resolver: Resolver = None):
        self.window = window
        self.mets_url = mets_url
        self.workspace: Workspace = workspace
        self.resolver: Resolver = resolver if resolver else Resolver()
        self.empty = True

    @classmethod
    def create(cls, window, directory=None, resolver: Resolver = None) -> 'Document':
        resolver = resolver if resolver else Resolver()
        workspace = resolver.workspace_from_nothing(directory=directory, mets_basename='mets.xml')
        return cls(window, workspace, None, resolver)

    @classmethod
    def load(cls, window, mets_url=None, resolver: Resolver = None) -> 'Document':
        if not mets_url:
            return cls.create(window, None, resolver)
        mets_url = str(mets_url)
        result = urlparse(mets_url)
        if result.scheme == 'file':
            mets_url = result.path

        resolver = resolver if resolver else Resolver()
        workspace = resolver.workspace_from_url(mets_url, download=True)
        doc = cls(window, workspace, mets_url, resolver)
        doc.empty = False
        return doc

    @property
    def directory(self) -> Path:
        """
        Get workspace directory as a Path object
        """
        return Path(self.workspace.directory)

    def path(self, other: Union[OcrdFile, Path, str]) -> Path:
        """
        Resolves other relative to current workspace
        """
        if isinstance(other, OcrdFile):
            return self.directory / other.local_filename
        elif isinstance(other, Path):
            return self.directory / other
        elif isinstance(other, str):
            return self.directory / other

    @property
    def page_ids(self) -> list:
        """
        List of page_ids in this workspace

        TODO: This is unsorted (or sorted in document order) use @ORDER attribute or keep document order in sync with the correct order

        @return: List[str]
        """
        return self.workspace.mets.physical_pages

    @property
    def file_groups(self) -> List[str]:
        """
        List of file_groups in this workspace

        @return: List[str]
        """

        return self.workspace.mets.file_groups

    @property
    def mime_types(self) -> Set[str]:
        """
        Set with the distinct mime-types in this workspace

        @return: Set[str]
        """
        return {el.get('MIMETYPE') for el in
                self.workspace.mets._tree.findall('mets:fileSec/mets:fileGrp/mets:file[@MIMETYPE]', NS)}

    @property
    def file_groups_and_mimetypes(self) -> List[Tuple[str, str]]:
        """
        A list with the distinct file_group/mimetype pairs in this workspace

        @return: List[Tuple[str,str]]
        """
        distinct_groups = OrderedDict()
        for el in self.workspace.mets._tree.findall('mets:fileSec/mets:fileGrp[@USE]/mets:file[@MIMETYPE]', NS):
            distinct_groups[(el.getparent().get('USE'), el.get('MIMETYPE'))] = None

        return list(distinct_groups.keys())

    def get_unused_page_id(self, template_page_id: str = 'PAGE_{page_nr}') -> Tuple[str, int]:
        """
        Finds a page_nr that yields an unused page_id for the workspace and returns page_id, page_nr

        @param template_page_id: str
        @return: Tuple[str, int]
        """
        page_nr = len(self.page_ids) + 1
        page_ids = self.page_ids
        while page_nr < 9999:
            page_id = template_page_id.format(**{'page_nr': page_nr})
            if page_id not in page_ids:
                return page_id, page_nr
            page_nr += 1

        raise RuntimeError('No unused page_id found')

    def display_id_range(self, page_id, page_qty):
        """
        Calculates an page_id range of size page_qty around page_id
        @param page_id:
        @param page_qty:
        @return:
        """
        if not page_id:
            return []
        try:
            index = self.page_ids.index(page_id)
        except ValueError:
            return []
        index = index - index % page_qty
        return self.page_ids[index:index + page_qty]

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
            files = self.workspace.mets.find_files(fileGrp=file_group or DEFAULT_FILE_GROUP, pageId=page_id)
            if not files:
                return None
            return self.workspace.download_file(files[0])

    def page_for_file(self, page_file: OcrdFile) -> PcGtsType:
        with pushd_popd(self.workspace.directory):
            return page_from_file(page_file)

    def reorder(self, ordered_page_ids: List[str]):
        """
        Orders the pages in physSequence according to ordered_page_ids

        """
        if set(self.page_ids) != set(ordered_page_ids):
            raise ValueError('page_ids do not match: missing in mets.xml: {} / missing in order: {}'.format(
                set(ordered_page_ids).difference(set(self.page_ids)),
                set(self.page_ids).difference(set(ordered_page_ids))
            ))

        page_sequence: Element = self.workspace.mets._tree.getroot().xpath(
            '/mets:mets/mets:structMap[@TYPE="PHYSICAL"]/mets:div[@TYPE="physSequence"]',
            namespaces=NS)[0]

        ordered_divs = []
        for page_id in ordered_page_ids:
            divs = page_sequence.xpath('mets:div[@TYPE="page"][@ID="%s"]' % page_id, namespaces=NS)
            if divs:
                ordered_divs.append(divs[0])
                page_sequence.remove(divs[0])

        if len(page_sequence) > 0:
            raise RuntimeError('page_sequence not empty, still has: {}'.format(page_sequence.getchildren()))

        for div in ordered_divs:
            page_sequence.append(div)

    def save(self):
        self.workspace.save_mets()
        self.window.emit('document_saved')

    def delete_image(self, page_id, file_group='OCR-D-IMG') -> OcrdFile:
        image_files = self.workspace.mets.find_files(pageId=page_id, fileGrp=file_group, local_only=True,
                                                     mimetype='//image/.+')
        # TODO rename to delete_images and cope with it, e.g. for file groups with segementation images
        if len(image_files) != 1:
            print('oh oh', image_files)
            return
        image_file = image_files[0]
        self.workspace.remove_file(image_file, force=False, keep_file=False, page_recursive=True, page_same_group=True)
        self.window.emit('document_changed', [page_id])
        self.save()
        return image_file

    def delete_page(self, page_id) -> OcrdFile:
        files = self.workspace.mets.find_files(pageId=page_id, local_only=True)
        for file in files:
            self.workspace.remove_file(file, force=False, keep_file=False)
        self.window.emit('document_changed', [page_id])
        self.save()

    def add_image(self, image, page_id, file_id, file_group='OCR-D-IMG', dpi: int = 300,
                  mimetype='image/png') -> 'OcrdFile':
        extension = MIME_TO_EXT[mimetype]
        retval, image_bytes = cv2.imencode(extension, image)
        image_bytes = self._add_dpi_to_png_buffer(image_bytes, dpi)
        local_filename = Path(file_group, '%s%s' % (file_id, extension))
        url = (Path(self.workspace.directory) / local_filename)
        current_file = self.workspace.add_file(file_group, ID=file_id, mimetype=mimetype, force=True,
                                               content=image_bytes, url=str(url),
                                               local_filename=str(local_filename), pageId=page_id)
        self.empty = False
        self.window.emit('document_changed', [page_id])
        self.save()
        return current_file

    @staticmethod
    def _add_dpi_to_png_buffer(image_bytes, dpi=300):
        """
        adds dpi information to a png image

        see https://stackoverflow.com/questions/57553641/how-to-save-dpi-info-in-py-opencv/57555123#57555123

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
