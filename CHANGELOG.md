# Change Log

<!-- 
## [Unreleased](../../compare/v0.5.4...master)
-->

## [0.5.4](../../compare/v0.5.3...0.5.4)

Changed: 
 * build via python -m build and setup.cfg

Fixed:
 *  False warning about number of images per grp/page [#51](../../issues/51)
 *  adapt to new import.metadata.entry_points API [#53](../../pull/53), thanks @bertsky
 *  Dockerfile: use local pkg, not PyPI [#56](../../pull/56), thanks @bertsky
 *  AttributeError: 'EntryPoints' object has no attribute 'get' [#57](../../issues/57) 
 *  Document.reorder: invalidate OcrdMets cache before save [#58](../../pull/58), thanks @kba

## [0.5.3](../../compare/v0.5.2...v0.5.3) - 2022-07-19

Breaking: 
 * Make explicit: requires now python>=3.7 (v0.5.1 is the last supported python3.6 version)

Changed:
 * Startup time improved by not using pkg_resources [#48](../../pull/48)  


## [0.5.2](../../compare/v0.5.1...v0.5.2) - 2022-06-10

New Features:
 * Automatically build a docker image at [`hnesk/ocrd_browser`](https://hub.docker.com/r/hnesk/ocrd_browser), thanks @bertsky 

Fixed:
 * PageView: improve reading order and region rendering order #44 [#44](../../issues/44)
 * Use `ocrd_utils.getLogger` instead `logging.getLogger` 

Changed:
 * Performance improvements 
   * use [fastentrypoints](https://github.com/ninjaaron/fast-entry_points)
   * use annotations
   * reduce imports with `if TYPE_CHECKING` 
 * Use [codespell](https://github.com/codespell-project/codespell) in CI
 * Stop supporting python-3.6, start supporting 3.9

## [0.5.1](../../compare/v0.5...v0.5.1) - 2022-05-10

New Features:
 * PageView: add baselines if available  [#34](../../issues/34)
 * PageView: add screenshot button  [#41](../../pull/41), thanks @bertsky
 * PageView: show @conf in tooltip [#39](../../pull/39), thanks @bertsky
 * Text/Xml/Diff view: Allow zooming with CTRL+mousewheel [#33](../../pull/33), thanks @bertsky

Fixed:
 * PageView: component menu not editable with older PAGE-XML Namespaces [#35](../../issues/35)
 * support path names with spaces [#40](../../issues/40)
 * ViewPage: ignore AlternativeImage if not retrievable [#37](../../issues/37)


## [0.5](../../compare/v0.4.3...v0.5) - 2021-11-09

New Features:
* [Added a PageView](../../pull/30) ([#15](../../issues/15) / [#28](../../issues/28)) \
  Shows page image overlaid with [PAGE-XML](https://ocr-d.de/en/spec/page) annotations, similar to PRImA-[PageViewer](https://github.com/PRImA-Research-Lab/prima-page-viewer)
  * Selectable `<Page>` or any `<AlternativeImage>` image as a base   
  * Selectable features as overlay: border, printSpace, region order, regions, lines, words, glyphs, warnings
  * Warnings: Display regions with problematic coordinates in red
  * Tooltip with current coordinates, region, text annotations

* ImageView:
  * zoom keyboard shortcuts `<CTRL>+`/`<CTRL>-`/`<CTRL>0`/`<CTRL>#`/`<CTRL><ALT>#`

Changed:
* Performance / responsiveness improvements 
  * Events get queued 
  * Introduction of `LazyPage` a lazy loading page proxy


## [0.4.3](../../compare/v0.4.2...v0.4.3) - 2021-07-22 

Fixed: 
* require gi >= 3.28 [#26](../../pull/26)

Changed:
* [Using Github actions for CI](https://github.com/hnesk/browse-ocrd/actions/workflows/unittest.yml)
* Get rid of DEFAULT_FILE_GROUP = 'OCR-D-IMG'
* Silence xsd error messages on stderr, when reading files produced by ocrd-cis-align 

New Features:
* Added a Diff-View [#13](../../issues/13) & [#29](../../pull/29)

## [0.4.2](../../compare/v0.4.1...v0.4.2) - 2020-11-12 

Fixed: 

* Catch empty imageFilename case &  don't download remote urls upfront [#25](../../issues/25)  
* Pillow workaround: convert 16-bit images to 8-bit [#23](../../pull/23)
* Don't crash on unhandled mimetype [#18](../../issues/18)
* typing.OrderedDict is not available in python 3.6  [#22](../../issues/22)

New Features

* Views can be resized and split now [#12](../../issues/12) 
* Added Webkit-HTML-View for [dinglehopper](https://github.com/qurator-spk/dinglehopper) [#25](../../pull/25) (partially fixes [#13](../../issues/13))
* Added a button to launch [PageViewer](https://www.primaresearch.org/tools/PAGEViewer) from XmlView [#21](../../pull/21) 


## [0.4.1](../../compare/v0.4.0...v0.4.1) - 2020-10-30

Fixed:

* Fix segfault: Dont put scrollable Gtk.Viewports in scrollable Gtk.Sourceviews / Removes self.viewport from View / Fixes #17
* chdir to workspace directory, fixes #19

## [0.4.0](../../compare/v0.3.0...v0.4.0) - 2020-10-22

Changed:

* Introduce Zoom #14
* show all derived images per page #14
* add Text view (simple concatenated) #10 
  
Fixed:
*  Support conversion of PIL LA image via cv #5
*  adapt to ocrd>=2.17 logging #6 

## [0.3.0](../../compare/v0.1.9...v0.3.0) - 2020-08-13

A lot:
* Found a basic structure 
* Started unittests
* Implement [scanning](https://github.com/hnesk/browse-ocrd-physical-import) as an extension

## [0.1.9] - 2020-08-01

First more or less public release 



