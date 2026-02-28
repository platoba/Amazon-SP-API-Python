#!/usr/bin/env python3
"""
SP-API CLI — Command-line interface for Amazon Selling Partner API.

Usage:
    sp-api orders list
    sp-api catalog search "wireless earbuds"
    sp-api inventory list
    sp-api pricing competitive B09XYZ1234
    sp-api reports create inventory
"""

import argparse
import json
import os
import sys
import logging

from sp_api import SPAPI, __version__


def get_client(args):
    """Create SPAPI client from args or env vars."""
    return SPAPI(
        refresh_token=args.refresh_token or os.environ.get("SP_REFRESH_TOKEN", ""),
        client_id=args.client_id or os.environ.get("SP_CLIENT_ID", ""),
        client_secret=args.client_secret or os.environ.get("SP_CLIENT_SECRET", ""),
        marketplace=args.marketplace or os.environ.get("SP_MARKETPLACE", "US"),
    )


def output(data, args):
    """Pretty-print or compact JSON output."""
    indent = None if args.compact else 2
    print(json.dumps(data, indent=indent, ensure_ascii=False, default=str))


# ── Subcommand handlers ──────────────────────────────────

def cmd_orders(args):
    client = get_client(args)
    if args.sub == "list":
        result = client.get_orders(
            created_after=args.after,
            max_results=args.limit,
        )
    elif args.sub == "get":
        result = client.get_order(args.order_id)
    elif args.sub == "items":
        result = client.get_order_items(args.order_id)
    else:
        print("Usage: sp-api orders {list|get|items}", file=sys.stderr)
        return
    output(result, args)


def cmd_catalog(args):
    client = get_client(args)
    if args.sub == "search":
        result = client.search_catalog(
            args.keywords,
            page_size=args.limit,
        )
    elif args.sub == "get":
        result = client.get_catalog_item(args.asin)
    else:
        print("Usage: sp-api catalog {search|get}", file=sys.stderr)
        return
    output(result, args)


def cmd_inventory(args):
    client = get_client(args)
    if args.sub in ("list", "summaries"):
        result = client.get_inventory_summaries()
    elif args.sub == "sku":
        result = client.get_inventory_summary_by_sku(args.sku)
    else:
        print("Usage: sp-api inventory {list|sku}", file=sys.stderr)
        return
    output(result, args)


def cmd_pricing(args):
    client = get_client(args)
    if args.sub == "competitive":
        asins = args.asins.split(",") if args.asins else None
        result = client.get_competitive_pricing(asins=asins)
    elif args.sub == "offers":
        result = client.get_item_offers(args.asin, item_condition=args.condition)
    elif args.sub == "price":
        asins = args.asins.split(",") if args.asins else None
        result = client.get_pricing(asins=asins)
    else:
        print("Usage: sp-api pricing {competitive|offers|price}", file=sys.stderr)
        return
    output(result, args)


def cmd_reports(args):
    client = get_client(args)
    if args.sub == "create":
        result = client.create_report(args.report_type, start_date=args.start, end_date=args.end)
    elif args.sub == "get":
        result = client.get_report(args.report_id)
    elif args.sub == "list":
        result = client.get_reports(max_results=args.limit)
    elif args.sub == "wait":
        result = client.create_and_wait(args.report_type, start_date=args.start, end_date=args.end)
    else:
        print("Usage: sp-api reports {create|get|list|wait}", file=sys.stderr)
        return
    output(result, args)


def cmd_feeds(args):
    client = get_client(args)
    if args.sub == "list":
        result = client.get_feeds(max_results=args.limit)
    elif args.sub == "get":
        result = client.get_feed(args.feed_id)
    elif args.sub == "submit":
        content = sys.stdin.read() if args.file == "-" else open(args.file).read()
        result = client.submit_feed(args.feed_type, content)
    else:
        print("Usage: sp-api feeds {list|get|submit}", file=sys.stderr)
        return
    output(result, args)


def cmd_listings(args):
    client = get_client(args)
    if args.sub == "get":
        result = client.get_listings_item(args.seller_id, args.sku)
    elif args.sub == "delete":
        result = client.delete_listings_item(args.seller_id, args.sku)
    else:
        print("Usage: sp-api listings {get|delete}", file=sys.stderr)
        return
    output(result, args)


def cmd_notifications(args):
    client = get_client(args)
    if args.sub == "destinations":
        result = client.get_destinations()
    elif args.sub == "subscribe":
        result = client.create_subscription(args.notification_type, destination_id=args.destination)
    elif args.sub == "get":
        result = client.get_subscription(args.notification_type)
    else:
        print("Usage: sp-api notifications {destinations|subscribe|get}", file=sys.stderr)
        return
    output(result, args)


