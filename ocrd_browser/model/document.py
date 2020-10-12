import shutil

from ocrd import Workspace, Resolver
from ocrd_browser.model import Page
from ocrd_browser.util.image import add_dpi_to_png_buffer
from ocrd_modelfactory import page_from_file
from ocrd_models import OcrdFile
from ocrd_models.ocrd_page_generateds import PcGtsType
from ocrd_models.constants import NAMESPACES as NS
from ocrd_utils import pushd_popd
from ocrd_utils.constants import MIME_TO_EXT, MIMETYPE_PAGE
from . import DEFAULT_FILE_GROUP

from logging import getLogger
from typing import Optional, Tuple, List, Set, Union, cast, Callable, Any
from collections import OrderedDict
from pathlib import Path
from tempfile import mkdtemp
from datetime import datetime
from urllib.parse import urlparse
from lxml.etree import ElementBase as Element
from numpy import array as ndarray

import cv2

log = getLogger(__name__)

EventCallBack = Optional[Callable[[str, Any], None]]


class Document:

    def __init__(self, workspace: Workspace, emitter: EventCallBack = None):
        self.emitter: EventCallBack = emitter
        self.workspace: Workspace = workspace
        self.empty = True

    @classmethod
    def create(cls, mets_url: Union[Path, str] = None, emitter: EventCallBack = None) -> 'Document':
        if mets_url:
            mets_path = Path(cls._strip_local(mets_url, disallow_remote=True))
            workspace_directory = mets_path.parent
            mets_basename = mets_path.name
        else:
            workspace_directory = None
            mets_basename = 'mets.xml'

        workspace = Resolver().workspace_from_nothing(directory=workspace_directory, mets_basename=mets_basename)
        return cls(workspace, emitter=emitter)

    @classmethod
    def load(cls, mets_url: Union[Path, str] = None, emitter: EventCallBack = None) -> 'Document':
        """
        Load a project from an url, WARNING! edits the project in place

        Any modifications (page/image deletion) will be done in place, maybe you want to use Document.clone() instead
        """
        if not mets_url:
            return cls.create(None, emitter=emitter)
        mets_url = cls._strip_local(mets_url)

        workspace = Resolver().workspace_from_url(mets_url, download=True)
        doc = cls(workspace, emitter=emitter)
        doc.empty = False
        return doc

    @classmethod
    def clone(cls, mets_url: Union[Path, str], emitter: EventCallBack = None) -> 'Document':
        """
        Clones a project (mets.xml and all used files) to a temporary directory for editing
        """
        mets_url = cls._strip_local(mets_url, disallow_remote=False)
        temporary_workspace = mkdtemp(prefix='browse-ocrd-clone-')
        # TODO download = False and lazy loading would be nice for responsiveness
        log.info("Cloning '%s' to '%s'", mets_url, temporary_workspace)
        workspace = Resolver().workspace_from_url(mets_url=mets_url, dst_dir=temporary_workspace, download=True)
        doc = cls(workspace, emitter=emitter)
        doc.empty = False
        return doc

    def save(self, mets_url: Union[Path, str], backup_directory: Union[bool, Path, str] = True) -> None:
        self.workspace.save_mets()
        mets_path = Path(self._strip_local(mets_url, disallow_remote=True))
        workspace_directory = mets_path.parent
        if workspace_directory.exists():
            if backup_directory:
                if isinstance(backup_directory, bool):
                    backup_directory = self._derive_backup_directory(workspace_directory)
                shutil.move(workspace_directory, backup_directory)
            else:
                shutil.rmtree(workspace_directory)

        mets_basename = mets_path.name
        workspace_directory.mkdir(parents=True, exist_ok=True)
        self._emit('document_saving', 0, None)

        saved_space = Resolver().workspace_from_url(mets_url=self.workspace.mets_target, mets_basename=mets_basename,
                                                    download=False, clobber_mets=True, dst_dir=workspace_directory)
        saved_files = saved_space.mets.find_files()
        for n, f in enumerate(saved_files):
            f = saved_space.download_file(f)
            self._emit('document_saving', n / len(saved_files), f)

        self._emit('document_saving', 1, None)
        self._emit('document_saved', Document(saved_space, self.emitter))

    @property
    def directory(self) -> Path:
        """
        Get workspace directory as a Path object
        """
        return Path(self.workspace.directory)

    @property
    def mets_filename(self) -> str:
        """
        Gets the mets file name (e.g. "mets.xml")
        """
        return Path(self.workspace.mets_target).name

    @property
    def baseurl_mets(self) -> str:
        """
        Gets the uri of the original mets file name
        """
        return str(self.workspace.baseurl) + '/' + self.mets_filename

    def path(self, other: Union[OcrdFile, Path, str]) -> Path:
        """
        Resolves other relative to current workspace
        """
        if isinstance(other, OcrdFile):
            return self.directory.joinpath(other.local_filename)
        elif isinstance(other, Path):
            return self.directory.joinpath(other)
        elif isinstance(other, str):
            return self.directory.joinpath(other)
        else:
            raise ValueError('Unsupported other of type {}'.format(type(other)))

    @property
    def page_ids(self) -> List[str]:
        """
        List of page_ids in this workspace

        TODO: This is unsorted (or sorted in document order) use @ORDER attribute or keep document order in sync with the correct order

        @return: List[str]
        """
        # noinspection PyTypeChecker
        return cast(List[str], self.workspace.mets.physical_pages)

    @property
    def file_groups(self) -> List[str]:
        """
        List of file_groups in this workspace

        @return: List[str]
        """
        # noinspection PyTypeChecker
        return cast(List[str], self.workspace.mets.file_groups)

    # noinspection PyProtectedMember
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
        distinct_groups: OrderedDict[Tuple[str, str], None] = OrderedDict()
        # noinspection PyProtectedMember
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

    def display_id_range(self, page_id: str, page_qty: int) -> List[str]:
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
        """
        Find the Page object for page_id and filegroup

        If no PAGE-XML is found finds a single image file in the group, PAGE-XML will be populated automatically by page_from_image
        This is modelled after Processor.input_files https://github.com/OCR-D/core/pull/556/
        """
        page_files = self.files_for_page_id(page_id, file_group, MIMETYPE_PAGE)
        if not page_files:
            page_files = self.files_for_page_id(page_id, file_group, mimetype="//image/.*")
            if not page_files:
                log.warning("No PAGE-XML and no image for page '{}' in fileGrp '{}'".format(page_id, file_group))
                return None
            elif len(page_files) > 1:
                log.warning("No PAGE-XML but {} images for page '{}' in fileGrp '{}'".format(len(page_files), page_id, file_group))
                # but keep going and show the first one for now

        pcgts = self.page_for_file(page_files[0])
        page = pcgts.get_Page()
        image, info, exif = self.workspace.image_from_page(page, page_id)
        return Page(page_id, page_files[0], pcgts, image, exif)

    def files_for_page_id(self, page_id: str, file_group: str = DEFAULT_FILE_GROUP, mimetype: str = None) \
            -> List[OcrdFile]:
        with pushd_popd(self.workspace.directory):
            files: List[OcrdFile] = self.workspace.mets.find_files(fileGrp=file_group, pageId=page_id,
                                                                   mimetype=mimetype)
            files = [self.workspace.download_file(file) for file in files]
            return files

    def page_for_file(self, page_file: OcrdFile) -> PcGtsType:
        with pushd_popd(self.workspace.directory):
            return page_from_file(page_file)

    def reorder(self, ordered_page_ids: List[str]) -> None:
        """
        Orders the pages in physSequence according to ordered_page_ids

        """
        old_page_ids = self.page_ids

        if set(old_page_ids) != set(ordered_page_ids):
            raise ValueError('page_ids do not match: missing in mets.xml: {} / missing in order: {}'.format(
                set(ordered_page_ids).difference(set(old_page_ids)),
                set(self.page_ids).difference(set(ordered_page_ids))
            ))

        # noinspection PyProtectedMember
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

        old_to_new = dict(zip(old_page_ids, self.page_ids))
        self.workspace.save_mets()
        self._emit('document_changed', 'reordered', old_to_new)

    def delete_images(self, page_id: str, file_group: str = 'OCR-D-IMG') -> List[OcrdFile]:
        image_files: List[OcrdFile] = list(self.workspace.mets.find_files(pageId=page_id, fileGrp=file_group,
                                                                          local_only=True, mimetype='//image/.+'))

        for image_file in image_files:
            self.workspace.remove_file(image_file, force=True, keep_file=False, page_recursive=True,
                                       page_same_group=True)
        self.workspace.save_mets()
        self._emit('document_changed', 'page_changed', [page_id])
        return image_files

    def delete_page(self, page_id: str) -> None:
        files = self.workspace.mets.find_files(pageId=page_id, local_only=True)
        for file in files:
            self.workspace.remove_file(file, force=False, keep_file=False)
        self.workspace.mets.remove_physical_page(page_id)
        self.workspace.save_mets()
        self._emit('document_changed', 'page_deleted', [page_id])

    def add_image(self, image: ndarray, page_id: str, file_id: str, file_group: str = 'OCR-D-IMG', dpi: int = 300,
                  mimetype: str = 'image/png') -> 'OcrdFile':
        extension = MIME_TO_EXT[mimetype]
        retval, image_array = cv2.imencode(extension, image)
        image_bytes = add_dpi_to_png_buffer(image_array.tostring(), dpi)
        local_filename = Path(file_group, '%s%s' % (file_id, extension))
        url = (Path(self.workspace.directory) / local_filename)
        current_file = self.workspace.add_file(file_group, ID=file_id, mimetype=mimetype, force=True,
                                               content=image_bytes, url=str(url),
                                               local_filename=str(local_filename), pageId=page_id)
        self.empty = False
        self.workspace.save_mets()
        self._emit('document_changed', 'page_added', [page_id])
        return current_file

    def _emit(self, event: str, *args: Any) -> None:
        if self.emitter is not None:
            self.emitter(event, *args)

    @staticmethod
    def _strip_local(mets_url: Union[Path, str], disallow_remote: bool = True) -> str:
        result = urlparse(str(mets_url))
        if result.scheme == 'file' or result.scheme == '':
            mets_url = result.path
        elif disallow_remote:
            raise ValueError('invalid url {}'.format(mets_url))
        return str(mets_url)

    @staticmethod
    def _derive_backup_directory(workspace_directory: Path, now: datetime = None) -> Path:
        now = now or datetime.now()
        return workspace_directory.parent / ('.bak.' + workspace_directory.name + '.' + now.strftime('%Y%m%d-%H%M%S'))
