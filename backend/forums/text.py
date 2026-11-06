"""What a player may write, as pure functions (no Django, no database), like a game's engine.py.

`clean` turns what the browser sent into the text we store and count. `has_link` and `banned_hit`
decide whether it is allowed. Player text is stored and returned as plain text and is never
translated; it is shown only as text (the frontend never renders it as HTML).

Banned words, per language but checked in every language (the language of a post is unknown). An
entry and a post go through the same steps, so they meet in the same form:

1. Unicode NFKC and `casefold()`: case-insensitive for Latin, Cyrillic and Armenian alike
   (`ԱՐՍԵՆԱԼ` and `արսենալ` are the same). Nothing is transliterated.
2. Zero-width and format characters and combining marks are dropped.
3. Look-alike letters are folded to one shape (Cyrillic `а` and Latin `a`, Greek `ο`, Armenian `օ`)
   and `@ $` to letters. Leetspeak digits (`0 1 3 4 5 7`) become letters only inside a word that already has a
   letter in it (`idi0t`, `1xbet`): a number alone (a score, `4-5-5`, `455`) stays a number.
4. The words are compared whole (so "class" never trips "ass"), also when the letters are spaced out
   (`f u c k`, `f.u.c.k`) or stretched (`fuuuck`). An entry marked `inside_words` is also looked for
   inside longer words, for the stems of heavily inflected languages.

Not caught, and said so: a digit used as a letter inside a spaced-out word (`i d 1 o t`: a single digit never
joins a run of single letters, or `4 5 5` would spell "ass"), other creative spellings, a language written in another script
(Armenian in Latin letters) unless that spelling is its own entry, images. The Report button and the
moderators are the backstop.
"""

import re
import unicodedata

CONTROL = {ord(c) for c in map(chr, range(32)) if c not in "\n"} | {0x7F}
INVISIBLE = {ord(c): None for c in "​‌‍‎‏⁠﻿­‪‫‬‭‮"}

# Letters that look like another script's letter, and the symbols @ and $, folded to one shape. Applied to
# the entry and to the post alike, so only the shape has to agree, not the "right" letter.
LOOKALIKES = str.maketrans(
    {
        "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x", "у": "y", "і": "i", "ј": "j",  # Cyrillic
        "α": "a", "ο": "o", "ρ": "p", "ε": "e", "ι": "i",  # Greek
        "օ": "o", "ս": "u", "ո": "n",  # Armenian
        "@": "a", "$": "s",
    }
)
# Leetspeak digits become letters only inside a word that has a letter in it ("idi0t", "1xbet"). A number
# on its own (a score, a formation, "455") stays a number, and a single digit never joins a run of single
# letters, so "4 5 5" can never spell "ass".
LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t"})

# A bare domain: a name, a dot and one of these endings ("site . com" too).
TLDS = (
    "com|net|org|io|ru|am|info|biz|co|me|tv|gg|xyz|app|bet|to|ly|link|click|site|online|top|club|live|news|"
    "uk|de|fr|es|it|eu|us|ua|by|kz|ge|cc|ws|vip|win|pro|shop|store|fun|space|cloud|page|dev"
)
LINK = re.compile(
    rf"(?:\b(?:https?|ftp)\s*:\s*/\s*/)|(?:\bwww\s*\.)|(?:\b[a-z0-9-]{{2,}}\s*\.\s*(?:{TLDS})\b)"
    r"|(?:\S+@\S+\.\w{2,})",  # an email address
    re.IGNORECASE,
)
WORDS = re.compile(r"[^\W_]+")
RUN = re.compile(r"(.)\1{2,}")


def clean(raw):
    """What is stored and counted: NFC, no control or invisible characters, line breaks as \\n, trimmed,
    at most one empty line in a row."""
    text = unicodedata.normalize("NFC", raw).translate(INVISIBLE)
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ")
    text = "".join(char for char in text if ord(char) not in CONTROL)
    text = re.sub(r"[  ]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def has_link(text):
    """A scheme, `www.`, or a bare domain, also with spaces around the dot. Checked on NFKC + casefold."""
    plain = unicodedata.normalize("NFKC", text).casefold().translate(INVISIBLE)
    return bool(LINK.search(plain))


def shape(text):
    """Steps 1-3 without the digits: one shape for look-alikes, no case, no marks, no invisible characters."""
    text = unicodedata.normalize("NFKC", text).casefold().translate(INVISIBLE)
    text = "".join(char for char in unicodedata.normalize("NFD", text) if unicodedata.category(char) != "Mn")
    return text.translate(LOOKALIKES)


def leet(word):
    return word if word.isdigit() else word.translate(LEET)


def key_of(word):
    """An admin entry as the matcher stores it: folded, words joined by single spaces."""
    return " ".join(leet(part) for part in WORDS.findall(shape(word)))


def tokens(text):
    """The words of a post. Runs of single letters ("f u c k", "f.u.c.k") become one word; digits never join them."""
    words, single = [], []
    for word in WORDS.findall(shape(text)):
        if len(word) == 1 and word.isalpha():
            single.append(word)
            continue
        if single:
            words.append("".join(single))
            single = []
        words.append(word)
    if single:
        words.append("".join(single))
    return [leet(word) for word in words]


def variants(words):
    """The words as typed, with long runs shortened to one letter and to two: `fuuuck` -> `fuck`,
    `assss` -> `ass`. A word that is already fine is untouched, so "as" never becomes "ass"."""
    return [
        words,
        [RUN.sub(r"\1", word) for word in words],
        [RUN.sub(r"\1\1", word) for word in words],
    ]


def banned_hit(text, entries):
    """True when the text contains a banned entry. `entries` are (key, inside_words) pairs, keys as key_of()."""
    for words in variants(tokens(text)):
        padded = f" {' '.join(words)} "
        for key, inside in entries:
            if not key:
                continue
            if f" {key} " in padded:
                return True
            if inside and any(key in word for word in words):
                return True
    return False
