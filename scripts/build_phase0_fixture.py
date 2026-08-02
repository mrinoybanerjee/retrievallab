from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "research" / "phase0-diagnostic-v1.json"


class ConditionSpec(TypedDict):
    text: str
    alias: str


class Scenario(TypedDict):
    id: str
    subject: str
    required: list[ConditionSpec]
    excluded: ConditionSpec


CATALOG_SCENARIOS: list[Scenario] = [
    {
        "id": "security-platform",
        "subject": "cloud security platform",
        "required": [
            {"text": "SOC 2 Type II certified", "alias": "independent SOC2 type 2 attestation"},
            {"text": "European Union data residency", "alias": "customer data remains in EU regions"},
            {"text": "self hosted deployment", "alias": "runs inside the customer network"},
            {"text": "under 500 dollars monthly", "alias": "monthly price below $500"},
        ],
        "excluded": {"text": "setup fee", "alias": "one-time onboarding charge"},
    },
    {
        "id": "clinical-database",
        "subject": "managed clinical database",
        "required": [
            {"text": "point in time recovery", "alias": "restore to any second"},
            {"text": "HIPAA business associate agreement", "alias": "signed healthcare BAA"},
            {"text": "Virginia cloud region", "alias": "data center in Virginia"},
            {"text": "pay as you go pricing", "alias": "usage based monthly billing"},
        ],
        "excluded": {"text": "annual contract", "alias": "twelve month commitment"},
    },
    {
        "id": "support-suite",
        "subject": "customer support suite",
        "required": [
            {"text": "single sign on", "alias": "SAML SSO"},
            {"text": "immutable audit logs", "alias": "tamper resistant activity history"},
            {"text": "30 day data retention", "alias": "records deleted after one month"},
            {"text": "Slack integration", "alias": "native Slack connector"},
        ],
        "excluded": {"text": "seat minimum", "alias": "minimum agent license count"},
    },
    {
        "id": "observability-stack",
        "subject": "observability stack",
        "required": [
            {"text": "OpenTelemetry ingestion", "alias": "accepts OTEL traces"},
            {"text": "on premise deployment", "alias": "installed in a private data center"},
            {"text": "PII redaction", "alias": "removes personal information"},
            {"text": "under 1000 dollars monthly", "alias": "monthly price below $1,000"},
        ],
        "excluded": {"text": "egress charge", "alias": "fee for exporting data"},
    },
    {
        "id": "translation-sdk",
        "subject": "translation SDK",
        "required": [
            {"text": "offline mode", "alias": "works without an internet connection"},
            {"text": "at least 30 languages", "alias": "supports thirty or more languages"},
            {"text": "mobile software development kit", "alias": "native iOS and Android SDK"},
            {"text": "custom glossary", "alias": "customer terminology dictionary"},
        ],
        "excluded": {"text": "per character billing", "alias": "charge for every translated character"},
    },
    {
        "id": "vector-database",
        "subject": "vector database",
        "required": [
            {"text": "hybrid lexical semantic search", "alias": "combined BM25 and vector retrieval"},
            {"text": "metadata filters", "alias": "structured attribute constraints"},
            {"text": "automatic backups", "alias": "scheduled snapshots"},
            {"text": "ARM processor support", "alias": "runs on arm64 servers"},
        ],
        "excluded": {"text": "GPU requirement", "alias": "dedicated accelerator required"},
    },
    {
        "id": "contact-center",
        "subject": "contact center platform",
        "required": [
            {"text": "SIP trunking", "alias": "bring your own carrier over SIP"},
            {"text": "real time transcription", "alias": "live speech to text"},
            {"text": "PCI redaction", "alias": "payment card details are masked"},
            {"text": "99.99 percent SLA", "alias": "four nines uptime guarantee"},
        ],
        "excluded": {"text": "long term contract", "alias": "multi-year commitment"},
    },
    {
        "id": "document-ai",
        "subject": "document AI service",
        "required": [
            {"text": "table extraction", "alias": "parses rows and columns"},
            {"text": "handwritten form recognition", "alias": "reads cursive forms"},
            {"text": "private cloud deployment", "alias": "isolated customer cloud"},
            {"text": "field confidence scores", "alias": "probability for each extracted value"},
        ],
        "excluded": {"text": "page minimum", "alias": "minimum document volume"},
    },
]


