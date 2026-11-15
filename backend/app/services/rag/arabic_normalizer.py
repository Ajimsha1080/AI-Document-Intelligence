import re
import unicodedata

# Arabic Tashkeel (diacritics) regex
TASHKEEL_REGEX = re.compile(r"[\u064B-\u0652\u0653-\u0655\u0670\u06D6-\u06ED]")
# Tatweel (kashida)
TATWEEL_REGEX = re.compile(r"\u0640")

# Arabic-Indic to ASCII digits translation
ARABIC_INDIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

def normalize_arabic_text(text: str) -> str:
    """
    Normalizes Arabic text for layout-aware chunking and lexical/semantic RAG indexing.
    - Strips tashkeel (diacritical marks)
    - Normalizes alef forms (إ, أ, آ, ٱ -> ا)
    - Normalizes taa marbuta (ة -> ه)
    - Normalizes alef maqsoora (ى -> ي)
    - Translates Arabic-Indic digits to Latin digits
    - Strips tatweel (kashida)
    - Collapses multiple whitespace
    """
    if not text:
        return ""

    # Normalize unicode composition
    t = unicodedata.normalize("NFKC", text)

    # Remove tashkeel
    t = TASHKEEL_REGEX.sub("", t)

    # Remove tatweel
    t = TATWEEL_REGEX.sub("", t)

    # Translate Arabic-Indic numbers
    t = t.translate(ARABIC_INDIC_DIGITS)

    # Normalize Alef forms
    t = re.sub(r"[إأآٱ]", "ا", t)

    # Normalize Taa Marbuta
    t = re.sub(r"ة", "ه", t)

    # Normalize Alef Maqsoora
    t = re.sub(r"ى", "ي", t)

    # Normalize whitespace
    t = re.sub(r"\s+", " ", t).strip()

    return t.lower()
