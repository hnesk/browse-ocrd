from ocrd_models import OcrdFile, OcrdExif
from ocrd_models.ocrd_page_generateds import PcGtsType, PageType, MetadataType
from PIL.Image import Image
from typing import List


class Page:
    def __init__(self, id_: str, file: OcrdFile, pc_gts: PcGtsType, image_files: List[OcrdFile], images: List[Image], exif: OcrdExif):
        self.id: str = id_
        self.file: OcrdFile = file
        self.pc_gts: PcGtsType = pc_gts
        # due to AlternativeImage on all hierarchy levels,
        # a physical page can have multiple images or none;
        # if it has none itself, a single image representing the page
        # is extracted from the original image and the annotation
        # of the top level
        self.image_files: List[OcrdFile] = image_files
        self.images: List[Image] = images
        self.exif: OcrdExif = exif

    @property
    def page(self) -> PageType:
        return self.pc_gts.get_Page()

    @property
    def meta(self) -> MetadataType:
        return self.pc_gts.get_Metadata()
