"""
Data Pipeline module — ETL framework for automated data extraction.

Provides composable pipelines for extracting SP-API data,
transforming it, and loading into various destinations
(CSV, JSON, SQLite, webhooks).
"""

import csv
import json
import logging
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


class PipelineStep:
    """Base class for pipeline steps."""

    def __init__(self, name=None):
        self.name = name or self.__class__.__name__

    def process(self, data, context=None):
        """Process data and return transformed result."""
        raise NotImplementedError


class ExtractStep(PipelineStep):
    """Extract data from SP-API."""

    def __init__(self, method_name, params=None, name=None):
        super().__init__(name or f"Extract:{method_name}")
        self.method_name = method_name
        self.params = params or {}

    def process(self, data, context=None):
        client = context.get("client") if context else None
        if not client:
            raise ValueError("Pipeline context must include 'client' (SPAPIClient)")

        method = getattr(client, self.method_name, None)
        if not method:
            raise ValueError(f"Client has no method: {self.method_name}")

        result = method(**self.params)
        return result


class TransformStep(PipelineStep):
    """Transform data using a callable."""

    def __init__(self, fn, name=None):
        super().__init__(name or f"Transform:{fn.__name__}")
        self.fn = fn

    def process(self, data, context=None):
        return self.fn(data)


class FilterStep(PipelineStep):
    """Filter records based on a predicate."""

    def __init__(self, predicate, name=None):
        super().__init__(name or "Filter")
        self.predicate = predicate

    def process(self, data, context=None):
        if isinstance(data, list):
            return [item for item in data if self.predicate(item)]
        if isinstance(data, dict) and "payload" in data:
            items = data["payload"]
            if isinstance(items, list):
                data["payload"] = [i for i in items if self.predicate(i)]
        return data


class FlattenStep(PipelineStep):
    """Flatten nested dicts/lists into flat records."""

    def __init__(self, key_path=None, separator=".", name=None):
        super().__init__(name or "Flatten")
        self.key_path = key_path
        self.separator = separator

    def _flatten_dict(self, d, prefix=""):
        items = {}
        for k, v in d.items():
            key = f"{prefix}{self.separator}{k}" if prefix else k
            if isinstance(v, dict):
                items.update(self._flatten_dict(v, key))
            elif isinstance(v, list):
                items[key] = json.dumps(v)
            else:
                items[key] = v
        return items

    def process(self, data, context=None):
        # Extract from nested path if specified
        if self.key_path:
            for key in self.key_path.split(self.separator):
                if isinstance(data, dict):
                    data = data.get(key, data)

        if isinstance(data, list):
            return [
                self._flatten_dict(item) if isinstance(item, dict) else item
                for item in data
            ]
        if isinstance(data, dict):
            return self._flatten_dict(data)
        return data


class AggregateStep(PipelineStep):
    """Aggregate records with grouping and aggregation functions."""

    def __init__(self, group_by, aggregations, name=None):
        """
        Args:
            group_by: Field name to group by
            aggregations: Dict of {output_field: (source_field, agg_fn)}
                         agg_fn: 'sum', 'avg', 'count', 'min', 'max'
        """
        super().__init__(name or f"Aggregate:{group_by}")
        self.group_by = group_by
        self.aggregations = aggregations

    def process(self, data, context=None):
        if not isinstance(data, list):
            return data

        groups = {}
        for item in data:
            key = item.get(self.group_by, "unknown")
            if key not in groups:
                groups[key] = []
            groups[key].append(item)

        results = []
        for key, items in groups.items():
            row = {self.group_by: key, "_count": len(items)}
            for out_field, (src_field, agg_fn) in self.aggregations.items():
                values = [
                    item.get(src_field, 0) for item in items
                    if item.get(src_field) is not None
                ]
                if agg_fn == "sum":
                    row[out_field] = sum(values)
                elif agg_fn == "avg":
                    row[out_field] = sum(values) / len(values) if values else 0
                elif agg_fn == "count":
                    row[out_field] = len(values)
                elif agg_fn == "min":
                    row[out_field] = min(values) if values else None
                elif agg_fn == "max":
                    row[out_field] = max(values) if values else None
            results.append(row)

        return results


class DeduplicateStep(PipelineStep):
    """Remove duplicate records based on a key field."""

    def __init__(self, key_field, name=None):
        super().__init__(name or f"Deduplicate:{key_field}")
        self.key_field = key_field

    def process(self, data, context=None):
        if not isinstance(data, list):
            return data
        seen = set()
        result = []
        for item in data:
            key = item.get(self.key_field)
            if key not in seen:
                seen.add(key)
                result.append(item)
        return result


class EnrichStep(PipelineStep):
    """Enrich records with computed fields."""

    def __init__(self, enrichments, name=None):
        """
        Args:
            enrichments: Dict of {new_field: callable(record) -> value}
        """
        super().__init__(name or "Enrich")
        self.enrichments = enrichments

    def process(self, data, context=None):
        if isinstance(data, list):
            for item in data:
                for field, fn in self.enrichments.items():
                    try:
                        item[field] = fn(item)
                    except Exception:
                        item[field] = None
        elif isinstance(data, dict):
            for field, fn in self.enrichments.items():
                try:
                    data[field] = fn(data)
                except Exception:
                    data[field] = None
        return data


