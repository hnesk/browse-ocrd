from __future__ import annotations
from typing import List, Optional, Any, Tuple, Dict, Union, cast, Set, TYPE_CHECKING

from PIL.Image import Image
from lxml.etree import ElementBase as Element
from inspect import signature
from deprecated import deprecated

from ocrd import Workspace, OcrdFile, OcrdExif
from ocrd_utils import MIMETYPE_PAGE, getLogger, pushd_popd, VERSION as OCRD_VERSION
from ocrd_models.ocrd_page import PcGtsType, PageType, MetadataType
from ocrd_models.constants import NAMESPACES

if TYPE_CHECKING:
    from ocrd_browser.model import Document

IMAGE_FROM_PAGE_FILENAME_SUPPORT = 'filename' in signature(Workspace.image_from_page).parameters


class Page:
    def __init__(self, document: Document, id_: str, file_group: str):
        self.document = document
        self._id = id_
        self.file_group = file_group
        self._pc_gts: Optional[PcGtsType] = None
        self._images: Optional[List[Image]] = None
        self._image_files: Optional[List[OcrdFile]] = None
        self._page_file: Optional[OcrdFile] = None

    @property
    def images(self) -> List[Image]:
        if self._images is None:
            self._images = [self.document.resolve_image(f) for f in self.image_files]
        return self._images

    @property
    def image_files(self) -> List[OcrdFile]:
        if self._image_files is None:
            self._image_files = self.get_files("//image/.*")
        return self._image_files

    def get_files(self, mimetype: str = MIMETYPE_PAGE) -> List[OcrdFile]:
        return self.document.files_for_page_id(self.id, self.file_group, mimetype=mimetype)

    @property
    def page_file(self) -> OcrdFile:
        if self._page_file is None:
            page_files = self.get_files(MIMETYPE_PAGE)
            if page_files:
                self._page_file = page_files[0]
        return self._page_file

    @property  # type: ignore[misc]
    @deprecated(reason="Makes no sense anymore, what is **the** file of a page? Use get_files() or page_file / image_files instead")
    def file(self) -> Optional[OcrdFile]:
        """
        TODO: Makes no sense anymore, what is **the** file of a page?

        The whole Page class needs to be split in "PageProxy" and PageXmlPage maybe
        @return:  Optional[OcrdFile]
        """
        if self.page_file:
            return self.page_file
        elif self.image_files:
            return next(iter(self.image_files))
        else:
            any_files = self.get_files(mimetype=None)
            if any_files:
                return next(iter(any_files))

        return None

    @property
    def pc_gts(self) -> PcGtsType:
        if self._pc_gts is None:
            if self.page_file:
                self._pc_gts = self.document.page_for_file(self.page_file)
            else:
                image_files = self.image_files
                if len(image_files) > 0:
                    self._pc_gts = self.document.page_for_file(image_files[0])
        return self._pc_gts

    def get_image(self, feature_selector: Union[str, Set[str]] = '', feature_filter: Union[str, Set[str]] = '', filename: str = '') -> Tuple[Image, Dict[str, Any], OcrdExif]:
        log = getLogger('ocrd_browser.model.page.Page.get_image')

        ws: Workspace = self.document.workspace
        kwargs = {
            'transparency': True,
            'feature_selector': feature_selector if isinstance(feature_selector, str) else ','.join(sorted(feature_selector)),
            'feature_filter': feature_filter if isinstance(feature_filter, str) else ','.join(sorted(feature_filter))
        }
        if filename:
            if IMAGE_FROM_PAGE_FILENAME_SUPPORT:
                kwargs['filename'] = filename
            else:
                raise RuntimeError('Parameter filename not supported in ocrd version {}, at least 2.33.0 needed'.format(OCRD_VERSION))

        try:
            with pushd_popd(ws.directory):
                page_image, page_coords, page_image_info = ws.image_from_page(self.page, self.id, **kwargs)
        except Exception as e:
            log.exception(e)
            page_image, page_coords, page_image_info = None, None, None

        return page_image, page_coords, page_image_info

    @property
    def id(self) -> str:
        return self._id

    @property
    def page(self) -> PageType:
        return self.pc_gts.get_Page()

    @property
    def meta(self) -> MetadataType:
        return self.pc_gts.get_Metadata()

    def xpath(self, xpath: str) -> List[Element]:
        page_namespace = {'page': ns for ns in self.xml_root.nsmap.values() if ns.startswith('http://schema.primaresearch.org/PAGE/gts/pagecontent/')}
        return cast(List[Element], self.xml_root.xpath(xpath, namespaces=dict(NAMESPACES, **page_namespace)))

    @property
    def xml_root(self) -> Element:
        if self.pc_gts.gds_elementtree_node_ is None:
            from ocrd_models.ocrd_page_generateds import parsexmlstring_
            from io import StringIO
            sio = StringIO()

            self.pc_gts.export(
                outfile=sio,
                level=0,
                name_='PcGts',
                namespaceprefix_='pc:',
                namespacedef_='xmlns:pc="%s" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="%s %s/pagecontent.xsd"' % (
                    NAMESPACES['page'],
                    NAMESPACES['page'],
                    NAMESPACES['page']
                ))
            self.pc_gts.gds_elementtree_node_ = parsexmlstring_(sio.getvalue())  # pylint: disable=undefined-variable

        return self.pc_gts.gds_elementtree_node_
