"""Tests for CLI module."""

import pytest
import json
from unittest.mock import patch, MagicMock
from sp_api.cli import main


class TestCLI:
    """Test CLI commands."""

    def test_version(self, capsys):
        with pytest.raises(SystemExit) as exc:
            with patch("sys.argv", ["sp-api", "--version"]):
                main()
        assert exc.value.code == 0
        captured = capsys.readouterr()
        assert "sp-api" in captured.out

    def test_no_command_shows_help(self, capsys):
        with pytest.raises(SystemExit) as exc:
            with patch("sys.argv", ["sp-api"]):
                main()
        assert exc.value.code == 1

    def test_info_command(self, capsys):
        with patch("sys.argv", ["sp-api", "info"]):
            main()
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "marketplaces" in data
        assert "US" in data["marketplaces"]
        assert "api_modules" in data

    @patch("sp_api.cli.SPAPI")
    def test_orders_list(self, mock_spapi, capsys):
        mock_client = MagicMock()
        mock_client.get_orders.return_value = {"payload": {"Orders": []}}
        mock_spapi.return_value = mock_client

        with patch("sys.argv", ["sp-api", "--refresh-token", "t", "--client-id", "c",
                                 "--client-secret", "s", "orders", "list"]):
            main()

        mock_client.get_orders.assert_called_once()
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "payload" in data

    @patch("sp_api.cli.SPAPI")
    def test_catalog_search(self, mock_spapi, capsys):
        mock_client = MagicMock()
        mock_client.search_catalog.return_value = {"items": []}
        mock_spapi.return_value = mock_client

        with patch("sys.argv", ["sp-api", "--refresh-token", "t", "--client-id", "c",
                                 "--client-secret", "s", "catalog", "search", "wireless"]):
            main()

        mock_client.search_catalog.assert_called_once()

    @patch("sp_api.cli.SPAPI")
    def test_pricing_competitive(self, mock_spapi, capsys):
        mock_client = MagicMock()
        mock_client.get_competitive_pricing.return_value = {"payload": []}
        mock_spapi.return_value = mock_client

        with patch("sys.argv", ["sp-api", "--refresh-token", "t", "--client-id", "c",
                                 "--client-secret", "s", "pricing", "competitive", "B09TEST"]):
            main()

        mock_client.get_competitive_pricing.assert_called_once()

    @patch("sp_api.cli.SPAPI")
    def test_compact_output(self, mock_spapi, capsys):
        mock_client = MagicMock()
        mock_client.get_orders.return_value = {"orders": []}
        mock_spapi.return_value = mock_client

        with patch("sys.argv", ["sp-api", "--compact", "--refresh-token", "t",
                                 "--client-id", "c", "--client-secret", "s",
                                 "orders", "list"]):
            main()

        captured = capsys.readouterr()
        # Compact output = single line
        assert "\n" not in captured.out.strip()
