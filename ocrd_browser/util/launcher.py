from ocrd_models import OcrdFile

from ocrd_browser.model import Document
from ocrd_browser.util.config import _Tool
from subprocess import Popen, DETACHED_PROCESS


class Launcher:

    def __init__(self):
        self.processes = []

    def launch(self, config: _Tool, doc: Document, file: OcrdFile):
        args = [config.executable] + [self._template(arg, file) for arg in config.args]
        print(args)
        #process = Popen(args=args, creationflags=DETACHED_PROCESS)
        #self.processes.append(process)

    def _template(self, arg: str, doc: Document, file: OcrdFile):
        vars = {
            'workspace': {
                'directory': doc.workspace.directory,
                'baseurl': doc.workspace.baseurl,
                'mets_target': doc.workspace.mets_target,
            },
            'file': {
                'absolute_path': doc.path(file),
                'local_filename': file.local_filename,
                'mimetype': file.mimetype,
                'pageId': file.pageId,
                'fileGrp': file.fileGrp,
                'extension': file.extension,
                'basename': file.basename,
                'url': file.url,
                'ID': file.ID,
                'basename_without_extension': file.basename_without_extension
            }
        }
        return arg.format(**vars)