CROSS_PASSAGE_SCENARIOS: list[Scenario] = [
    {
        "id": "municipal-plan",
        "subject": "municipal climate plan",
        "required": [
            {"text": "40 percent emissions reduction", "alias": "cuts emissions by forty percent"},
            {"text": "dedicated public transit funding", "alias": "ring-fenced budget for buses and rail"},
            {"text": "2030 completion deadline", "alias": "must finish by the year 2030"},
        ],
        "excluded": {"text": "highway expansion", "alias": "adds new freeway lanes"},
    },
    {
        "id": "clinical-trial",
        "subject": "oncology clinical trial",
        "required": [
            {"text": "adults age 18 to 65", "alias": "participants between eighteen and sixty-five"},
            {"text": "prior treatment failure", "alias": "previous therapy was unsuccessful"},
            {"text": "two hospital locations", "alias": "recruiting at two medical centers"},
        ],
        "excluded": {"text": "pregnant participants", "alias": "enrollment during pregnancy"},
    },
    {
        "id": "retrieval-paper",
        "subject": "retrieval research paper",
        "required": [
            {"text": "public source code", "alias": "open implementation repository"},
            {"text": "evaluation on natural queries", "alias": "tested with human authored searches"},
            {"text": "CPU latency measurements", "alias": "reports processor-only response time"},
        ],
        "excluded": {"text": "proprietary dataset only", "alias": "results use closed data exclusively"},
    },
    {
        "id": "sustainable-supplier",
        "subject": "packaging supplier",
        "required": [
            {"text": "ISO 27001 certification", "alias": "certified information security system"},
            {"text": "80 percent recycled materials", "alias": "four fifths recycled content"},
            {"text": "delivery under 14 days", "alias": "ships within two weeks"},
        ],
        "excluded": {"text": "minimum order", "alias": "mandatory purchase quantity"},
    },
    {
        "id": "accessible-hotel",
        "subject": "downtown hotel",
        "required": [
            {"text": "wheelchair accessible rooms", "alias": "ADA mobility rooms"},
            {"text": "pet friendly policy", "alias": "dogs and cats are welcome"},
            {"text": "electric vehicle charging", "alias": "EV chargers in the garage"},
        ],
        "excluded": {"text": "resort fee", "alias": "mandatory destination charge"},
    },
    {
        "id": "engineering-role",
        "subject": "machine learning engineering role",
        "required": [
            {"text": "remote within the United States", "alias": "work from anywhere in the US"},
            {"text": "salary above 150000 dollars", "alias": "base pay exceeds $150k"},
            {"text": "visa transfer support", "alias": "employer transfers work authorization"},
        ],
        "excluded": {"text": "on call rotation", "alias": "after-hours pager duty"},
    },
    {
        "id": "climate-grant",
        "subject": "climate adaptation grant",
        "required": [
            {"text": "nonprofit organizations eligible", "alias": "open to charitable organizations"},
            {"text": "community flood resilience", "alias": "local adaptation to flooding"},
            {"text": "September 30 deadline", "alias": "applications close on 30 September"},
        ],
        "excluded": {"text": "matching funds required", "alias": "recipient must provide a cost share"},
    },
    {
        "id": "linux-laptop",
        "subject": "developer laptop",
        "required": [
            {"text": "32 gigabytes of memory", "alias": "32GB RAM"},
            {"text": "Linux hardware certification", "alias": "officially certified for Linux"},
            {"text": "weight under 1.5 kilograms", "alias": "lighter than one and a half kilograms"},
        ],
        "excluded": {"text": "soldered storage", "alias": "non-replaceable SSD"},
    },
]


def sentence(subject: str, clauses: list[str]) -> str:
    return f"{subject.title()}. Verified evidence: {'; '.join(clauses)}."


def build_case(scenario: Scenario, family: str, *, cross_passage: bool) -> dict[str, object]:
    case_id = f"{family}-{scenario['id']}"
    required = [
        {"id": f"c{index + 1}", "text": item["text"], "aliases": [item["alias"]]}
        for index, item in enumerate(scenario["required"])
    ]
    excluded = [{"id": "x1", "text": scenario["excluded"]["text"], "aliases": [scenario["excluded"]["alias"]]}]
    query = (
        f"Find a {scenario['subject']} with "
        f"{', '.join(item['text'] for item in scenario['required'])}, without {scenario['excluded']['text']}."
    )

    def passages(clauses: list[str]) -> list[str]:
        if cross_passage:
            return [sentence(scenario["subject"], [clause]) for clause in clauses]
        return [sentence(scenario["subject"], clauses)]

    literal = [item["text"] for item in scenario["required"]]
    aliases = [item["alias"] for item in scenario["required"]]
    documents: list[dict[str, object]] = [
        {
            "id": f"{case_id}-complete-literal",
            "title": "Complete literal match",
            "passages": passages(literal),
        },
        {
            "id": f"{case_id}-complete-paraphrase",
            "title": "Complete paraphrased match",
            "passages": passages(aliases),
        },
    ]
    for missing_index in range(len(literal)):
        clauses = [clause for index, clause in enumerate(literal) if index != missing_index]
        documents.append(
            {
                "id": f"{case_id}-missing-{missing_index + 1}",
                "title": f"Partial match missing condition {missing_index + 1}",
                "passages": passages(clauses),
            }
        )
    documents.extend(
        [
            {
                "id": f"{case_id}-violates-exclusion",
                "title": "Topical match with forbidden condition",
                "passages": passages([*literal, scenario["excluded"]["text"]]),
            },
            {
                "id": f"{case_id}-topical-decoy",
                "title": "High-topic low-constraint decoy",
                "passages": [
                    (
                        f"Comparison guide for the {scenario['subject']}. This {scenario['subject']} review discusses "
                        f"features, pricing, deployment, compliance, and support for {scenario['subject']} buyers."
                    )
                ],
            },
        ]
    )
    complete_ids = [f"{case_id}-complete-literal", f"{case_id}-complete-paraphrase"]
    partial_ids = [str(document["id"]) for document in documents if document["id"] not in complete_ids]
    return {
        "id": case_id,
        "family": family,
        "query": query,
        "required": required,
        "excluded": excluded,
        "documents": documents,
        "complete_document_ids": complete_ids,
        "partial_document_ids": partial_ids,
    }


def main() -> None:
    cases = [build_case(scenario, "catalog", cross_passage=False) for scenario in CATALOG_SCENARIOS]
    cases.extend(
        build_case(scenario, "cross-passage", cross_passage=True)
        for scenario in CROSS_PASSAGE_SCENARIOS
    )
    payload = {
        "schema_version": "retrievallab-probe-v1",
        "suite": "phase0-diagnostic-v1",
        "classification": "synthetic_diagnostic",
        "description": (
            "Deterministic complete-versus-partial fixtures for implementation falsification. "
            "These cases are not evidence of generalization or publication readiness."
        ),
        "generator": "scripts/build_phase0_fixture.py",
        "cases": cases,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")
    print(f"Wrote {len(cases)} cases to {OUTPUT}")


if __name__ == "__main__":
    main()
