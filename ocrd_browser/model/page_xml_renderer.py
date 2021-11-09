"""
Page-XML rendering object

This is heavily based on ocrd_segment.extract_pages (https://github.com/OCR-D/ocrd_segment/blob/master/ocrd_segment/extract_pages.py)
"""
from math import sin, cos, radians, inf
from enum import IntFlag
from typing import Optional, Dict, Any, Union, List, Iterator, Tuple, Type, cast
from collections import defaultdict
from logging import Logger

from functools import lru_cache as memoized

from PIL import ImageDraw, Image

from ocrd_models.ocrd_page import PcGtsType, PageType, BorderType, PrintSpaceType, RegionType, TextRegionType, TextLineType, WordType, GlyphType, GraphemeType, ChartRegionType, GraphicRegionType
from ocrd_utils import coordinates_of_segment, getLogger

from shapely.geometry import Polygon, Point
from shapely.validation import explain_validity
from shapely import prepared

RegionWithCoords = Union[RegionType, TextLineType, WordType, GlyphType, GraphemeType, PrintSpaceType, BorderType]
__all__ = ['PageXmlRenderer', 'RegionMap', 'Feature', 'Region']

CLASSES = {
    '': 'FFFFFF00',
    'Glyph': '2E8B08FF',
    'Word': 'B22222FF',
    'TextLine': '32CD32FF',
    'Border': 'FFFFFFFF',
    'PrintSpace': 'CCCCCCFF',
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
    'CustomRegion': '637C81FF'
}


class Feature(IntFlag):
    IMAGE = 1
    BORDER = 2
    PRINT_SPACE = 4
    ORDER = 8
    REGIONS = 16
    LINES = 32
    WORDS = 64
    GLYPHS = 128
    GRAPHEMES = 256
    WARNINGS = 512

    DEFAULT = 1 | 2 | 16 | 32

    def should_render(self, region_ds: RegionWithCoords) -> bool:
        lookup = {
            self.BORDER: BorderType,
            self.PRINT_SPACE: PrintSpaceType,
            self.REGIONS: RegionType,
            self.LINES: TextLineType,
            self.WORDS: WordType,
            self.GLYPHS: GlyphType,
            # self.GRAPHEMES: GraphemeType
        }
        for feature, region_type in lookup.items():
            if feature & self and isinstance(region_ds, region_type):
                return True
        return False


class Region:
    """
    A wrapper around all types of Page-XML regions and their polygon with convenience methods
    """
    def __init__(self, region: RegionWithCoords) -> None:
        self.region = region
        self._poly: Optional[Polygon] = None
        self._prep_poly: Optional[prepared.PreparedGeometry] = None
        self.warnings: List[str] = []

    @property
    def poly(self) -> Polygon:
        return self._poly

    @poly.setter
    def poly(self, poly: Polygon) -> None:
        self._poly = poly
        self._prep_poly = prepared.prep(self._poly)

    def contains(self, p: Point) -> bool:
        return self._prep_poly and cast(bool, self._prep_poly.contains(p))

    @property
    def id(self) -> str:
        if hasattr(self.region, 'id'):
            return str(self.region.id)
        elif hasattr(self.region, 'pcGtsId'):
            return str(self.region.pcGtsId)
        elif hasattr(self.region, 'imageFilename'):
            return str(self.region.imageFilename)
        else:
            return ''

    @property
    def region_type(self) -> str:
        return self.base_type + (':' + self.region_subtype if self.region_subtype else '')

    @property
    def base_type(self) -> str:
        return cast(str, self.region.__class__.__name__[:-4])

    @property
    def region_subtype(self) -> str:
        return cast(str, self.region.get_type()) if isinstance(self.region, (TextRegionType, ChartRegionType, GraphicRegionType)) else ''

    @property
    def text(self) -> str:
        if isinstance(self.region, (TextRegionType, TextLineType, WordType, GlyphType)):
            if self.region.get_TextEquiv() and self.region.get_TextEquiv()[0].Unicode:
                return cast(str, self.region.get_TextEquiv()[0].Unicode)
        return ''

    @property
    def parent(self) -> Optional['Region']:
        return Region(self.region.parent_object_) if hasattr(self.region, 'parent_object_') and self.region.parent_object_ else None

    @memoized(maxsize=1)
    def depth(self) -> int:
        return len(self.breadcrumbs())

    @memoized(maxsize=1)
    def breadcrumbs(self) -> List['Region']:
        """
        Traverses region up to the root (PcGts) element
        """
        breadcrumbs: List[Region] = []
        r = self
        while r:
            breadcrumbs.append(r)
            r = r.parent
        return list(breadcrumbs)

    def __str__(self) -> str:
        return '{:s}{:s}'.format(self.region_type, '#' + self.id)

    def __hash__(self) -> int:
        return id(self.region)

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, self.__class__) and self.region is other.region