# ── Load Steps ────────────────────────────────────────────

class CSVLoadStep(PipelineStep):
    """Write records to CSV file."""

    def __init__(self, path, append=False, name=None):
        super().__init__(name or f"CSV:{path}")
        self.path = Path(path)
        self.append = append

    def process(self, data, context=None):
        if not isinstance(data, list) or not data:
            return data

        self.path.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if self.append and self.path.exists() else "w"
        write_header = mode == "w" or not self.path.exists()

        fieldnames = list(data[0].keys()) if isinstance(data[0], dict) else None
        if not fieldnames:
            return data

        with open(self.path, mode, newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            if write_header:
                writer.writeheader()
            writer.writerows(data)

        logger.info("Wrote %d records to %s", len(data), self.path)
        return data


class JSONLoadStep(PipelineStep):
    """Write records to JSON/JSONL file."""

    def __init__(self, path, jsonl=False, name=None):
        super().__init__(name or f"JSON:{path}")
        self.path = Path(path)
        self.jsonl = jsonl

    def process(self, data, context=None):
        self.path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.path, "w", encoding="utf-8") as f:
            if self.jsonl and isinstance(data, list):
                for item in data:
                    f.write(json.dumps(item, default=str, ensure_ascii=False) + "\n")
            else:
                json.dump(data, f, default=str, ensure_ascii=False, indent=2)

        logger.info("Wrote data to %s", self.path)
        return data


class SQLiteLoadStep(PipelineStep):
    """Write records to SQLite database."""

    def __init__(self, db_path, table_name, name=None):
        super().__init__(name or f"SQLite:{table_name}")
        self.db_path = str(db_path)
        self.table_name = table_name

    def process(self, data, context=None):
        if not isinstance(data, list) or not data:
            return data

        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        try:
            # Auto-create table from first record
            if isinstance(data[0], dict):
                columns = list(data[0].keys())
                col_defs = ", ".join(f'"{c}" TEXT' for c in columns)
                conn.execute(
                    f'CREATE TABLE IF NOT EXISTS "{self.table_name}" ({col_defs})'
                )

                placeholders = ", ".join("?" for _ in columns)
                col_names = ", ".join(f'"{c}"' for c in columns)
                insert_sql = (
                    f'INSERT INTO "{self.table_name}" ({col_names}) '
                    f"VALUES ({placeholders})"
                )

                rows = [
                    tuple(str(item.get(c, "")) for c in columns)
                    for item in data
                ]
                conn.executemany(insert_sql, rows)
                conn.commit()
                logger.info(
                    "Inserted %d records into %s.%s",
                    len(rows), self.db_path, self.table_name,
                )
        finally:
            conn.close()

        return data


class CallbackLoadStep(PipelineStep):
    """Send data to a callback function (webhook, queue, etc.)."""

    def __init__(self, callback, name=None):
        super().__init__(name or "Callback")
        self.callback = callback

    def process(self, data, context=None):
        self.callback(data, context)
        return data


# ── Pipeline ──────────────────────────────────────────────

