from __future__ import annotations

import json

from authdiff.inventory.collector import collect_inventory
from authdiff.paths import repo_root
from authdiff.semantic import validate_semantics
from authdiff.supply_chain.digest import verify_file_digest
from authdiff.validate_report import analyze_graph_paths, validate_graph_file, validate_report_file


def run_corpus() -> dict:
    root = repo_root() / "tests" / "corpus"
    cases_dir = root / "cases"
    passed = 0
    failed = 0
    results: list[dict] = []

    for case_path in sorted(cases_dir.glob("*.json")):
        case = json.loads(case_path.read_text(encoding="utf-8"))
        case_id = case["case_id"]
        entry: dict = {"case_id": case_id, "checks": []}
        ok = True

        fixture_rel = case.get("fixture_path")
        if fixture_rel:
            fixture = (root / fixture_rel).resolve()
            inv = collect_inventory(fixture)
            expected_components = case.get("expected_inventory", {}).get("min_components", 0)
            actual = len(inv.components)
            check_ok = actual >= expected_components
            entry["checks"].append(
                {
                    "name": "inventory_min_components",
                    "expected_min": expected_components,
                    "actual": actual,
                    "ok": check_ok,
                }
            )
            ok = ok and check_ok
            for substr in case.get("expected_inventory", {}).get("component_names_contain", []):
                names = " ".join(c.get("name", "") for c in inv.components)
                c_ok = substr in names
                entry["checks"].append({"name": f"inventory_name_contains:{substr}", "ok": c_ok})
                ok = ok and c_ok

        report_rel = case.get("report_fixture")
        if report_rel:
            report_path = (root / report_rel).resolve()
            if not report_path.is_file():
                report_path = (repo_root() / "tests" / "corpus" / report_rel).resolve()
            expect = case.get("expect_validation", "pass")
            try:
                sem = validate_report_file(report_path)
                valid = sem.ok
            except SystemExit:
                valid = False
                sem = None
            check_ok = valid if expect == "pass" else not valid
            entry["checks"].append({"name": f"report_{expect}", "ok": check_ok})
            if sem and not sem.ok and expect == "fail":
                entry["semantic_issues"] = [
                    {"code": i.code, "message": i.message} for i in sem.issues[:5]
                ]
            ok = ok and check_ok

        graph_rel = case.get("graph_fixture")
        if graph_rel:
            graph_path = (repo_root() / "tests" / "corpus" / graph_rel).resolve()
            if not graph_path.is_file():
                graph_path = (root / graph_rel).resolve()
            try:
                gsem = validate_graph_file(graph_path, semantic=True)
                g_ok = gsem.ok
            except SystemExit:
                g_ok = False
                gsem = None
            entry["checks"].append({"name": "graph_schema_semantic", "ok": g_ok})
            ok = ok and g_ok
            min_paths = case.get("expect_min_attack_paths")
            if min_paths is not None and g_ok:
                paths = analyze_graph_paths(graph_path)
                p_ok = len(paths) >= min_paths
                entry["checks"].append(
                    {
                        "name": "graph_attack_paths",
                        "expected_min": min_paths,
                        "actual": len(paths),
                        "ok": p_ok,
                    }
                )
                ok = ok and p_ok

        digest_check = case.get("digest_check")
        if digest_check:
            fixture_base = (root / case.get("fixture_path", ".")).resolve()
            target = (fixture_base / digest_check["path"]).resolve()
            digest_ok, digest_hex = verify_file_digest(target, digest_check["expected_sha256"])
            entry["checks"].append(
                {
                    "name": "digest_verify",
                    "ok": digest_ok,
                    "sha256": digest_hex,
                }
            )
            ok = ok and digest_ok

        neg_report = case.get("negative_report_fixture")
        if neg_report:
            path = (root / neg_report).resolve()
            doc = json.loads(path.read_text(encoding="utf-8"))
            sem = validate_semantics(doc)
            expect_fail = case.get("expect_semantic_fail", True)
            check_ok = (not sem.ok) if expect_fail else sem.ok
            entry["checks"].append({"name": "semantic_negative", "ok": check_ok})
            ok = ok and check_ok

        sarif_cfg = case.get("sarif_export")
        report_rel = case.get("report_fixture")
        if sarif_cfg and report_rel:
            from authdiff.export.sarif import report_to_sarif

            report_path = (root / report_rel).resolve()
            if not report_path.is_file():
                report_path = (repo_root() / "tests" / "corpus" / report_rel).resolve()
            doc = json.loads(report_path.read_text(encoding="utf-8"))
            sarif = report_to_sarif(doc)
            count = len(sarif["runs"][0]["results"])
            min_r = sarif_cfg.get("min_results", 1)
            s_ok = count >= min_r
            entry["checks"].append(
                {"name": "sarif_export", "min_results": min_r, "actual": count, "ok": s_ok}
            )
            ok = ok and s_ok

        entry["ok"] = ok
        results.append(entry)
        if ok:
            passed += 1
        else:
            failed += 1

    return {
        "corpus_version": "0.3.3",
        "passed": passed,
        "failed": failed,
        "cases": results,
    }
