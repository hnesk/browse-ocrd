from __future__ import annotations
from typing import TextIO, Optional, Type, TYPE_CHECKING

import sys
import os

if TYPE_CHECKING:
    from types import TracebackType


class RedirectedStdStreams:
    """
    Temporarily redirects stdout/stderr

    Usage:
    with RedirectStdStreams(stderr=open(os.devnull, 'w')):
        # do something that spams stderr

    """
    def __init__(self, stdout: TextIO = None, stderr: TextIO = None) -> None:
        self._stdout = stdout or sys.stdout
        self._stderr = stderr or sys.stderr

    def __enter__(self) -> None:
        self.old_stdout, self.old_stderr = sys.stdout, sys.stderr
        self.old_stdout.flush()
        self.old_stderr.flush()
        sys.stdout, sys.stderr = self._stdout, self._stderr

    def __exit__(self, t: Optional[Type[BaseException]], e: Optional[BaseException], tb: TracebackType) -> None:
        self._stdout.flush()
        self._stderr.flush()
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr


class SilencedStreams(RedirectedStdStreams):
    """
    Temporarily redirects stdout/stderr to nothing (dev/null)

    Usage:
    with SilencedStream(False, True):
        # do something that spams stderr

    """
    def __init__(self, silence_stdout: bool = True, silence_stderr: bool = True):
        self.silence_stdout = silence_stdout
        self.silence_stderr = silence_stderr
        super().__init__(
            open(os.devnull, 'w') if self.silence_stdout else sys.stdout,
            open(os.devnull, 'w') if self.silence_stderr else sys.stderr
        )

    def __exit__(self, t: Optional[Type[BaseException]], e: Optional[BaseException], tb: TracebackType) -> None:
        super().__exit__(t, e, tb)
        if self.silence_stdout:
            self._stdout.close()
        if self.silence_stderr:
            self._stderr.close()
