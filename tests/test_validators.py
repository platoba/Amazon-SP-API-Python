"""Tests for validators module — ASIN, SKU, EAN, UPC, marketplace, dates, orders."""

import pytest

from sp_api.validators import (
    validate_asin,
    validate_asins,
    validate_sku,
    validate_ean,
    validate_upc,
    validate_marketplace,
    validate_date,
    validate_date_range,
    validate_order_id,
    validate_string,
    validate_positive_int,
    validated,
    _verify_ean_check_digit,
    _verify_upc_check_digit,
)
from sp_api.exceptions import SPAPIValidationError


class TestValidateAsin:
    def test_valid_asin(self):
        assert validate_asin("B09XYZ1234") == "B09XYZ1234"

    def test_valid_asin_lowercase(self):
        assert validate_asin("b09xyz1234") == "B09XYZ1234"

    def test_valid_asin_with_spaces(self):
        assert validate_asin("  B09XYZ1234  ") == "B09XYZ1234"

    def test_invalid_too_short(self):
        with pytest.raises(SPAPIValidationError, match="10 alphanumeric"):
            validate_asin("B09XYZ")

    def test_invalid_too_long(self):
        with pytest.raises(SPAPIValidationError, match="10 alphanumeric"):
            validate_asin("B09XYZ12345678")

    def test_invalid_special_chars(self):
        with pytest.raises(SPAPIValidationError, match="10 alphanumeric"):
            validate_asin("B09-XYZ-12")

    def test_invalid_type(self):
        with pytest.raises(SPAPIValidationError, match="string"):
            validate_asin(12345)

    def test_strict_mode_b0_prefix(self):
        assert validate_asin("B09XYZ1234", strict=True) == "B09XYZ1234"

    def test_strict_mode_isbn(self):
        assert validate_asin("0123456789", strict=True) == "0123456789"

    def test_strict_mode_rejects_random(self):
        with pytest.raises(SPAPIValidationError, match="strict mode"):
            validate_asin("X09XYZ1234", strict=True)


class TestValidateAsins:
    def test_valid_list(self):
        result = validate_asins(["B09XYZ1234", "B09ABC5678"])
        assert len(result) == 2

    def test_deduplication(self):
        result = validate_asins(["B09XYZ1234", "B09XYZ1234", "B09ABC5678"])
        assert len(result) == 2

    def test_empty_list(self):
        with pytest.raises(SPAPIValidationError, match="empty"):
            validate_asins([])

    def test_too_many(self):
        asins = [f"B09XYZ{i:04d}" for i in range(25)]
        with pytest.raises(SPAPIValidationError, match="Too many"):
            validate_asins(asins)

    def test_custom_max(self):
        asins = ["B09XYZ1234", "B09ABC5678", "B09DEF9012"]
        with pytest.raises(SPAPIValidationError):
            validate_asins(asins, max_count=2)


class TestValidateSku:
    def test_valid_sku(self):
        assert validate_sku("MY-PRODUCT-001") == "MY-PRODUCT-001"

    def test_valid_sku_dots(self):
        assert validate_sku("SKU.V2.RED") == "SKU.V2.RED"

    def test_valid_sku_underscore(self):
        assert validate_sku("SKU_VARIANT_01") == "SKU_VARIANT_01"

    def test_empty_sku(self):
        with pytest.raises(SPAPIValidationError, match="empty"):
            validate_sku("")

    def test_too_long(self):
        with pytest.raises(SPAPIValidationError, match="too long"):
            validate_sku("A" * 41)

    def test_invalid_chars(self):
        with pytest.raises(SPAPIValidationError, match="alphanumeric"):
            validate_sku("SKU WITH SPACES")

    def test_invalid_type(self):
        with pytest.raises(SPAPIValidationError, match="string"):
            validate_sku(12345)


class TestValidateEan:
    def test_valid_ean(self):
        # Known valid EAN-13: 4006381333931
        assert validate_ean("4006381333931") == "4006381333931"

    def test_invalid_length(self):
        with pytest.raises(SPAPIValidationError, match="13 digits"):
            validate_ean("12345")

    def test_invalid_check_digit(self):
        with pytest.raises(SPAPIValidationError, match="check digit"):
            validate_ean("4006381333932")  # Wrong last digit

    def test_verify_check_digit(self):
        assert _verify_ean_check_digit("4006381333931")
        assert not _verify_ean_check_digit("4006381333932")


class TestValidateUpc:
    def test_valid_upc(self):
        # Known valid UPC-A: 036000291452
        assert validate_upc("036000291452") == "036000291452"

    def test_invalid_length(self):
        with pytest.raises(SPAPIValidationError, match="12 digits"):
            validate_upc("12345")

    def test_invalid_check_digit(self):
        with pytest.raises(SPAPIValidationError, match="check digit"):
            validate_upc("036000291453")

    def test_verify_check_digit(self):
        assert _verify_upc_check_digit("036000291452")
        assert not _verify_upc_check_digit("036000291453")


