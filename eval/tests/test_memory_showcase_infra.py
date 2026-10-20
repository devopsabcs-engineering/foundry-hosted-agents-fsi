"""The opt-in memory prerequisite must not rewrite any baseline resource."""

import json
from pathlib import Path


def test_compiled_memory_template_only_adds_the_pinned_embedding_deployment():
    root = Path(__file__).resolve().parents[2]
    template = json.loads((root / "infra" / "memory-showcase.json").read_text(encoding="utf-8"))
    resources = template["resources"]
    assert len(resources) == 1
    resource = resources[0]
    assert resource["type"] == "Microsoft.CognitiveServices/accounts/deployments"
    assert "showcase-memory-embedding" in resource["name"]
    assert resource["sku"] == {"name": "Standard", "capacity": 1}
    assert resource["properties"]["model"] == {
        "format": "OpenAI", "name": "text-embedding-3-small", "version": "1",
    }
    assert resource["properties"]["versionUpgradeOption"] == "NoAutoUpgrade"
    assert template["parameters"]["regionalQuotaConfirmed"]["allowedValues"] == [True]
    assert "defaultValue" not in template["parameters"]["accountName"]
    assert "defaultValue" not in template["parameters"]["regionalQuotaConfirmed"]
