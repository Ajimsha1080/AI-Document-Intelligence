import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

ARABIC_INDIC_MAP = {
    '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
    '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9',
    '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
    '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9'
}

def normalize_arabic_digits(text: str) -> str:
    """Normalizes Arabic-Indic and Eastern digits (٠-٩) to standard ASCII digits (0-9)."""
    if not text:
        return ""
    result = []
    for char in text:
        result.append(ARABIC_INDIC_MAP.get(char, char))
    return "".join(result)

def calculate_emirates_id_check_digit(first_14_digits: str) -> int:
    """
    Computes standard check digit for the first 14 digits of a UAE Emirates ID.
    Uses ISO/IEC 7812 Luhn algorithm.
    """
    digits = [int(d) for d in first_14_digits if d.isdigit()]
    if len(digits) != 14:
        raise ValueError(f"Expected 14 digits, got {len(digits)}")

    # Luhn algorithm: double every second digit from the right
    total = 0
    for idx, d in enumerate(reversed(digits)):
        if idx % 2 == 0:
            doubled = d * 2
            total += (doubled - 9) if doubled > 9 else doubled
        else:
            total += d

    return (10 - (total % 10)) % 10

def validate_emirates_id_number(id_str: str) -> Tuple[bool, Optional[str], Optional[int]]:
    """
    Validates UAE Emirates ID format: 784-YYYY-NNNNNNN-C.
    Returns (is_valid, normalized_id, expected_check_digit).
    """
    if not id_str:
        return False, None, None

    normalized = normalize_arabic_digits(id_str)
    # Extract all digits
    digits = re.sub(r"[^\d]", "", normalized)
    if len(digits) != 15:
        return False, None, None

    # Check UAE country code
    if not digits.startswith("784"):
        return False, None, None

    # Check birth year range
    current_year = datetime.now().year
    try:
        birth_year = int(digits[3:7])
        if birth_year < 1900 or birth_year > current_year:
            return False, None, None
    except ValueError:
        return False, None, None

    # Format as 784-YYYY-NNNNNNN-C
    formatted_id = f"{digits[:3]}-{digits[3:7]}-{digits[7:14]}-{digits[14]}"
    expected_check = calculate_emirates_id_check_digit(digits[:14])
    actual_check = int(digits[14])

    is_valid = (expected_check == actual_check)
    return is_valid, formatted_id, expected_check

def parse_date_string(date_str: str) -> Optional[str]:
    """
    Parses various date formats into standard ISO YYYY-MM-DD:
    Supports D/M/YYYY, DD-MM-YYYY, DD.MM.YYYY, YYYY-MM-DD, YYYY/MM/DD, YYYY.MM.DD,
    and Eastern Arabic-Indic digits (٠-٩).
    """
    if not date_str:
        return None
    cleaned = normalize_arabic_digits(str(date_str)).strip()

    # Match YYYY-MM-DD or YYYY/MM/DD or YYYY.MM.DD
    m_year_first = re.search(r"\b(\d{4})[/\-\.](\d{1,2})[/\-\.](\d{1,2})\b", cleaned)
    if m_year_first:
        try:
            year, month, day = int(m_year_first.group(1)), int(m_year_first.group(2)), int(m_year_first.group(3))
            dt = datetime(year=year, month=month, day=day)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    # Match D/M/YYYY, DD-MM-YYYY, DD.MM.YYYY
    m_day_first = re.search(r"\b(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})\b", cleaned)
    if m_day_first:
        try:
            day, month, year = int(m_day_first.group(1)), int(m_day_first.group(2)), int(m_day_first.group(3))
            dt = datetime(year=year, month=month, day=day)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    return None