class TestValidateMarketplace:
    def test_valid_us(self):
        assert validate_marketplace("US") == "US"

    def test_valid_lowercase(self):
        assert validate_marketplace("de") == "DE"

    def test_gb_alias(self):
        assert validate_marketplace("GB") == "UK"

    def test_invalid_marketplace(self):
        with pytest.raises(SPAPIValidationError, match="Unknown marketplace"):
            validate_marketplace("INVALID")

    def test_invalid_type(self):
        with pytest.raises(SPAPIValidationError, match="string"):
            validate_marketplace(123)


class TestValidateDate:
    def test_valid_date(self):
        assert validate_date("2024-01-15") == "2024-01-15"

    def test_invalid_format(self):
        with pytest.raises(SPAPIValidationError, match="YYYY-MM-DD"):
            validate_date("01/15/2024")

    def test_invalid_date(self):
        with pytest.raises(SPAPIValidationError, match="Invalid date"):
            validate_date("2024-13-01")

    def test_future_date_rejected(self):
        with pytest.raises(SPAPIValidationError, match="Future date"):
            validate_date("2099-01-01")

    def test_future_date_allowed(self):
        result = validate_date("2099-01-01", allow_future=True)
        assert result == "2099-01-01"

    def test_invalid_type(self):
        with pytest.raises(SPAPIValidationError, match="string"):
            validate_date(20240115)


class TestValidateDateRange:
    def test_valid_range(self):
        start, end = validate_date_range("2024-01-01", "2024-06-30")
        assert start == "2024-01-01"
        assert end == "2024-06-30"

    def test_reversed_dates(self):
        with pytest.raises(SPAPIValidationError, match="before"):
            validate_date_range("2024-12-31", "2024-01-01")

    def test_too_wide(self):
        with pytest.raises(SPAPIValidationError, match="too wide"):
            validate_date_range("2020-01-01", "2024-12-31")

    def test_custom_max_days(self):
        with pytest.raises(SPAPIValidationError, match="too wide"):
            validate_date_range("2024-01-01", "2024-02-15", max_days=30)

    def test_no_max_days(self):
        start, end = validate_date_range("2020-01-01", "2024-12-31", max_days=None, allow_future=True)
        assert start == "2020-01-01"


class TestValidateOrderId:
    def test_valid_order(self):
        assert validate_order_id("123-4567890-1234567") == "123-4567890-1234567"

    def test_invalid_format(self):
        with pytest.raises(SPAPIValidationError, match="format"):
            validate_order_id("INVALID-ORDER")

    def test_invalid_type(self):
        with pytest.raises(SPAPIValidationError, match="string"):
            validate_order_id(12345)


class TestValidateString:
    def test_valid(self):
        assert validate_string("hello", "test") == "hello"

    def test_too_short(self):
        with pytest.raises(SPAPIValidationError, match="too short"):
            validate_string("", "test", min_length=1)

    def test_too_long(self):
        with pytest.raises(SPAPIValidationError, match="too long"):
            validate_string("hello world", "test", max_length=5)

    def test_invalid_type(self):
        with pytest.raises(SPAPIValidationError, match="string"):
            validate_string(123, "test")


class TestValidatePositiveInt:
    def test_valid(self):
        assert validate_positive_int(5, "count") == 5

    def test_zero_rejected(self):
        with pytest.raises(SPAPIValidationError, match="positive"):
            validate_positive_int(0, "count")

    def test_negative_rejected(self):
        with pytest.raises(SPAPIValidationError, match="positive"):
            validate_positive_int(-1, "count")

    def test_too_large(self):
        with pytest.raises(SPAPIValidationError, match="too large"):
            validate_positive_int(1000, "count", max_val=100)

    def test_bool_rejected(self):
        with pytest.raises(SPAPIValidationError, match="integer"):
            validate_positive_int(True, "count")


class TestValidatedDecorator:
    def test_validates_asin(self):
        @validated(asin="asin")
        def get_product(asin, marketplace="US"):
            return asin

        result = get_product("b09xyz1234")
        assert result == "B09XYZ1234"

    def test_validates_marketplace(self):
        @validated(marketplace="marketplace")
        def get_product(asin, marketplace="US"):
            return marketplace

        result = get_product("test", marketplace="gb")
        assert result == "UK"

    def test_raises_on_invalid(self):
        @validated(asin="asin")
        def get_product(asin):
            return asin

        with pytest.raises(SPAPIValidationError):
            get_product("INVALID!")

    def test_skips_none_values(self):
        @validated(asin="asin")
        def get_product(asin=None):
            return asin

        assert get_product() is None

    def test_multiple_validators(self):
        @validated(asin="asin", marketplace="marketplace")
        def get_product(asin, marketplace="US"):
            return asin, marketplace

        asin, mp = get_product("b09xyz1234", marketplace="de")
        assert asin == "B09XYZ1234"
        assert mp == "DE"
