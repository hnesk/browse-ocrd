from tests import TestCase
from ocrd_browser.model.page_xml_renderer import RegionFactory, Region
from ocrd_models.ocrd_page import CoordsType, SeparatorRegionType


class RegionFactoryTestCase(TestCase):

    def setUp(self) -> None:
        identity = {
            'transform': [[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]],
            'angle': 0,
            'features': ',normalized'
        }
        self.factory: RegionFactory = RegionFactory(identity, 'DUMMY_0001', None)

    def test_create(self):
        ds = SeparatorRegionType(id='r6', Coords=CoordsType(points="0,0 0,1 1,1 1,0"))
        try:
            with self.assertLogs('ocrd_browser.model.page_xml_renderer', level='WARNING') as log_watch:
                region = self.factory.create(ds)
                raise ValueError('Dummy instead of assertNoLogs')
        except ValueError:
            pass
        self.assertEqual(len(log_watch.output), 0, '{:d} Warning(s) logged "{:s}'.format(len(log_watch.output), '\n'.join(log_watch.output)))
        self.assertIsInstance(region, Region)
        self.assertGreater(region.poly.area, 0)

    def test_create_with_error(self):
        ds = SeparatorRegionType(id='r6', Coords=CoordsType(points="1,1 1,1 1,1 1,1"))
        with self.assertLogs('ocrd_browser.model.page_xml_renderer', level='ERROR') as log_watch:
            region = self.factory.create(ds)
        self.assertRegex(log_watch.output[0], r'ERROR:ocrd_browser\.model\.page_xml_renderer\.RegionFactory:Page "DUMMY_0001" @ SeparatorRegion#r6 Too few points.+')
        self.assertIsNone(region)

    def test_create_with_warning(self):
        ds = SeparatorRegionType(id='r6', Coords=CoordsType(points="239,1303 508,1303 899,1302 1626,1307 2441,1307 2444,1319 2414,1322 1664,1319 619,1317 235,1317 237,1302 235,1302"))
        with self.assertLogs('ocrd_browser.model.page_xml_renderer', level='WARNING') as log_watch:
            region = self.factory.create(ds)
        self.assertIsNotNone(region)
        self.assertRegex(log_watch.output[0], r'WARNING:ocrd_browser\.model\.page_xml_renderer\.RegionFactory:Page "DUMMY_0001" @ SeparatorRegion#r6 Self-intersection.+')
        self.assertRegex(region.warnings[0], r'Self-intersection.+')

    def test_create_with_warning_negative(self):
        ds = SeparatorRegionType(id='r6', Coords=CoordsType(points="0,0 0,-1 -1,-1 -1,0"))
        with self.assertLogs('ocrd_browser.model.page_xml_renderer', level='WARNING'):
            region = self.factory.create(ds)
        self.assertRegex(region.warnings[0], r'is negative')

    def test_create_with_warning_too_few_points(self):
        ds = SeparatorRegionType(id='r6', Coords=CoordsType(points="0,0 0,1 1,1"))
        with self.assertLogs('ocrd_browser.model.page_xml_renderer', level='WARNING'):
            region = self.factory.create(ds)
        self.assertRegex(region.warnings[0], r'has too few points')
