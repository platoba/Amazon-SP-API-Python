"""
Reports API module — SP-API Reports 2021-06-30.
"""

import time
import logging
from sp_api.base import BaseAPI
from sp_api.exceptions import SPAPIError

logger = logging.getLogger(__name__)


class ReportsAPI(BaseAPI):
    """Amazon SP-API Reports endpoints."""

    REPORTS_VERSION = "2021-06-30"

    # Common report types
    REPORT_TYPES = {
        "inventory": "GET_FBA_MYI_UNSUPPRESSED_INVENTORY_DATA",
        "all_orders": "GET_FLAT_FILE_ALL_ORDERS_DATA_BY_ORDER_DATE_GENERAL",
        "active_listings": "GET_MERCHANT_LISTINGS_DATA",
        "cancelled_listings": "GET_MERCHANT_CANCELLED_LISTINGS_DATA",
        "fba_shipments": "GET_AMAZON_FULFILLED_SHIPMENTS_DATA_GENERAL",
        "returns": "GET_FBA_FULFILLMENT_CUSTOMER_RETURNS_DATA",
        "performance": "GET_SELLER_FEEDBACK_DATA",
        "brand_analytics": "GET_BRAND_ANALYTICS_SEARCH_TERMS_REPORT",
    }

    def create_report(self, report_type, start_date=None, end_date=None, **kwargs):
        """
        Request a new report.

        Args:
            report_type: SP-API report type string or shortcut key from REPORT_TYPES.
            start_date: ISO 8601 start datetime.
            end_date: ISO 8601 end datetime.
        """
        resolved_type = self.REPORT_TYPES.get(report_type, report_type)
        body = {
            "reportType": resolved_type,
            "marketplaceIds": [self.marketplace_id],
        }
        if start_date:
            body["dataStartTime"] = start_date
        if end_date:
            body["dataEndTime"] = end_date
        body.update(kwargs)
        return self.post(f"/reports/{self.REPORTS_VERSION}/reports", body)

    def get_report(self, report_id):
        """Get report status/metadata."""
        return self.get(f"/reports/{self.REPORTS_VERSION}/reports/{report_id}")

    def get_reports(self, report_types=None, processing_statuses=None,
                    max_results=10, next_token=None, **kwargs):
        """List reports with optional filters."""
        params = {}
        if report_types:
            params["reportTypes"] = ",".join(report_types) if isinstance(report_types, list) else report_types
        if processing_statuses:
            params["processingStatuses"] = ",".join(processing_statuses)
        if max_results:
            params["pageSize"] = max_results
        if next_token:
            params["nextToken"] = next_token
        params.update(kwargs)
        return self.get(f"/reports/{self.REPORTS_VERSION}/reports", params)

    def get_report_document(self, document_id):
        """Get report document download URL."""
        return self.get(f"/reports/{self.REPORTS_VERSION}/documents/{document_id}")

    def cancel_report(self, report_id):
        """Cancel a pending report."""
        return self.delete(f"/reports/{self.REPORTS_VERSION}/reports/{report_id}")

    def create_and_wait(self, report_type, start_date=None, end_date=None,
                        poll_interval=15, max_wait=600, **kwargs):
        """
        Create a report and poll until complete.

        Args:
            report_type: Report type string or shortcut.
            poll_interval: Seconds between status checks.
            max_wait: Maximum seconds to wait.

        Returns:
            Report document info dict.

        Raises:
            SPAPIError: If report fails or times out.
        """
        result = self.create_report(report_type, start_date, end_date, **kwargs)
        report_id = result.get("reportId")
        if not report_id:
            raise SPAPIError(f"No reportId in response: {result}")

        logger.info("Report %s created, polling...", report_id)
        start = time.time()

        while time.time() - start < max_wait:
            status_resp = self.get_report(report_id)
            status = status_resp.get("processingStatus", "")

            if status == "DONE":
                doc_id = status_resp.get("reportDocumentId")
                if doc_id:
                    return self.get_report_document(doc_id)
                return status_resp

            if status in ("CANCELLED", "FATAL"):
                raise SPAPIError(f"Report {report_id} failed with status: {status}")

            logger.debug("Report %s status: %s", report_id, status)
            time.sleep(poll_interval)

        raise SPAPIError(f"Report {report_id} timed out after {max_wait}s")
