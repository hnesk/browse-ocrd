from typing import Optional, Dict, Any, Union, List, Iterator, Tuple
from collections import defaultdict
from logging import Logger

from PIL import ImageDraw, Image
from ocrd_models.ocrd_page import PcGtsType, PageType, BorderType, PrintSpaceType, RegionType, TextRegionType, TextLineType, WordType, GlyphType, GraphemeType
from ocrd_utils import coordinates_of_segment, getLogger
from shapely.geometry import Polygon
from shapely.validation import explain_validity

RegionWithCoords = Union[RegionType, TextLineType, WordType, GlyphType, GraphemeType, PrintSpaceType, BorderType]

# pragma pylint: disable=bad-whitespace
CLASSES = {
    '': 'FFFFFF00',
    'Glyph': '2E8B08FF',
    'Word': 'B22222FF',
    'TextLine': '32CD32FF',
    'Border': 'FFFFFFFF',
    'TableRegion': '8B4513FF',
    'AdvertRegion': '4682B4FF',
    'ChemRegion': 'FF8C00FF',
    'MusicRegion': '9400D3FF',
    'MapRegion': '9ACDD2FF',
    'TextRegion': '0000FFFF',
    'TextRegion:paragraph': '0000FFFA',
    'TextRegion:heading': '0000FFF5',
    'TextRegion:caption': '0000FFF0',
    'TextRegion:header': '0000FFEB',
    'TextRegion:footer': '0000FFE6',
    'TextRegion:page-number': '0000FFE1',
    'TextRegion:drop-capital': '0000FFDC',
    'TextRegion:credit': '0000FFD7',
    'TextRegion:floating': '0000FFD2',
    'TextRegion:signature-mark': '0000FFCD',
    'TextRegion:catch-word': '0000FFC8',
    'TextRegion:marginalia': '0000FFC3',
    'TextRegion:footnote': '0000FFBE',
    'TextRegion:footnote-continued': '0000FFB9',
    'TextRegion:endnote': '0000FFB4',
    'TextRegion:TOC-entry': '0000FFAF',
    'TextRegion:list-label': '0000FFA5',
    'TextRegion:other': '0000FFA0',
    'ChartRegion': '800080FF',
    'ChartRegion:bar': '800080FA',
    'ChartRegion:line': '800080F5',
    'ChartRegion:pie': '800080F0',
    'ChartRegion:scatter': '800080EB',
    'ChartRegion:surface': '800080E6',
    'ChartRegion:other': '800080E1',
    'GraphicRegion': '008000FF',
    'GraphicRegion:logo': '008000FA',
    'GraphicRegion:letterhead': '008000F0',
    'GraphicRegion:decoration': '008000EB',
    'GraphicRegion:frame': '008000E6',
    'GraphicRegion:handwritten-annotation': '008000E1',
    'GraphicRegion:stamp': '008000DC',
    'GraphicRegion:signature': '008000D7',
    'GraphicRegion:barcode': '008000D2',
    'GraphicRegion:paper-grow': '008000CD',
    'GraphicRegion:punch-hole': '008000C8',
    'GraphicRegion:other': '008000C3',
    'ImageRegion': '00CED1FF',
    'LineDrawingRegion': 'B8860BFF',
    'MathsRegion': '00BFFFFF',
    'NoiseRegion': 'FF0000FF',
    'SeparatorRegion': 'FF00FFFF',
    'UnknownRegion': '646464FF',
    'CustomRegion': '637C81FF'}


# pragma pylint: enable=bad-whitespace


class Operation:
    def __init__(self, region: RegionWithCoords, fill: str, outline: str):
        self.region = region
        self.fill = fill
        self.outline = outline

    def paint(self, draw: ImageDraw.Draw) -> None:
        pass

    @property
    def depth(self) -> int:
        depth = 0
        r = self.region
        while hasattr(r, 'parent_object_'):
            r = r.parent_object_
            depth += 1
        return depth


