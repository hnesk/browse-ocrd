import re
from collections import Counter
from typing import List, Tuple, Optional, Counter as CounterType


def weight_match(s: str, preferreds: Optional[List[str]] = None) -> float:
    """
    Weights how good a string matches a list of regular expressions
    """
    weight = 0.0
    if preferreds:
        ln = float(len(preferreds))
        for i, preferred in enumerate(preferreds):
            if re.fullmatch(preferred, s):
                # prefer matches earlier in the list
                weight += (ln - i) / ln
                # break or no break???
    return weight


def best_file_group(file_groups_and_mimetypes: List[Tuple[str, str]], preferred_groups: Optional[List[str]] = None, preferred_mimetypes: Optional[List[str]] = None, cutoff: float = -9999) -> Optional[Tuple[str, str]]:
    file_groups: CounterType[Tuple[str, str]] = Counter()
    for file_group_and_mimetype in file_groups_and_mimetypes:
        file_group, mimetype = file_group_and_mimetype
        file_groups[file_group_and_mimetype] += weight_match(file_group, preferred_groups)  # type: ignore[assignment]
        file_groups[file_group_and_mimetype] += weight_match(mimetype, preferred_mimetypes)  # type: ignore[assignment]
        file_groups[file_group_and_mimetype] -= len(file_group) * 0.0001  # type: ignore[assignment]
    if file_groups:
        [(file_group_and_mimetype, score)] = file_groups.most_common(1)
        if score > cutoff:
            return file_group_and_mimetype
        else:
            return None
    else:
        return None
