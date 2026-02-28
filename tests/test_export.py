"""Tests for Export module."""

import json
import os
import tempfile
import pytest
from sp_api.export import Exporter


class TestExporter:
    """Tests for Exporter."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.exporter = Exporter(output_dir=self.tmpdir)

    def test_to_csv_basic(self):
        """Test basic CSV export."""
        data = [
            {"id": 1, "name": "Product A", "price": 29.99},
            {"id": 2, "name": "Product B", "price": 49.99},
        ]
        path = self.exporter.to_csv(data, "test.csv")
        assert path is not None
        assert os.path.exists(path)
        with open(path) as f:
            content = f.read()
        assert "Product A" in content
        assert "29.99" in content

    def test_to_csv_nested(self):
        """Test CSV export with nested dicts (flattening)."""
        data = [
            {"id": 1, "price": {"amount": 29.99, "currency": "USD"}},
        ]
        path = self.exporter.to_csv(data, "nested.csv")
        with open(path) as f:
            content = f.read()
        assert "price.amount" in content
        assert "29.99" in content

    def test_to_csv_empty(self):
        """Test CSV export with empty data."""
        result = self.exporter.to_csv([], "empty.csv")
        assert result is None

    def test_to_csv_custom_fields(self):
        """Test CSV export with custom field list."""
        data = [{"a": 1, "b": 2, "c": 3}]
        path = self.exporter.to_csv(data, "custom.csv", fields=["a", "c"])
        with open(path) as f:
            content = f.read()
        assert "a" in content
        assert "c" in content

    def test_to_json(self):
        """Test JSON export."""
        data = {"orders": [{"id": "ORD-001"}]}
        path = self.exporter.to_json(data, "test.json")
        assert os.path.exists(path)
        with open(path) as f:
            loaded = json.load(f)
        assert loaded["orders"][0]["id"] == "ORD-001"

    def test_to_jsonl(self):
        """Test JSONL export."""
        data = [
            {"id": 1, "name": "A"},
            {"id": 2, "name": "B"},
        ]
        path = self.exporter.to_jsonl(data, "test.jsonl")
        with open(path) as f:
            lines = f.readlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["id"] == 1

    def test_to_string_csv(self):
        """Test string output in CSV format."""
        data = [{"x": 1, "y": 2}]
        result = self.exporter.to_string(data, fmt="csv")
        assert "x" in result
        assert "1" in result

    def test_to_string_json(self):
        """Test string output in JSON format."""
        data = {"key": "value"}
        result = self.exporter.to_string(data, fmt="json")
        assert '"key"' in result

    def test_export_auto_timestamp(self):
        """Test auto-timestamped export."""
        data = [{"a": 1}]
        path = self.exporter.export(data, prefix="orders", fmt="csv")
        assert "orders_" in path
        assert path.endswith(".csv")

    def test_export_json_format(self):
        """Test export with JSON format."""
        data = {"test": True}
        path = self.exporter.export(data, prefix="data", fmt="json")
        assert path.endswith(".json")

    def test_export_jsonl_format(self):
        """Test export with JSONL format."""
        data = [{"a": 1}, {"a": 2}]
        path = self.exporter.export(data, prefix="stream", fmt="jsonl")
        assert path.endswith(".jsonl")

    def test_export_unknown_format(self):
        """Test export with unknown format raises error."""
        with pytest.raises(ValueError, match="Unknown format"):
            self.exporter.export([], fmt="xml")

    def test_extract_rows_from_dict(self):
        """Test extracting rows from SP-API response format."""
        data = {"payload": {"Orders": [{"id": 1}, {"id": 2}]}}
        rows = Exporter._extract_rows(data)
        assert len(rows) == 2

    def test_extract_rows_from_list(self):
        """Test extracting rows from plain list."""
        rows = Exporter._extract_rows([{"a": 1}, {"a": 2}])
        assert len(rows) == 2

    def test_extract_rows_single_dict(self):
        """Test extracting rows from a single dict."""
        rows = Exporter._extract_rows({"id": 1, "name": "test"})
        assert len(rows) == 1

    def test_flatten_dict(self):
        """Test dict flattening."""
        nested = {"a": 1, "b": {"c": 2, "d": {"e": 3}}}
        flat = Exporter._flatten_dict(nested)
        assert flat["a"] == 1
        assert flat["b.c"] == 2
        assert flat["b.d.e"] == 3

    def test_flatten_dict_with_list(self):
        """Test flattening with list values."""
        data = {"tags": ["red", "blue"], "complex": [{"x": 1}]}
        flat = Exporter._flatten_dict(data)
        assert flat["tags"] == "red; blue"
        assert isinstance(flat["complex"], str)  # JSON encoded

    def test_output_dir_creation(self):
        """Test that output directory is auto-created."""
        path = os.path.join(self.tmpdir, "subdir", "deep")
        exporter = Exporter(output_dir=path)
        assert os.path.isdir(path)
