"""
Input validators for Amazon SP-API operations.

Validates ASINs, SKUs, EANs, UPCs, marketplace IDs, date ranges,
and other SP-API parameters before sending requests.

Usage:
    from sp_api.validators import validate_asin, validate_sku, validate_marketplace

    validate_asin("B09XYZ1234")         # OK
    validate_asin("INVALID")            # Raises ValidationError
    validate_marketplace("US")          # OK
    validate_date_range("2024-01-01", "2024-12-31")  # OK

    # Decorator for methods
    @validated(asin="asin", marketplace="marketplace")
    def get_product(asin, marketplace="US"):
        ...
"""

import re
import functools
import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set, Union

from sp_api.exceptions import SPAPIValidationError
from sp_api.marketplaces import MARKETPLACES

logger = logging.getLogger(__name__)


# ── ASIN Validation ──────────────────────────────────────

# Amazon Standard Identification Number: 10 alphanumeric characters
# Starts with B0 for most products, or is a 10-digit ISBN
ASIN_PATTERN = re.compile(r'^[A-Z0-9]{10}$')
ASIN_B0_PATTERN = re.compile(r'^B0[A-Z0-9]{8}$')
ISBN10_PATTERN = re.compile(r'^\d{9}[\dX]$')


def validate_asin(asin: str, strict: bool = False) -> str:
    """
    Validate an Amazon ASIN.

    Args:
        asin: ASIN string to validate
        strict: If True, require B0 prefix or valid ISBN-10

    Returns:
        Cleaned ASIN string (uppercased, stripped)

    Raises:
        SPAPIValidationError: If ASIN is invalid
    """
    if not isinstance(asin, str):
        raise SPAPIValidationError(f"ASIN must be a string, got {type(asin).__name__}")

    asin = asin.strip().upper()

    if not ASIN_PATTERN.match(asin):
        raise SPAPIValidationError(
            f"Invalid ASIN '{asin}': must be exactly 10 alphanumeric characters"
        )

    if strict:
        if not (ASIN_B0_PATTERN.match(asin) or ISBN10_PATTERN.match(asin)):
            raise SPAPIValidationError(
                f"ASIN '{asin}' doesn't match B0* or ISBN-10 pattern (strict mode)"
            )

    return asin


def validate_asins(asins: List[str], max_count: int = 20, strict: bool = False) -> List[str]:
    """
    Validate a list of ASINs.

    Args:
        asins: List of ASINs
        max_count: Maximum allowed ASINs (SP-API typically limits to 20)
        strict: If True, require B0 prefix or valid ISBN-10

    Returns:
        List of cleaned ASINs (deduplicated)
    """
    if not asins:
        raise SPAPIValidationError("ASIN list cannot be empty")
    if len(asins) > max_count:
        raise SPAPIValidationError(f"Too many ASINs: {len(asins)} > {max_count}")

    validated = []
    seen = set()
    for a in asins:
        clean = validate_asin(a, strict=strict)
        if clean not in seen:
            validated.append(clean)
            seen.add(clean)

    return validated


# ── SKU Validation ───────────────────────────────────────

SKU_MAX_LENGTH = 40
SKU_PATTERN = re.compile(r'^[A-Za-z0-9\-_\.]+$')


def validate_sku(sku: str) -> str:
    """
    Validate a Seller SKU.

    Amazon SKUs: 1-40 chars, alphanumeric + hyphens/underscores/dots.
    """
    if not isinstance(sku, str):
        raise SPAPIValidationError(f"SKU must be a string, got {type(sku).__name__}")

    sku = sku.strip()
    if not sku:
        raise SPAPIValidationError("SKU cannot be empty")
    if len(sku) > SKU_MAX_LENGTH:
        raise SPAPIValidationError(f"SKU too long: {len(sku)} > {SKU_MAX_LENGTH}")
    if not SKU_PATTERN.match(sku):
        raise SPAPIValidationError(
            f"Invalid SKU '{sku}': only alphanumeric, hyphens, underscores, dots allowed"
        )

    return sku


# ── Barcode Validation ───────────────────────────────────

def validate_ean(ean: str) -> str:
    """Validate EAN-13 barcode with check digit."""
    ean = ean.strip()
    if not re.match(r'^\d{13}$', ean):
        raise SPAPIValidationError(f"Invalid EAN-13: must be exactly 13 digits, got '{ean}'")
    if not _verify_ean_check_digit(ean):
        raise SPAPIValidationError(f"Invalid EAN-13 check digit: '{ean}'")
    return ean


def validate_upc(upc: str) -> str:
    """Validate UPC-A barcode with check digit."""
    upc = upc.strip()
    if not re.match(r'^\d{12}$', upc):
        raise SPAPIValidationError(f"Invalid UPC-A: must be exactly 12 digits, got '{upc}'")
    if not _verify_upc_check_digit(upc):
        raise SPAPIValidationError(f"Invalid UPC-A check digit: '{upc}'")
    return upc


def _verify_ean_check_digit(ean: str) -> bool:
    """Verify EAN-13 check digit."""
    digits = [int(d) for d in ean]
    total = sum(d * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits[:12]))
    check = (10 - (total % 10)) % 10
    return check == digits[12]


def _verify_upc_check_digit(upc: str) -> bool:
    """Verify UPC-A check digit."""
    digits = [int(d) for d in upc]
    total = sum(d * (3 if i % 2 == 0 else 1) for i, d in enumerate(digits[:11]))
    check = (10 - (total % 10)) % 10
    return check == digits[11]


# ── Marketplace Validation ───────────────────────────────

