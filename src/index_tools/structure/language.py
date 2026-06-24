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

"""Offline Unicode-script language heuristic for the internal extractor (design brief §9.1).

No external dependency: dominant-script detection counts code points in the Latin, Cyrillic,
Arabic, Han (CJK), and Devanagari ranges and maps the dominant script to a primary BCP-47
language code. Latin text is further split into ``fr`` vs ``en`` using a trivial diacritic /
stop-word signal, falling back to ``en`` and to ``und`` (undetermined) when there is no signal.
"""

from __future__ import annotations

import unicodedata

#: Script → primary-language code mapping (dominant-script heuristic, design brief §9.1).
_SCRIPT_LANGUAGE = {
    "cyrillic": "ru",
    "arabic": "ar",
    "han": "zh",
    "devanagari": "hi",
}

#: Trivial French markers used only to split Latin-script text into ``fr`` vs ``en``.
_FRENCH_DIACRITICS = set("àâçéèêëîïôûùüÿœæ")
_FRENCH_STOPWORDS = frozenset(
    {"le", "la", "les", "des", "une", "est", "et", "pour", "avec", "dans", "sur", "ils", "nous", "vous", "cette"}
)


def _script_of(char: str) -> str | None:
    """Classify one character into a coarse script bucket, or ``None`` if not a counted letter."""
    if not char.isalpha():
        return None
    code = ord(char)
    if 0x0400 <= code <= 0x04FF or 0x0500 <= code <= 0x052F:
        return "cyrillic"
    if 0x0600 <= code <= 0x06FF or 0x0750 <= code <= 0x077F:
        return "arabic"
    if 0x0900 <= code <= 0x097F:
        return "devanagari"
    if (
        0x4E00 <= code <= 0x9FFF  # CJK unified ideographs
        or 0x3400 <= code <= 0x4DBF  # CJK extension A
        or 0x3040 <= code <= 0x30FF  # Hiragana + Katakana
    ):
        return "han"
    name = unicodedata.name(char, "")
    if name.startswith("LATIN"):
        return "latin"
    return None


def _latin_language(text: str) -> str:
    """Split Latin-script text into ``fr`` vs ``en`` on a trivial diacritic/stop-word signal."""
    lowered = text.lower()
    if any(ch in _FRENCH_DIACRITICS for ch in lowered):
        return "fr"
    tokens = {token.strip(".,;:!?()[]\"'") for token in lowered.split()}
    if tokens & _FRENCH_STOPWORDS:
        return "fr"
    return "en"


def detect_scripts(text: str) -> list[str]:
    """Return dominant script-language code(s) for ``text`` (design brief §9.1).

    Counts letters per coarse Unicode script bucket and maps the dominant bucket to a primary
    language code. Returns ``["und"]`` when no countable letters are present. The Latin bucket
    is resolved to ``fr``/``en`` via :func:`_latin_language`.
    """
    # req: FR-009
    counts: dict[str, int] = {}
    for char in text or "":
        script = _script_of(char)
        if script is not None:
            counts[script] = counts.get(script, 0) + 1
    if not counts:
        return ["und"]
    dominant = max(counts, key=lambda key: counts[key])
    if dominant == "latin":
        return [_latin_language(text)]
    return [_SCRIPT_LANGUAGE.get(dominant, "und")]
