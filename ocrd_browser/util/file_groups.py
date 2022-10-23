import re
from collections import Counter
from typing import List, Optional, Counter as CounterType, NamedTuple, cast

from ocrd_models import OcrdFile


class FileGroupHandle(NamedTuple):
    group: str
    mime: str

    @property
    def key(self) -> str:
        return '|'.join(self)

    def match(self, file: OcrdFile) -> bool:
        return cast(bool, file.fileGrp == self.group and file.mimetype == self.mime)

    def __str__(self) -> str:
        return ' - '.join(self)


def weight_match(s: str, preferred: Optional[List[str]] = None) -> float:
    """
    Weights how good a string matches a list of regular expressions
    """
    weight = 0.0
    if preferred:
        ln = float(len(preferred))
        for i, pref in enumerate(preferred):
            if re.fullmatch(pref, s):
                # prefer matches earlier in the list
                weight += (ln - i) / ln
                # break or no break???
    return weight


def best_file_group(file_group_handles: List[FileGroupHandle], preferred_groups: Optional[List[str]] = None, preferred_mimetypes: Optional[List[str]] = None, cutoff: float = -9999) -> Optional[FileGroupHandle]:
    file_groups_counter: CounterType[FileGroupHandle] = Counter()
    for file_group_handle in file_group_handles:
        file_groups_counter[file_group_handle] += weight_match(file_group_handle.group, preferred_groups)  # type: ignore[assignment]
        file_groups_counter[file_group_handle] += weight_match(file_group_handle.mime, preferred_mimetypes)  # type: ignore[assignment]
        file_groups_counter[file_group_handle] -= len(file_group_handle.group) * 0.0001  # type: ignore[assignment]
    if file_groups_counter:
        [(file_group_handle, score)] = file_groups_counter.most_common(1)
        if score > cutoff:
            return file_group_handle
        else:
            return None
    else:
        return None
