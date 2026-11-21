import pytest


@pytest.fixture
def valid_label_output() -> dict:
    return {
        "asset_type": "mcp",
        "sector_primary": "S03",
        "field_primary": "S03.1",
        "fields_secondary": ["S03.2"],
        "business_summary": "Lets support teams look up customer records from chat.",
        "developer_summary": "Python MCP server wrapping a CRM REST API; runs locally via stdio.",
        "use_cases": ["Answer ticket questions", "Update contact records"],
        "non_tech_usability": 2,
        "deploy_difficulty": 2,
        "inputs": ["text", "API"],
        "outputs": ["database"],
        "confidence": 0.8,
    }
