from ocrd_models import OcrdFile, OcrdExif
from ocrd_models.ocrd_page_generateds import PcGtsType, PageType, MetadataType
from PIL.Image import Image


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
