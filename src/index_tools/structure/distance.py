# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Structural-distance computation for corpus commonality/variation scoring (design brief §10.3).

Pure, dependency-free edit-distance over section-type sequences. ``structural_distance`` returns
a normalised Levenshtein distance in ``[0, 1]`` where ``0`` means the two section-type sequences
are identical and ``1`` means they share no order-preserving structure.
"""

from __future__ import annotations

from collections.abc import Sequence


def _levenshtein(seq_a: Sequence[str], seq_b: Sequence[str]) -> int:
    """Return the token-level Levenshtein (edit) distance between two sequences."""
    if seq_a == seq_b:
        return 0
    len_a, len_b = len(seq_a), len(seq_b)
    if len_a == 0:
        return len_b
    if len_b == 0:
        return len_a
    previous = list(range(len_b + 1))
    for i, token_a in enumerate(seq_a, start=1):
        current = [i]
        for j, token_b in enumerate(seq_b, start=1):
            insert_cost = current[j - 1] + 1
            delete_cost = previous[j] + 1
            substitute_cost = previous[j - 1] + (0 if token_a == token_b else 1)
            current.append(min(insert_cost, delete_cost, substitute_cost))
        previous = current
    return previous[-1]


def structural_distance(seq_a: Sequence[str], seq_b: Sequence[str]) -> float:
    """Return the normalised structural distance between two section-type sequences (§10.3).

    The raw token-level edit distance is divided by the length of the longer sequence so the
    result lands in ``[0.0, 1.0]``: ``0.0`` for identical sequences, ``1.0`` for maximally
    different ones. Two empty sequences are treated as identical (``0.0``).
    """
    # req: FR-009
    list_a = list(seq_a)
    list_b = list(seq_b)
    if not list_a and not list_b:
        return 0.0
    denominator = max(len(list_a), len(list_b))
    if denominator == 0:
        return 0.0
    return round(_levenshtein(list_a, list_b) / denominator, 6)
