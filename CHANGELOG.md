Change Log
==========


## Unreleased

Fixed:

  * Use `chmod`, not `fchmod` to support Windows, #636 ht @b2m

Changed:

  * Record version information in `pg:MetadataItem`, #637

## [0.4.1] - 2020-10-30

Fixed:

* Fix segfault: Dont put scrollable Gtk.Viewports in scrollable Gtk.Sourceviews / Removes self.viewport from View / Fixes #17
* chdir to workspace directory, fixes #19

## [0.4.0] - 2020-10-22

Changed:

* Introduce Zoom #14
* show all derived images per page #14
* add Text view (simple concatenated) #10 
  
Fixed:
*  Support conversion of PIL LA image via cv #5
*  adapt to ocrd>=2.17 logging #6 

## [0.3.0] - 2020-08-13

A lot:
* Found a basic structure 
* Started unittests
* Implement [scanning](https://github.com/hnesk/browse-ocrd-physical-import) as an extension

## [0.1.9] - 2020-08-01

First more or less public release 

<!-- link-labels -->
[0.4.1]: ../../compare/v0.4.0...v0.4.1
[0.4.0]: ../../compare/v0.3.0...v0.4.0
[0.3.0]: ../../compare/v0.1.9...v0.3.0