class DataPipeline:
    """
    Composable ETL pipeline for SP-API data.

    Usage:
        pipeline = DataPipeline("daily_orders")
        pipeline.extract("get_orders", created_after="2024-01-01")
        pipeline.transform(lambda data: data.get("payload", {}).get("Orders", []))
        pipeline.flatten(".")
        pipeline.filter(lambda order: order.get("OrderStatus") == "Shipped")
        pipeline.enrich({"total_usd": lambda o: float(o.get("OrderTotal.Amount", 0))})
        pipeline.load_csv("output/orders.csv")

        result = pipeline.run(client=my_sp_api_client)
    """

    def __init__(self, name="pipeline"):
        self.name = name
        self.steps: List[PipelineStep] = []
        self._metrics = {
            "start_time": None,
            "end_time": None,
            "steps_completed": 0,
            "records_in": 0,
            "records_out": 0,
            "errors": [],
        }

    def extract(self, method_name, **params):
        """Add an extract step."""
        self.steps.append(ExtractStep(method_name, params))
        return self

    def transform(self, fn, name=None):
        """Add a transform step."""
        self.steps.append(TransformStep(fn, name))
        return self

    def filter(self, predicate, name=None):
        """Add a filter step."""
        self.steps.append(FilterStep(predicate, name))
        return self

    def flatten(self, key_path=None, separator="."):
        """Add a flatten step."""
        self.steps.append(FlattenStep(key_path, separator))
        return self

    def aggregate(self, group_by, aggregations):
        """Add an aggregate step."""
        self.steps.append(AggregateStep(group_by, aggregations))
        return self

    def deduplicate(self, key_field):
        """Add a deduplication step."""
        self.steps.append(DeduplicateStep(key_field))
        return self

    def enrich(self, enrichments):
        """Add an enrichment step."""
        self.steps.append(EnrichStep(enrichments))
        return self

    def load_csv(self, path, append=False):
        """Add a CSV load step."""
        self.steps.append(CSVLoadStep(path, append))
        return self

    def load_json(self, path, jsonl=False):
        """Add a JSON/JSONL load step."""
        self.steps.append(JSONLoadStep(path, jsonl))
        return self

    def load_sqlite(self, db_path, table_name):
        """Add a SQLite load step."""
        self.steps.append(SQLiteLoadStep(db_path, table_name))
        return self

    def load_callback(self, callback):
        """Add a callback load step."""
        self.steps.append(CallbackLoadStep(callback))
        return self

    def add_step(self, step):
        """Add a custom pipeline step."""
        self.steps.append(step)
        return self

    def run(self, client=None, initial_data=None):
        """
        Execute the pipeline.

        Args:
            client: SPAPIClient instance (for extract steps)
            initial_data: Starting data (if no extract step)

        Returns:
            PipelineResult with data and metrics
        """
        self._metrics["start_time"] = datetime.now(timezone.utc)
        context = {"client": client, "pipeline": self.name}

        data = initial_data

        for i, step in enumerate(self.steps):
            try:
                logger.info(
                    "[%s] Step %d/%d: %s",
                    self.name, i + 1, len(self.steps), step.name,
                )
                data = step.process(data, context)
                self._metrics["steps_completed"] = i + 1

                # Track record counts
                if isinstance(data, list):
                    if i == 0:
                        self._metrics["records_in"] = len(data)
                    self._metrics["records_out"] = len(data)
                    logger.debug("  → %d records", len(data))

            except Exception as e:
                logger.error(
                    "[%s] Error in step %s: %s", self.name, step.name, e
                )
                self._metrics["errors"].append({
                    "step": step.name,
                    "step_index": i,
                    "error": str(e),
                })
                raise

        self._metrics["end_time"] = datetime.now(timezone.utc)
        return PipelineResult(data, self._metrics)

    @property
    def metrics(self):
        """Get pipeline execution metrics."""
        return self._metrics.copy()

    def __repr__(self):
        steps_str = " → ".join(s.name for s in self.steps)
        return f"DataPipeline({self.name!r}: {steps_str})"


class PipelineResult:
    """Result of a pipeline execution."""

    def __init__(self, data, metrics):
        self.data = data
        self.metrics = metrics

    @property
    def success(self):
        return not self.metrics.get("errors")

    @property
    def record_count(self):
        if isinstance(self.data, list):
            return len(self.data)
        return 1 if self.data else 0

    @property
    def duration_seconds(self):
        start = self.metrics.get("start_time")
        end = self.metrics.get("end_time")
        if start and end:
            return (end - start).total_seconds()
        return 0

    def to_dict(self):
        return {
            "success": self.success,
            "record_count": self.record_count,
            "duration_seconds": self.duration_seconds,
            "metrics": {
                k: str(v) if isinstance(v, datetime) else v
                for k, v in self.metrics.items()
            },
        }

    def __repr__(self):
        return (
            f"PipelineResult(success={self.success}, "
            f"records={self.record_count}, "
            f"duration={self.duration_seconds:.2f}s)"
        )


# ── Pre-built Pipelines ──────────────────────────────────

def orders_pipeline(output_path="output/orders.csv", days_back=7):
    """Pre-built pipeline for daily order extraction."""
    since = (
        datetime.now(timezone.utc) - timedelta(days=days_back)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    return (
        DataPipeline("daily_orders")
        .extract("get_orders", created_after=since)
        .transform(lambda d: d.get("payload", {}).get("Orders", d.get("Orders", [])))
        .flatten()
        .enrich({
            "extracted_at": lambda _: datetime.now(timezone.utc).isoformat(),
            "total_amount": lambda o: float(o.get("OrderTotal.Amount", 0)),
        })
        .load_csv(output_path)
    )


def inventory_pipeline(output_path="output/inventory.csv"):
    """Pre-built pipeline for inventory snapshot."""
    return (
        DataPipeline("inventory_snapshot")
        .extract("get_inventory_summaries")
        .transform(lambda d: d.get("payload", {}).get("inventorySummaries", []))
        .flatten()
        .enrich({
            "snapshot_at": lambda _: datetime.now(timezone.utc).isoformat(),
            "low_stock": lambda i: int(i.get("totalQuantity", 0)) < 10,
        })
        .load_csv(output_path)
    )


def pricing_pipeline(asins, output_path="output/pricing.csv"):
    """Pre-built pipeline for competitive pricing extraction."""
    return (
        DataPipeline("pricing_scan")
        .transform(lambda _: asins)
        .enrich({
            "scanned_at": lambda _: datetime.now(timezone.utc).isoformat(),
        })
        .load_csv(output_path)
    )