class RegionBase:
    def __init__(self) -> None:
        self.children: List['RegionNode'] = []

    def append(self, node: 'RegionNode') -> None:
        self.children.append(node)

    def find_region(self, x: float, y: float, ignore_regions: Optional[List[Type[RegionWithCoords]]] = None) -> Optional[Region]:
        """
        Finds deepest region at x,y
        """
        ignore_regions = ignore_regions if ignore_regions is not None else [BorderType, PrintSpaceType]

        def filter_regions(n: Region) -> bool:
            return type(n.region) not in ignore_regions

        p = Point(x, y)

        regions = list(filter(filter_regions, self.find_regions(p)))
        return regions[-1] if regions else None

    def find_regions(self, p: Point) -> List[Region]:
        regions: List[Region] = []
        for node in self.children:
            if node.region.contains(p):
                regions.append(node.region)
                regions.extend(node.find_regions(p))
        return regions


class RegionNode(RegionBase):
    def __init__(self, region: Region):
        super().__init__()
        self.region = region

    def __str__(self) -> str:
        return '{}'.format(self.region)


class RegionMap(RegionBase):
    """
    Builds a tree of regions based on their Page-XML nesting.
    """
    def __init__(self) -> None:
        super().__init__()
        self.nodes_by_region: Dict[Region, RegionNode] = {}
        self.region_by_id: Dict[str, Region] = {}

    def refetch(self, r: Region) -> Optional[Region]:
        return self.get(r.id) if r else None

    def get(self, id_: str) -> Optional[Region]:
        return self.region_by_id.get(id_, None)

    def append(self, node: RegionNode) -> None:
        """
        appends a RegionNode to the tree
        IMPORTANT: this will only work if the parent node already exists, so the calls have to be in breadth-first or depth-first pre-order order.
        The Operations class will iterate in breadth-first order
        """
        self.nodes_by_region[node.region] = node
        if node.region.id:
            self.region_by_id[node.region.id] = node.region

        if node.region.parent in self.nodes_by_region:
            parent_region = self.nodes_by_region[node.region.parent]
            parent_region.append(node)
        else:
            self.children.append(node)


class Operation:
    def __init__(self, region: Region, fill: str, outline: str):
        self.region = region
        self.fill = fill
        self.outline = outline

    def paint(self, draw: ImageDraw.Draw, regions: RegionMap) -> None:
        pass

    @property
    def depth(self) -> int:
        return self.region.depth()


class PolygonOperation(Operation):

    def paint(self, draw: ImageDraw.Draw, regions: RegionMap) -> None:
        xy = list(map(tuple, self.region.poly.exterior.coords[:-1]))
        draw.polygon(xy, self.fill, self.outline)
        regions.append(RegionNode(self.region))


class Operations:
    """
    Operations is a depth-sorted List of Operation objects

    Each depth can be plotted on its own image-layer and will be blended blended with Image.alpha_composite, so
    Image.alpha_composite will only be called once per layer instead of once per operation
    """

    def __init__(self) -> None:
        self.operations: Dict[int, List[Operation]] = defaultdict(list)

    def append(self, op: Operation) -> None:
        self.operations[op.depth].append(op)

    def layers(self) -> Iterator[Tuple[int, List[Operation]]]:
        for layer in sorted(self.operations, reverse=False):
            yield layer, self.operations[layer]

    def paint(self, canvas: Image.Image) -> Tuple[Image.Image, RegionMap]:
        """
        Paints the operations on canvas and fills the RegionMap accordingly
        """
        regions = RegionMap()
        for depth, operations in self.layers():
            layer = Image.new(mode='RGBA', size=canvas.size, color='#FFFFFF00')
            draw = ImageDraw.Draw(layer)
            for operation in operations:
                operation.paint(draw, regions)
            canvas.alpha_composite(layer)
        self.operations.clear()
        return canvas, regions


class RegionFactory:
    def __init__(self, coords: Dict[str, Any], page_id: str = '<unknown>', logger: Logger = None):
        self.coords = coords
        self.page_id = page_id
        self.logger = logger or getLogger(self.__class__.__module__ + '.' + self.__class__.__name__)

    def create(self, region_ds: RegionWithCoords) -> Optional[Region]:
        if not region_ds:
            return None

        region = Region(region_ds)
        coords = coordinates_of_segment(region_ds, None, self.coords)

        warnings = []

        try:
            poly = Polygon(coords)
        except ValueError as err:
            self.logger.error('Page "%s" @ %s %s', self.page_id, str(region), str(err))
            return None

        if not poly.is_valid:
            warning = explain_validity(poly)
            poly, error = self.make_valid(poly)
            if not poly.is_valid:
                self.logger.error('Page "%s" @ %s %s', self.page_id, str(region), str(warning))
                return None
            else:
                warnings.append('{} fixed with an error of {:.3%}'.format(warning, error))

        if poly.length < 4:
            warnings.append(str('has too few points'))

        if poly.is_empty or not poly.area > 0:
            self.logger.error('Page "%s" @ %s %s', self.page_id, str(region), 'is empty')
            return None

        if poly.bounds[0] < 0 or poly.bounds[1] < 0:
            warnings.append('is negative')

        if warnings:
            self.logger.warning('Page "%s" @ %s %s', self.page_id, str(region), ' | '.join(warnings))

        region.poly = poly
        region.warnings = warnings

        return region

    @staticmethod
    def make_valid(polygon: Polygon) -> Tuple[Polygon, float]:
        """Ensures shapely.geometry.Polygon object is valid by repeated simplification"""
        tolerance = 1
        for split in range(1, len(polygon.exterior.coords) - 1):
            if polygon.is_valid or polygon.simplify(polygon.area).is_valid:
                break
            # simplification may not be possible (at all) due to ordering
            # in that case, try another starting point
            polygon = Polygon(polygon.exterior.coords[-split:] + polygon.exterior.coords[:-split])
        for tolerance in range(1, int(polygon.area)):
            if polygon.is_valid:
                break
            # simplification may require a larger tolerance
            polygon = polygon.simplify(tolerance)

        a = polygon.area
        return polygon, tolerance / a if a > 0 else inf


