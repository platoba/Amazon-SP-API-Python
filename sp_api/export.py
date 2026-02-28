"""
Export utilities — CSV, JSON, and JSONL export for SP-API data.
"""

import csv
import json
import io
import os
import datetime
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class Exporter:
    """
    Export SP-API data to CSV, JSON, or JSONL files.

    Usage:
        from sp_api.export import Exporter

        exporter = Exporter(output_dir="./exports")

        # Export orders to CSV
        orders = api.get_orders()
        exporter.to_csv(orders["payload"]["Orders"], "orders.csv")

        # Export catalog to JSON
        catalog = api.search_catalog("wireless earbuds")
        exporter.to_json(catalog, "catalog.json")

        # Auto-export with timestamp
        exporter.export(data, "inventory", format="csv")
        # → exports/inventory_20260228_120000.csv
    """

    def __init__(self, output_dir="./output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _timestamped_name(self, prefix, ext):
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{ts}.{ext}"

    def to_csv(self, data, filename=None, fields=None, flatten=True):
        """
        Export data to CSV.

        Args:
            data: List of dicts or a dict with a list payload.
            filename: Output filename (auto-generated if None).
            fields: List of column names (auto-detected if None).
            flatten: Flatten nested dicts into dot-notation columns.

        Returns:
            Path to the generated CSV file.
        """
        rows = self._extract_rows(data)
        if not rows:
            logger.warning("No data to export to CSV")
            return None

        if flatten:
            rows = [self._flatten_dict(r) for r in rows]

        if fields is None:
            # Collect all unique keys across all rows
            fields = list(dict.fromkeys(k for row in rows for k in row.keys()))

        filename = filename or self._timestamped_name("export", "csv")
        filepath = self.output_dir / filename

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

        logger.info("Exported %d rows to %s", len(rows), filepath)
        return str(filepath)

    def to_json(self, data, filename=None, indent=2):
        """
        Export data to JSON.

        Args:
            data: Any JSON-serializable data.
            filename: Output filename.
            indent: JSON indentation level.

        Returns:
            Path to the generated JSON file.
        """
        filename = filename or self._timestamped_name("export", "json")
        filepath = self.output_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, default=str, ensure_ascii=False)

        logger.info("Exported to %s", filepath)
        return str(filepath)

    def to_jsonl(self, data, filename=None):
        """
        Export data to JSONL (one JSON object per line).

        Args:
            data: List of dicts.
            filename: Output filename.

        Returns:
            Path to the generated JSONL file.
        """
        rows = self._extract_rows(data)
        filename = filename or self._timestamped_name("export", "jsonl")
        filepath = self.output_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, default=str, ensure_ascii=False) + "\n")

        logger.info("Exported %d records to %s", len(rows), filepath)
        return str(filepath)

    def to_string(self, data, fmt="csv", fields=None):
        """
        Export data to a string (useful for inline display).

        Args:
            data: Data to export.
            fmt: "csv" or "json".
            fields: CSV fields.

        Returns:
            Formatted string.
        """
        if fmt == "json":
            return json.dumps(data, indent=2, default=str, ensure_ascii=False)

        rows = self._extract_rows(data)
        if not rows:
            return ""

        rows = [self._flatten_dict(r) for r in rows]
        if fields is None:
            fields = list(dict.fromkeys(k for row in rows for k in row.keys()))

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue()

    def export(self, data, prefix="export", fmt="csv", **kwargs):
        """
        Auto-export with timestamped filename.

        Args:
            data: Data to export.
            prefix: Filename prefix.
            fmt: "csv", "json", or "jsonl".

        Returns:
            Path to the generated file.
        """
        ext_map = {"csv": "csv", "json": "json", "jsonl": "jsonl"}
        if fmt not in ext_map:
            raise ValueError(f"Unknown format: {fmt}. Use csv, json, or jsonl.")

        filename = self._timestamped_name(prefix, ext_map[fmt])

        if fmt == "csv":
            return self.to_csv(data, filename=filename, **kwargs)
        elif fmt == "json":
            return self.to_json(data, filename=filename, **kwargs)
        elif fmt == "jsonl":
            return self.to_jsonl(data, filename=filename, **kwargs)

    @staticmethod
    def _extract_rows(data):
        """Extract a list of dicts from various response formats."""
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            # Try common SP-API response patterns
            for key in ("payload", "Orders", "Items", "items",
                        "inventorySummaries", "results", "data"):
                if key in data:
                    val = data[key]
                    if isinstance(val, list):
                        return val
                    if isinstance(val, dict):
                        # Nested payload
                        for sub_key in ("Orders", "Items", "inventorySummaries",
                                        "results", "data"):
                            if sub_key in val and isinstance(val[sub_key], list):
                                return val[sub_key]
            # Single record → wrap in list
            return [data]
        return []

    @staticmethod
    def _flatten_dict(d, parent_key="", sep="."):
        """Flatten a nested dict into dot-notation keys."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(Exporter._flatten_dict(v, new_key, sep).items())
            elif isinstance(v, list):
                if all(isinstance(i, (str, int, float, bool)) for i in v):
                    items.append((new_key, "; ".join(str(i) for i in v)))
                else:
                    items.append((new_key, json.dumps(v, default=str)))
            else:
                items.append((new_key, v))
        return dict(items)
