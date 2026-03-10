"""Regression tests for the zero-trust assessor."""



from __future__ import annotations







import importlib.util



import sys



from pathlib import Path







import pytest







MODULE_PATH = Path(__file__).resolve().parents[1] / "security" / "imp-zero-trust-assessor.py"



SPEC = importlib.util.spec_from_file_location("imp_zero_trust_assessor", MODULE_PATH)



assessor = importlib.util.module_from_spec(SPEC)



assert SPEC and SPEC.loader



sys.modules[SPEC.name] = assessor



SPEC.loader.exec_module(assessor)











def test_zero_trust_default_passes():



    posture = assessor.collect_posture()



    result = assessor.assess(posture)



    assert result.issues == []



    # Advisories are environment dependent; ensure structure exists.



    assert isinstance(result.advisories, list)











def test_zero_trust_detects_processing_issue():



    posture = assessor.collect_posture()



    posture["processing_security"]["require_allowlist"] = False



    result = assessor.assess(posture)



    assert any("allowlist" in item for item in result.issues)











def test_generate_report_contains_status():



    posture = assessor.collect_posture()



    report = assessor.generate_report(posture)



    assert "IMP Zero-Trust Assessment" in report



    assert "Status:" in report











@pytest.mark.parametrize(



    "idle_minutes, expected_in_advisories",



    [



        (120, True),



        (15, False),



    ],



)



def test_idle_timeout_threshold(idle_minutes, expected_in_advisories):



    posture = assessor.collect_posture()



    posture["session_security"]["max_idle_minutes"] = idle_minutes



    result = assessor.assess(posture)



    contains = any("Idle timeout" in item for item in result.advisories)



    assert contains is expected_in_advisories