VALID_MARKETPLACES = set(MARKETPLACES.keys()) if MARKETPLACES else {
    "US", "CA", "MX", "BR", "UK", "DE", "FR", "IT", "ES", "NL",
    "SE", "PL", "TR", "EG", "SA", "AE", "IN", "JP", "AU", "SG",
}


def validate_marketplace(marketplace: str) -> str:
    """
    Validate marketplace code.

    Returns:
        Uppercased marketplace code
    """
    if not isinstance(marketplace, str):
        raise SPAPIValidationError(f"Marketplace must be a string, got {type(marketplace).__name__}")

    marketplace = marketplace.strip().upper()
    if marketplace == "GB":
        marketplace = "UK"  # Common alias

    if marketplace not in VALID_MARKETPLACES:
        raise SPAPIValidationError(
            f"Unknown marketplace '{marketplace}'. "
            f"Valid: {', '.join(sorted(VALID_MARKETPLACES))}"
        )
    return marketplace


# ── Date Validation ──────────────────────────────────────

ISO_DATE_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}$')
ISO_DATETIME_PATTERN = re.compile(
    r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?$'
)


def validate_date(date_str: str, allow_future: bool = False) -> str:
    """
    Validate ISO 8601 date string.

    Args:
        date_str: Date in YYYY-MM-DD format
        allow_future: Whether to allow future dates

    Returns:
        Validated date string
    """
    if not isinstance(date_str, str):
        raise SPAPIValidationError(f"Date must be a string, got {type(date_str).__name__}")

    date_str = date_str.strip()
    if not ISO_DATE_PATTERN.match(date_str):
        raise SPAPIValidationError(
            f"Invalid date format '{date_str}': expected YYYY-MM-DD"
        )

    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError as e:
        raise SPAPIValidationError(f"Invalid date '{date_str}': {e}")

    if not allow_future and dt.date() > datetime.now().date():
        raise SPAPIValidationError(f"Future date not allowed: '{date_str}'")

    return date_str


def validate_date_range(
    start: str,
    end: str,
    max_days: Optional[int] = 365,
    allow_future: bool = False,
) -> tuple:
    """
    Validate a date range.

    Returns:
        Tuple of (start_date, end_date) strings
    """
    start = validate_date(start, allow_future=allow_future)
    end = validate_date(end, allow_future=allow_future)

    start_dt = datetime.strptime(start, "%Y-%m-%d")
    end_dt = datetime.strptime(end, "%Y-%m-%d")

    if start_dt > end_dt:
        raise SPAPIValidationError(
            f"Start date ({start}) must be before end date ({end})"
        )

    if max_days:
        delta = (end_dt - start_dt).days
        if delta > max_days:
            raise SPAPIValidationError(
                f"Date range too wide: {delta} days > {max_days} max"
            )

    return start, end


# ── Order ID Validation ──────────────────────────────────

ORDER_ID_PATTERN = re.compile(r'^\d{3}-\d{7}-\d{7}$')


def validate_order_id(order_id: str) -> str:
    """Validate Amazon Order ID format (XXX-XXXXXXX-XXXXXXX)."""
    if not isinstance(order_id, str):
        raise SPAPIValidationError(f"Order ID must be a string, got {type(order_id).__name__}")

    order_id = order_id.strip()
    if not ORDER_ID_PATTERN.match(order_id):
        raise SPAPIValidationError(
            f"Invalid order ID '{order_id}': expected format XXX-XXXXXXX-XXXXXXX"
        )
    return order_id


# ── Generic Validators ───────────────────────────────────

def validate_string(
    value: Any,
    name: str = "value",
    min_length: int = 1,
    max_length: int = 500,
    pattern: Optional[re.Pattern] = None,
) -> str:
    """Generic string validator."""
    if not isinstance(value, str):
        raise SPAPIValidationError(f"{name} must be a string, got {type(value).__name__}")

    value = value.strip()
    if len(value) < min_length:
        raise SPAPIValidationError(f"{name} too short: {len(value)} < {min_length}")
    if len(value) > max_length:
        raise SPAPIValidationError(f"{name} too long: {len(value)} > {max_length}")
    if pattern and not pattern.match(value):
        raise SPAPIValidationError(f"{name} doesn't match expected pattern")

    return value


def validate_positive_int(value: Any, name: str = "value", max_val: Optional[int] = None) -> int:
    """Validate positive integer."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise SPAPIValidationError(f"{name} must be an integer, got {type(value).__name__}")
    if value < 1:
        raise SPAPIValidationError(f"{name} must be positive, got {value}")
    if max_val and value > max_val:
        raise SPAPIValidationError(f"{name} too large: {value} > {max_val}")
    return value


# ── Decorator ────────────────────────────────────────────

VALIDATOR_MAP: Dict[str, Callable] = {
    "asin": validate_asin,
    "sku": validate_sku,
    "marketplace": validate_marketplace,
    "date": validate_date,
    "order_id": validate_order_id,
    "ean": validate_ean,
    "upc": validate_upc,
}


def validated(**param_validators: str):
    """
    Decorator that validates function parameters.

    Usage:
        @validated(asin="asin", marketplace="marketplace")
        def get_product(asin, marketplace="US"):
            ...

    Args:
        **param_validators: Mapping of param_name → validator_name
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import inspect
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()

            for param_name, validator_name in param_validators.items():
                if param_name in bound.arguments:
                    value = bound.arguments[param_name]
                    if value is not None:
                        validator = VALIDATOR_MAP.get(validator_name)
                        if validator:
                            bound.arguments[param_name] = validator(value)

            return func(*bound.args, **bound.kwargs)
        return wrapper
    return decorator