def cmd_info(args):
    """Show supported marketplaces and API modules."""
    from sp_api.marketplaces import MARKETPLACES
    info = {
        "version": __version__,
        "marketplaces": sorted(MARKETPLACES.keys()),
        "api_modules": [
            "Catalog Items", "Orders", "Product Pricing", "Reports",
            "Feeds", "FBA Inventory", "Finances", "Listings Items",
            "Fulfillment Outbound (MCF)", "Notifications",
        ],
        "report_shortcuts": list(SPAPI.__mro__[4].REPORT_TYPES.keys()) if hasattr(SPAPI, '__mro__') else [],
    }
    output(info, args)


# ── Main ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="sp-api",
        description="Amazon SP-API CLI — Lightweight command-line client",
    )
    parser.add_argument("-V", "--version", action="version", version=f"sp-api {__version__}")
    parser.add_argument("--refresh-token", default="", help="SP-API refresh token (or SP_REFRESH_TOKEN env)")
    parser.add_argument("--client-id", default="", help="LWA client ID (or SP_CLIENT_ID env)")
    parser.add_argument("--client-secret", default="", help="LWA client secret (or SP_CLIENT_SECRET env)")
    parser.add_argument("-m", "--marketplace", default="", help="Marketplace code (US, UK, DE, JP...)")
    parser.add_argument("--compact", action="store_true", help="Compact JSON output")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")

    sub = parser.add_subparsers(dest="command")

    # orders
    p_orders = sub.add_parser("orders", help="Orders API")
    p_orders.add_argument("sub", choices=["list", "get", "items"])
    p_orders.add_argument("order_id", nargs="?", default=None)
    p_orders.add_argument("--after", default=None, help="CreatedAfter (ISO 8601)")
    p_orders.add_argument("--limit", type=int, default=100)

    # catalog
    p_catalog = sub.add_parser("catalog", help="Catalog Items API")
    p_catalog.add_argument("sub", choices=["search", "get"])
    p_catalog.add_argument("keywords", nargs="?", default="")
    p_catalog.add_argument("--asin", default=None)
    p_catalog.add_argument("--limit", type=int, default=20)

    # inventory
    p_inv = sub.add_parser("inventory", help="FBA Inventory API")
    p_inv.add_argument("sub", choices=["list", "summaries", "sku"])
    p_inv.add_argument("--sku", default=None)

    # pricing
    p_price = sub.add_parser("pricing", help="Product Pricing API")
    p_price.add_argument("sub", choices=["competitive", "offers", "price"])
    p_price.add_argument("asins", nargs="?", default=None, help="Comma-separated ASINs")
    p_price.add_argument("--asin", default=None)
    p_price.add_argument("--condition", default="New")

    # reports
    p_rep = sub.add_parser("reports", help="Reports API")
    p_rep.add_argument("sub", choices=["create", "get", "list", "wait"])
    p_rep.add_argument("report_type", nargs="?", default=None)
    p_rep.add_argument("--report-id", default=None)
    p_rep.add_argument("--start", default=None)
    p_rep.add_argument("--end", default=None)
    p_rep.add_argument("--limit", type=int, default=10)

    # feeds
    p_feeds = sub.add_parser("feeds", help="Feeds API")
    p_feeds.add_argument("sub", choices=["list", "get", "submit"])
    p_feeds.add_argument("--feed-id", default=None)
    p_feeds.add_argument("--feed-type", default=None)
    p_feeds.add_argument("--file", default="-", help="Feed content file (or - for stdin)")
    p_feeds.add_argument("--limit", type=int, default=10)

    # listings
    p_list = sub.add_parser("listings", help="Listings Items API")
    p_list.add_argument("sub", choices=["get", "delete"])
    p_list.add_argument("--seller-id", required=True)
    p_list.add_argument("--sku", required=True)

    # notifications
    p_notif = sub.add_parser("notifications", help="Notifications API")
    p_notif.add_argument("sub", choices=["destinations", "subscribe", "get"])
    p_notif.add_argument("notification_type", nargs="?", default=None)
    p_notif.add_argument("--destination", default=None)

    # info
    sub.add_parser("info", help="Show supported marketplaces and API modules")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(name)s: %(message)s")

    if not args.command:
        parser.print_help()
        sys.exit(1)

    handlers = {
        "orders": cmd_orders,
        "catalog": cmd_catalog,
        "inventory": cmd_inventory,
        "pricing": cmd_pricing,
        "reports": cmd_reports,
        "feeds": cmd_feeds,
        "listings": cmd_listings,
        "notifications": cmd_notifications,
        "info": cmd_info,
    }

    try:
        handlers[args.command](args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
