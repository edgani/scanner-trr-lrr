from __future__ import annotations

from ui.home_page import render_home_page
from ui.active_route_page import render_active_route_page
from ui.opportunity_board_page import render_opportunity_board_page
from ui.us_stocks_page import render_us_stocks_page
from ui.ihsg_page import render_ihsg_page
from ui.forex_page import render_forex_page
from ui.commodities_page import render_commodities_page
from ui.crypto_page import render_crypto_page
from ui.scenario_lab_page import render_scenario_lab_page
from ui.diagnostics_page import render_diagnostics_page


def render_selected_page(page: str, snapshot: dict) -> None:
    routes = {
        "Home": render_home_page,
        "Active Route": render_active_route_page,
        "Opportunity Board": render_opportunity_board_page,
        "US": render_us_stocks_page,
        "IHSG": render_ihsg_page,
        "FX": render_forex_page,
        "Commodities": render_commodities_page,
        "Crypto": render_crypto_page,
        "Scenario Lab": render_scenario_lab_page,
        "Diagnostics": render_diagnostics_page,
        # legacy aliases
        "Dashboard Utama": render_home_page,
        "Cross-Asset": render_active_route_page,
        "US Stocks": render_us_stocks_page,
        "Forex": render_forex_page,
        "Scenarios & What If": render_scenario_lab_page,
    }
    routes[page](snapshot)
