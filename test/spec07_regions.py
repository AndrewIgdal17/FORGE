"""Sentinel terminal regions for runnable fixtures.

Task 10 stores accepted terminals in the case-study files. Until then,
``setdefault`` fills a path only when the bundled file left it out.
"""

REGION_SENTINELS = {
    "01_project_technical_details.terminals.sending.gea": "CAISO",
    "01_project_technical_details.terminals.sending.egrid_subregion": "AZNM",
    "01_project_technical_details.terminals.sending.state": "AZ",
    "01_project_technical_details.terminals.receiving.gea": "CAISO",
    "01_project_technical_details.terminals.receiving.egrid_subregion": "AZNM",
    "01_project_technical_details.terminals.receiving.state": "AZ",
}
