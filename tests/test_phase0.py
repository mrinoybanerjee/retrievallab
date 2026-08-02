from pathlib import Path

import pytest
from retrievallab.constraint import SparseConstraintIndex
from retrievallab.phase0 import load_phase_zero_cases, run_case_probe, run_phase_zero

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "data" / "research" / "phase0-diagnostic-v1.json"


def test_phase_zero_fixture_is_versioned_and_label_complete() -> None:
    cases = load_phase_zero_cases(SUITE)

    assert len(cases) == 16
    assert {case.family for case in cases} == {"catalog", "cross-passage"}
    for case in cases:
        document_ids = {document.id for document in case.documents}
        assert case.complete_document_ids
        assert case.complete_document_ids | case.partial_document_ids == document_ids
        assert not case.complete_document_ids & case.partial_document_ids


def test_coverage_first_is_non_compensatory_and_label_blind() -> None:
    case = load_phase_zero_cases(SUITE)[0]
    index = SparseConstraintIndex(case.documents)

    dense = index.rank(case, "dense")
    candidate = index.rank(case, "coverage_first")

    first_complete_rank = min(candidate.ranked_document_ids.index(item) for item in case.complete_document_ids)
    first_partial_rank = min(candidate.ranked_document_ids.index(item) for item in case.partial_document_ids)
    assert first_complete_rank < first_partial_rank
    assert dense.ranked_document_ids[0] in case.partial_document_ids
    assert candidate.trace["labels_used_in_scoring"] is False
    assert candidate.trace["execution"] == "rarest_condition_first"
    assert candidate.documents_scored < len(case.documents)


def test_diagnostic_report_refuses_a_publication_claim() -> None:
    report = run_phase_zero(SUITE, repeats=1, bootstrap_samples=100, seed=7)

    assert report["reports"]["coverage_first"]["complete_before_partial_at_10"] > report["reports"]["dense"][
        "complete_before_partial_at_10"
    ]
    assert report["reports"]["coverage_first"]["complete_before_partial_at_10"] > report["reports"]["hybrid"][
        "complete_before_partial_at_10"
    ]
    assert report["comparison"]["delta"] == 0.0
    assert report["gate"]["status"] == "not_evaluable"
    assert report["gate"]["diagnostic_decision"] == "simple_control_matches_candidate"
    assert report["provenance"]["labels_used_in_scoring"] is False
    assert report["perturbations"]["reordered"]["delta_from_oracle"] == 0.0
    assert report["perturbations"]["duplicated"]["delta_from_oracle"] == 0.0


def test_interactive_probe_can_disable_a_condition() -> None:
    case = load_phase_zero_cases(SUITE)[0]
    active = {constraint.id for constraint in case.required[:-1]}

    probe = run_case_probe(SUITE, case.id, active_required_ids=active)

    assert set(probe["active_required_ids"]) == active
    assert probe["classification"] == "interactive_diagnostic"
    assert probe["method_runs"]["coverage_first"]["trace"]["labels_used_in_scoring"] is False

    with pytest.raises(ValueError, match="At least one required"):
        run_case_probe(SUITE, case.id, active_required_ids=set())
    with pytest.raises(KeyError):
        run_case_probe(SUITE, "missing-case")
