"""
SP-API Marketplace and endpoint constants.
"""

ENDPOINTS = {
    "NA": "https://sellingpartnerapi-na.amazon.com",
    "EU": "https://sellingpartnerapi-eu.amazon.com",
    "FE": "https://sellingpartnerapi-fe.amazon.com",
}

REGION_MAP = {
    "NA": "us-east-1",
    "EU": "eu-west-1",
    "FE": "us-west-2",
}

MARKETPLACES = {
    "US": ("ATVPDKIKX0DER", "NA"),
    "CA": ("A2EUQ1WTGCTBG2", "NA"),
    "MX": ("A1AM78C64UM0Y8", "NA"),
    "BR": ("A2Q3Y263D00KWC", "NA"),
    "UK": ("A1F83G8C2ARO7P", "EU"),
    "DE": ("A1PA6795UKMFR9", "EU"),
    "FR": ("A13V1IB3VIYZZH", "EU"),
    "IT": ("APJ6JRA9NG5V4", "EU"),
    "ES": ("A1RKKUPIHCS9HS", "EU"),
    "NL": ("A1805IZSGTT6HS", "EU"),
    "SE": ("A2NODRKZP88ZB9", "EU"),
    "PL": ("A1C3SOZRARQ6R3", "EU"),
    "TR": ("A33AVAJ2PDY3EV", "EU"),
    "AE": ("A2VIGQ35RCS4UG", "EU"),
    "SA": ("A17E79C6D8DWNP", "EU"),
    "IN": ("A21TJRUUN4KGV", "EU"),
    "EG": ("ARBP9OOSHTCHU", "EU"),
    "JP": ("A1VC38T7YXB528", "FE"),
    "AU": ("A39IBJ37TRP1C6", "FE"),
    "SG": ("A19VAU5U5O7RUS", "FE"),
}
