from pathlib import Path
from tempfile import TemporaryDirectory

from tests import TestCase, ASSETS_PATH
from ocrd_browser.model import Document, Page
from datetime import datetime


# TODO: Later: from tests.assets import Assets, copy_of_directory

class DocumentTestCase(TestCase):

    def setUp(self):
        self.path = ASSETS_PATH / 'kant_aufklaerung_1784/data/mets.xml'

    def test_get_page_ids(self):
        doc = Document.load(self.path)
        self.assertEqual(['PHYS_0017', 'PHYS_0020'], doc.page_ids)

    def test_path_string(self):
        doc = Document.load(self.path)
        self.assertEqual(ASSETS_PATH / 'kant_aufklaerung_1784/data/lala.xml', doc.path('lala.xml'))

    def test_path_path(self):
        doc = Document.load(self.path)
        self.assertEqual(ASSETS_PATH / 'kant_aufklaerung_1784/data/OCR-D-DIR/lala.xml',
                         doc.path(Path('OCR-D-DIR/lala.xml')))

    def test_path_ocrd_file(self):
        doc = Document.load(self.path)
        image_file = doc.workspace.mets.find_files(pageId='PHYS_0017', fileGrp='OCR-D-IMG')[0]
        self.assertEqual(ASSETS_PATH / 'kant_aufklaerung_1784/data/OCR-D-IMG/INPUT_0017.tif', doc.path(image_file))

    def test_reorder(self):
        doc = Document.clone(self.path)
        doc.reorder(['PHYS_0020', 'PHYS_0017'])
        self.assertEqual(['PHYS_0020', 'PHYS_0017'], doc.page_ids)

    def test_reorder_with_wrong_ids_raises_value_error(self):
        doc = Document.clone(self.path)
        with self.assertRaises(ValueError) as context:
            doc.reorder(['PHYS_0021', 'PHYS_0017'])

        self.assertIn('page_ids do not match', str(context.exception))

    def test_clone(self):
        doc = Document.clone(self.path)
        self.assertIn('browse-ocrd-clone-', doc.workspace.directory)
        self.assertEqual(str(self.path), doc.baseurl_mets)

        original_files = self.path.parent.rglob('*.*')
        cloned_files = Path(doc.workspace.directory).rglob('*.*')
        for original, cloned in zip(sorted(original_files), sorted(cloned_files)):
            self.assertEqual(original.read_bytes(), cloned.read_bytes())

    def test_save(self):
        doc = Document.clone(self.path)
        with TemporaryDirectory(prefix='browse-ocrd-tests') as directory:
            saved_mets = directory + '/mets.xml'
            doc.save(saved_mets)
            saved = Document.load(saved_mets)
            self.assertEqual(doc.file_groups, saved.file_groups)
            self.assertEqual(doc.page_ids, saved.page_ids)
            self.assertEqual(doc.workspace.mets.unique_identifier, saved.workspace.mets.unique_identifier)

            for page_id in doc.page_ids:
                for file_group, mime in doc.file_groups_and_mimetypes:
                    original_file = doc.files_for_page_id(page_id, file_group, mime)[0]
                    saved_file = saved.files_for_page_id(page_id, file_group, mime)[0]
                    self.assertEqual(original_file, saved_file)

    def test_derive_backup_directory(self):
        self.assertEqual(
            Path('/home/jk/.bak.important_project.20200813-184321'),
            Document._derive_backup_directory(Path('/home/jk/important_project'), datetime(2020, 8, 13, 18, 43, 21))
        )

    def test_page_for_id_with_no_images_for_page_and_fileGrp(self):
        """
        Issue #4: list index out of range on non-XML fileGrp

        https://github.com/hnesk/browse-ocrd/issues/4
        """
        doc = Document.load(ASSETS_PATH / 'kant_aufklaerung_1784-complex/data/mets.xml')
        with self.assertLogs('ocrd_browser.model.document', level='WARNING') as log_watch:
            page = doc.page_for_id('PHYS_0020', 'OCR-D-IMG-CLIP')
        self.assertIsNone(page)
        self.assertEqual(1, len(log_watch.records))
        self.assertEqual("No PAGE-XML and no image for page 'PHYS_0020' in fileGrp 'OCR-D-IMG-CLIP'",
                         log_watch.records[0].msg)

    def test_page_for_id_with_nothing_for_page_and_fileGrp(self):
        """
        Issue #4 again: This time for missing PAGE-XMLs

        https://github.com/hnesk/browse-ocrd/issues/4
        """
        doc = Document.load(ASSETS_PATH / '../bad/workspaces/kant_aufklaerung_1784_missing_xml/mets.xml')
        with self.assertLogs('ocrd_browser.model.document', level='WARNING') as log_watch:
            page = doc.page_for_id('PHYS_0020', 'OCR-D-GT-PAGE')
        self.assertIsNone(page)
        self.assertEqual(1, len(log_watch.records))
        self.assertEqual("No PAGE-XML and no image for page 'PHYS_0020' in fileGrp 'OCR-D-GT-PAGE'",
                         log_watch.records[0].msg)


    def test_page_for_id_with_multiple_images_for_page_and_fileGrp(self):
        """
        returns first image and warns
        """
        doc = Document.load(ASSETS_PATH / 'kant_aufklaerung_1784-complex/data/mets.xml')
        with self.assertLogs('ocrd_browser.model.document', level='WARNING') as log_watch:
            page = doc.page_for_id('PHYS_0017', 'OCR-D-IMG-CLIP')
        self.assertIsInstance(page, Page)
        self.assertEqual(1, len(log_watch.records))
        self.assertEqual("No PAGE-XML but 2 images for page 'PHYS_0017' in fileGrp 'OCR-D-IMG-CLIP'",
                         log_watch.records[0].msg)
