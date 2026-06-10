from __future__ import annotations

import re


def parse_price(value: str) -> int | None:
    cleaned = value.strip().lower().replace("руб.", "").replace("руб", "").replace("₽", "")
    digits = re.sub(r"[\s.,_']", "", cleaned)
    if not digits.isdigit():
        return None
    price = int(digits)
    return price if price > 0 else None