class PolygonOperation(Operation):
    def __init__(self, poly: Polygon, region: RegionWithCoords, fill: str, outline: str) -> None:
        super().__init__(region, fill, outline)
        self.poly = poly

    def paint(self, draw: ImageDraw.Draw) -> None:
        xy = list(map(tuple, self.poly.exterior.coords[:-1]))
        draw.polygon(xy, self.fill, self.outline)


class Operations:
    """
    Operations is a depth-sorted List of Operation objects

    Each depth can be plotted on its own image-layer and
    """

    def __init__(self) -> None:
        self.operations: Dict[int, List[Operation]] = defaultdict(list)

    clear = __init__

    def append(self, op: Operation) -> None:
        self.operations[op.depth].append(op)

    def layers(self) -> Iterator[Tuple[int, List[Operation]]]:
        for layer in sorted(self.operations, reverse=True):
            yield layer, self.operations[layer]


class PageXmlRenderer:

    def __init__(self, canvas: Image.Image, coords: Dict[str, Any], page_id: str = '<unknown>',
                 colors: Optional[Dict[str, str]] = None, logger: Logger = None):
        self.canvas = canvas.convert('RGBA')
        self.coords = coords
        self.page_id = page_id
        self.colors: Dict[str, str] = defaultdict(lambda: 'FF0000FF')
        self.colors.update(colors or CLASSES)
        self.logger = logger or getLogger(self.__class__.__name__)
        self.operations = Operations()
        self.direct_composite = False

    def render_all(self, pc_gts: PcGtsType) -> None:
        page: PageType = pc_gts.get_Page()
        self.render_type(page.get_Border())
        for region in page.get_AllRegions(order='reading-order'):
            self.render_type(region)

    def get_canvas(self) -> Image:
        if not self.direct_composite:
            canvas = self.canvas.copy()
            for depth, operations in self.operations.layers():
                layer = Image.new(mode='RGBA', size=canvas.size, color='#FFFFFF00')
                draw = ImageDraw.Draw(layer)
                for operation in operations:
                    operation.paint(draw)
                canvas.alpha_composite(layer)
            self.operations.clear()
            return canvas
        return self.canvas

    def render_text_region(self, text_region: TextRegionType) -> None:
        line: TextLineType
        for line in text_region.get_TextLine():
            self.render_type(line)
            for word in line.get_Word():
                self.render_type(word)

    def render_type(self, region: RegionWithCoords) -> None:
        if not region:
            return
        poly = self.segment_poly(region)
        if poly:
            self.plot_segment(poly, region)
            if isinstance(region, TextRegionType):
                self.render_text_region(region)

    def segment_poly(self, segment: RegionWithCoords) -> Optional[Polygon]:
        """
        Nearly 1:1 copy of ocrd_segment.extract_pages.segment_poly
        @see https://github.com/OCR-D/ocrd_segment/blob/master/ocrd_segment/extract_pages.py#L387
        """
        polygon = coordinates_of_segment(segment, self.canvas, self.coords)
        poly = None
        # validate coordinates
        try:
            poly = Polygon(polygon)
            reason = ''
            if not poly.is_valid:
                reason = explain_validity(poly)
            elif poly.is_empty:
                reason = 'is empty'
            # elif poly.bounds[0] < 0 or poly.bounds[1] < 0:
            #    reason = 'is negative'
            elif poly.length < 4:
                reason = 'has too few points'
        except ValueError as err:
            reason = str(err)
        if reason:
            tag = segment.__class__.__name__.replace('Type', '')
            if hasattr(segment, 'id'):
                tag += ' "%s"' % segment.id
            self.logger.error('Page "%s" %s %s', self.page_id, tag, reason)
            return None
        return poly

    def plot_segment(self, poly: Polygon, region: RegionWithCoords) -> None:
        # Remove 'Type' for lookup
        region_type = region.__class__.__name__[:-4]
        color = self.colors[region_type]

        # draw segment
        op = PolygonOperation(poly, region, '#' + color[:6] + '1E', '#' + color[:6] + '96')
        if self.direct_composite:
            layer = Image.new(mode='RGBA', size=self.canvas.size, color='#FFFFFF00')
            op.paint(ImageDraw.Draw(layer))
            self.canvas.alpha_composite(layer)
        else:
            self.operations.append(op)