class PageXmlRenderer:

    def __init__(self, canvas: Image.Image, coords: Dict[str, Any], page_id: str = '<unknown>',
                 features: Optional[Feature] = None, colors: Optional[Dict[str, str]] = None, logger: Logger = None):
        self.features = features or Feature.DEFAULT

        if self.features & Feature.IMAGE:
            self.canvas = canvas.convert('RGBA')
        else:
            self.canvas = Image.new(mode='RGBA', size=canvas.size, color='#FFFFFF00')

        self.region_factory = RegionFactory(coords, page_id, logger)

        self.colors: Dict[str, str] = defaultdict(lambda: 'FF0000FF')
        self.colors.update(colors or CLASSES)

        self.operations = Operations()
        self.order: List[Point] = []

    def render_all(self, pc_gts: PcGtsType) -> None:
        page: PageType = pc_gts.get_Page()
        self.render_type(page.get_PrintSpace())
        self.render_type(page.get_Border())
        for region_ds in page.get_AllRegions(order='reading-order'):
            self.render_type(region_ds)

        if self.features & Feature.ORDER:
            for region_ds in page.get_AllRegions(classes=['Text'], order='reading-order'):
                region = self.region_factory.create(region_ds)
                self.order.append(region.poly.centroid)

    def get_result(self) -> Tuple[Image.Image, RegionMap]:
        canvas, regions = self.operations.paint(self.canvas.copy())
        self.draw_order(canvas)
        return canvas, regions

    def draw_order(self, canvas: Image.Image) -> None:
        if self.order and len(self.order) > 1:
            last_point = None
            draw = ImageDraw.Draw(canvas)
            for p in self.order:
                point = p.coords[0]
                if last_point:
                    self.draw_arrow(draw, last_point, point)  # type: ignore[unreachable]
                last_point = point

            self.order = []

    @staticmethod
    def draw_arrow(draw: ImageDraw.Draw, p0: Tuple[float, float], p1: Tuple[float, float], color: str = '#FF0000FF', arrow_size: float = 30.0, angle_deg: float = 30.0, line_width: int = 3) -> None:
        angle = radians(180.0 - angle_deg)
        c, s = cos(angle), sin(angle)
        d = p1[0] - p0[0], p1[1] - p0[1]
        left = d[0] * c - d[1] * s, d[0] * s + d[1] * c
        right = d[0] * c + d[1] * s, -d[0] * s + d[1] * c
        lf = arrow_size / (d[0] ** 2 + d[1] ** 2) ** 0.5

        draw.line([p0, p1], fill=color, width=line_width)
        draw.ellipse((p1[0] - 5, p1[1] - 5, p1[0] + 5, p1[1] + 5), fill=color)
        draw.line([(p1[0] + lf * left[0], p1[1] + lf * left[1]), p1], fill=color, width=line_width)
        draw.line([(p1[0] + lf * right[0], p1[1] + lf * right[1]), p1], fill=color, width=line_width)

    def render_type(self, region_ds: RegionWithCoords) -> None:
        if self.features.should_render(region_ds):
            region = self.region_factory.create(region_ds)
            if region:
                color = self.colors[region.region_type]
                if self.features & Feature.WARNINGS and region.warnings:
                    op = PolygonOperation(region, '#FF00003E', '#FF000076')
                else:
                    op = PolygonOperation(region, '#' + color[:6] + '1E', '#' + color[:6] + '96')
                self.operations.append(op)

        if isinstance(region_ds, TextRegionType):
            self.render_text_region(region_ds)

    def render_text_region(self, text_region: TextRegionType) -> None:
        line: TextLineType
        word: WordType
        glyph: GlyphType
        for line in text_region.get_TextLine():
            self.render_type(line)
            for word in line.get_Word():
                self.render_type(word)
                for glyph in word.get_Glyph():
                    self.render_type(glyph)
