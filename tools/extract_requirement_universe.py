#!/usr/bin/env python3
"""Extract R3 §4 metadata without importing or executing any archived/runtime code.

Run ``python -I tools/extract_requirement_universe.py --write`` to regenerate.
Both check modes are read-only and verify current artifacts and source counts.
``--check-source-counts`` permits honest pending implementation mappings; exit 2
means a source-count conflict. ``--check`` also requires final traceability
completion, returning 2 for pending mappings. Exit 1 means invalid sources or
stale/invalid artifacts. Pending rows have an empty final_status and a separate
NOT_IMPLEMENTED implementation_state.
Existing implementation mappings are preserved by ID when regenerating.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import stat
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = "design/War_Rig_V3_Complete_Offline_Design_V5_MSB_REVIEW_CANDIDATE_20261113.zip"
ARCHIVE_SHA256 = "3d6632a2d662deade05b957ad822edd9af6e8eda8c1d7ebca3f098e122760796"
PROMPT = "prompts/War_Rig_V3_OWNER_DIRECTED_OFFLINE_START_MASTER_IDE_PROMPT_R3_20261116.md"
PIN = "SOURCE_PINS_UNMODIFIED/"
D03 = PIN + "STAGE_D03_REVIEW_BYTES/"
COMPONENTS = "01_COMPLETE_OFFLINE_CORE_DESIGN_13_COMPONENTS.md"
MODULES = "02_SCOPE_C_COMPLETE_18_MODULE_SCHEDULE.csv"
DECISIONS = "05_CONSOLIDATED_61_ROW_OWNER_DECISION_REGISTER_NOT_SELECTED.csv"
FINDINGS = "06_ORIGINAL_13_FREEZE_FINDINGS_OPEN.csv"
REPAIRS = "07_ORIGINAL_21_REPAIRS_OPEN.csv"
EDGES = D03 + "01_EDGE_CONTRACTS_35_DRAFT.json"
NEGATIVES = D03 + "02_NEGATIVE_GRAPH_COMPLEMENT_59_SOURCE_PRESERVED.json"
TESTS = D03 + "06_DETERMINISTIC_TEST_PLAN_UNEXECUTED.json"
EXT = PIN + "EXT_G0R_14_UNCHANGED.md"
MASTER = PIN + "MASTER_V1_8_CORRECTED_UNCHANGED.md"
ATC = PIN + "ATC_01_REV2_UNCHANGED.md"
WDA = PIN + "WDA_08_UNCHANGED.md"
MSB = "24_MSB_CONTROLLED_DUAL_SOURCE_PREDICTIONS_CONTRACT.md"
INIT = "08_ACCEPTANCE_TEST_CONTRACT_AND_FAILURE_MATRIX.md"
EXPECTED = {
    "component": 13,
    "module": 18,
    "owner_decision": 61,
    "finding": 13,
    "repair": 21,
    "d03_test": 187,
    "d03_edge": 42,
    "d03_negative_case": 59,
    "msb_test": 19,
    "initial_protection_test": 10,
    "v3ext_oracle": 83,
}
FINAL_STATUSES = {
    "IMPLEMENTED_TESTED",
    "DENIED_BY_POLICY_TESTED",
    "OUT_OF_G1_SCOPE",
    "BLOCKED_MISSING_APPROVAL",
    "NOT_APPLICABLE_WITH_SIGNED_PROOF",
}
UNIVERSE_FIELDS = [
    "universe_id",
    "source_id",
    "requirement_classes",
    "source_member",
    "source_clause",
    "source_line_start",
    "source_line_end",
    "source_jsonpath",
    "source_sha256",
    "original_text",
    "source_references_json",
    "related_ids",
]
MAPPING_FIELDS = [
    "implementation_state",
    "final_status",
    "applicability",
    "runtime_module_class_function",
    "positive_tests",
    "negative_fault_tests",
    "executed_result",
    "evidence_paths",
    "approval_or_signed_proof",
    "mapping_notes",
]
TRACE_FIELDS = UNIVERSE_FIELDS + MAPPING_FIELDS
OUTPUTS = {
    "universe": "evidence/requirement_universe.csv",
    "traceability": "evidence/traceability.csv",
    "report": "evidence/REQUIREMENT_UNIVERSE_REPORT.json",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def packed(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_archive():
    raw = (ROOT / ARCHIVE).read_bytes()
    require(digest(raw) == ARCHIVE_SHA256, "BLOCKED_SOURCE_INTEGRITY: archive hash")
    members = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        for info in archive.infolist():
            path = PurePosixPath(info.filename)
            mode = info.external_attr >> 16
            require(
                bool(info.filename)
                and not path.is_absolute()
                and ".." not in path.parts
                and "\\" not in info.filename
                and ":" not in info.filename
                and str(path) == info.filename
                and not info.is_dir()
                and (not stat.S_IFMT(mode) or stat.S_ISREG(mode)),
                f"BLOCKED_SOURCE_INTEGRITY: unsafe ZIP entry {info.filename!r}",
            )
            require(info.filename not in members, "BLOCKED_SOURCE_INTEGRITY: duplicate ZIP name")
            require(info.file_size <= 16_000_000, "BLOCKED_SOURCE_INTEGRITY: oversized ZIP entry")
            members[info.filename] = archive.read(info)
    manifest_raw = members["MANIFEST_SHA256.json"]
    manifest = json.loads(manifest_raw)
    paths = [entry["path"] for entry in manifest["entries"]]
    require(len(paths) == len(set(paths)) == 69, "BLOCKED_SOURCE_INTEGRITY: manifest count")
    require(
        set(paths) == set(members) - {"MANIFEST_SHA256.json"},
        "BLOCKED_SOURCE_INTEGRITY: manifest inventory",
    )
    for entry in manifest["entries"]:
        data = members[entry["path"]]
        require(
            len(data) == entry["size_bytes"] and digest(data) == entry["sha256"],
            f"BLOCKED_SOURCE_INTEGRITY: {entry['path']}",
        )
    return members, {
        "archive": ARCHIVE,
        "archive_sha256": digest(raw),
        "manifest_sha256": digest(manifest_raw),
        "manifest_entry_count": len(paths),
        "archive_entry_count": len(members),
        "candidate_id": manifest["id"],
        "candidate_status": manifest["status"],
        "approved_group_root": None,
        "member_sha256": {name: digest(data) for name, data in sorted(members.items())},
        "safety": "All 70 entries verified; no extraction/import/execution of archive code.",
    }


class Extractor:
    def __init__(self, members):
        self.members = members
        self.rows = {}
        self.class_ids = defaultdict(set)
        self.recipes = []
        self.conflicts = []
        self.decision_kinds = Counter()

    def text(self, member):
        return self.members[member].decode("utf-8-sig")

    def reference(self, member, start, end, clause="", jsonpath=""):
        text = self.text(member)
        line_start = text.count("\n", 0, start) + 1
        line_end = text.count("\n", 0, max(start, end - 1)) + 1
        if not clause:
            headings = re.findall(r"^#{1,6}\s+(.+)$", text[:start], re.MULTILINE)
            clause = headings[-1] if headings else "document"
        return {
            "member": member,
            "clause": clause,
            "line_start": line_start,
            "line_end": line_end,
            "jsonpath": jsonpath,
            "sha256": digest(self.members[member]),
            "text": text[start:end],
        }

    def add(self, identifier, kind, reference, source_id=None):
        self.class_ids[kind].add(identifier)
        if identifier not in self.rows:
            self.rows[identifier] = {
                "source_id": source_id or identifier,
                "classes": set(),
                "references": [],
            }
        row = self.rows[identifier]
        row["classes"].add(kind)
        if reference not in row["references"]:
            row["references"].append(reference)

    def csv_rows(self, member, key, kind, pattern=None, namespace=""):
        text = self.text(member)
        reader = csv.DictReader(io.StringIO(text, newline=""))
        lines = text.splitlines(keepends=True)
        previous = 1
        seen = set()
        for index, row in enumerate(reader):
            identifier = row[key]
            require(
                pattern is None or re.fullmatch(pattern, identifier),
                f"Unrecognised {kind} ID {identifier!r}",
            )
            require(identifier not in seen, f"Duplicate {kind} source row: {identifier}")
            seen.add(identifier)
            start = sum(map(len, lines[:previous]))
            end = sum(map(len, lines[: reader.line_num]))
            reference = self.reference(
                member, start, end, f"CSV data row {index + 1}; {key}={identifier}"
            )
            reference["record"] = row
            self.add(namespace + identifier, kind, reference, identifier)
            if kind == "owner_decision":
                self.decision_kinds[row["kind"]] += 1
            previous = reader.line_num
        self.recipes.append(
            {"class": kind, "member": member, "selector": key, "pattern": pattern or "nonempty"}
        )

    def json_rows(self, member, key):
        text = self.text(member)
        data = json.loads(text)
        match = re.search(r'"' + re.escape(key) + r'"\s*:\s*\[', text)
        require(match is not None, f"Missing JSON collection {key}")
        cursor = match.end()
        rows = []
        for index, expected in enumerate(data[key]):
            cursor += len(text[cursor:]) - len(text[cursor:].lstrip())
            start = cursor
            row, cursor = json.JSONDecoder().raw_decode(text, cursor)
            require(row == expected, f"JSON row mismatch {member}:{index}")
            reference = self.reference(
                member, start, cursor, f"{key}[{index}]", f"$.{key}[{index}]"
            )
            reference["record"] = row
            rows.append((row, reference))
            cursor += len(text[cursor:]) - len(text[cursor:].lstrip())
            if text[cursor : cursor + 1] == ",":
                cursor += 1
        return rows

    def literals(self, member, kind, pattern):
        text = self.text(member)
        for match in re.finditer(pattern, text):
            start = text.rfind("\n", 0, match.start()) + 1
            end = text.find("\n", match.end())
            self.add(
                match.group(),
                kind,
                self.reference(member, start, len(text) if end < 0 else end),
            )
        self.recipes.append({"class": kind, "member": member, "pattern": pattern})

    def conflict(self, check, expected, actual, **details):
        if expected != actual:
            self.conflicts.append(
                {
                    "status": "BLOCKED_SOURCE_CONFLICT",
                    "check": check,
                    "expected": expected,
                    "actual": actual,
                    **details,
                }
            )

    def extract(self):
        text = self.text(COMPONENTS)
        pattern = r"^\| (\d{2}) \| ([^\n]+)$"
        for match in re.finditer(pattern, text, re.MULTILINE):
            self.add(
                "COMPONENT-" + match[1],
                "component",
                self.reference(COMPONENTS, match.start(), match.end()),
                match[1],
            )
        self.recipes.append({"class": "component", "member": COMPONENTS, "pattern": pattern})
        self.csv_rows(MODULES, "module", "module", r".+", "MODULE:")
        self.csv_rows(
            DECISIONS, "decision_id", "owner_decision", r"(?:OD-\d{2}|ATC-J\d|OC-D\d{2}-\d{2})"
        )
        self.csv_rows(FINDINGS, "finding_id", "finding", r"D\d{2}-(?:FREEZE|NOTE)-\d{2}")
        self.csv_rows(REPAIRS, "repair_id", "repair", r"R-\d{2}")
        test_rows = self.json_rows(TESTS, "tests")
        for row, reference in test_rows:
            require(re.fullmatch(r"[A-Z0-9]+(?:-[A-Z0-9]+)+", row["id"]), "Invalid test ID")
            self.add(row["id"], "d03_test", reference)
        require(
            len(test_rows) == len(self.class_ids["d03_test"]), "Duplicate D03 test specification ID"
        )
        self.recipes.append({"class": "d03_test", "member": TESTS, "selector": "$.tests[*].id"})
        for member, collection, field, kind, pattern in [
            (
                EDGES,
                "edge_contracts",
                "candidate_id",
                "d03_edge",
                r"D03-(?:SRC|ADD|MST)-\d{3}",
            ),
            (
                NEGATIVES,
                "negative_cases",
                "negative_id",
                "d03_negative_case",
                r"(?:CC1-NEG|SD2-MST-NEG)-\d{3}",
            ),
        ]:
            source_rows = self.json_rows(member, collection)
            for row, reference in source_rows:
                require(re.fullmatch(pattern, row[field]), f"Invalid {field}: {row[field]}")
                self.add(row[field], kind, reference)
            require(
                len(source_rows) == len(self.class_ids[kind]),
                f"Duplicate authoritative {kind} ID",
            )
            self.recipes.append(
                {
                    "class": kind,
                    "member": member,
                    "selector": f"$.{collection}[*].{field}",
                    "pattern": "^" + pattern + "$",
                }
            )
        self.literals(EDGES, "edge_oracle", r"\bSD[12]-EDGE-\d{3}-(?:POS|NEG)\b")
        self.literals(MSB, "msb_test", r"\bMSB-\d{2}\b")
        self.literals(INIT, "initial_protection_test", r"\bTC-INIT-\d{2}\b")
        self.literals(EXT, "v3ext_oracle", r"\bV3EXT-\d{3}\b")
        self.literals(ATC, "atc_contract_oracle", r"\bATC-(?:T|C|X|I)\d{2}\b")
        self.literals(WDA, "wda_oracle", r"\bV3WDA-\d{3}\b")
        self.literals(MASTER, "inherited_g1r", r"\bG1R-\d{2}-[A-Z]\b")
        self.literals(EXT, "inherited_g1r", r"\bG1R-\d{2}-[A-Z]\b")
        vector_pattern = r"^\*\*(V[1-6])\.\s"
        for match in re.finditer(vector_pattern, self.text(WDA), re.MULTILINE):
            end = self.text(WDA).find("\n**", match.end())
            self.add(
                "WDA-CF-1:" + match[1],
                "wda_canonical_vector",
                self.reference(
                    WDA, match.start(), len(self.text(WDA)) if end < 0 else end, "§21; " + match[1]
                ),
                match[1],
            )
        self.recipes.append(
            {"class": "wda_canonical_vector", "member": WDA, "pattern": vector_pattern}
        )
        for kind, expected in EXPECTED.items():
            recipes = [recipe for recipe in self.recipes if recipe["class"] == kind]
            self.conflict(
                kind + "_count",
                expected,
                len(self.class_ids[kind]),
                source_selectors=recipes,
                actual_ids=sorted(self.class_ids[kind]),
            )
        for kind, expected in {
            "MASTER_BINDING_ITEM": 43,
            "STAGE_D_OWNER_DECISION": 14,
            "ATC01_OWNER_DECISION": 4,
        }.items():
            self.conflict("decision_kind:" + kind, expected, self.decision_kinds[kind])
        for kind, prefix, count, width in [
            ("msb_test", "MSB-", 19, 2),
            ("initial_protection_test", "TC-INIT-", 10, 2),
            ("v3ext_oracle", "V3EXT-", 83, 3),
        ]:
            expected = {f"{prefix}{number:0{width}d}" for number in range(1, count + 1)}
            actual = self.class_ids[kind]
            self.conflict(
                kind + "_exact_set",
                sorted(expected),
                sorted(actual),
                missing=sorted(expected - actual),
                extra=sorted(actual - expected),
            )
        return self.graph()

    def graph(self):
        edges = self.json_rows(EDGES, "edge_contracts")
        negatives = self.json_rows(NEGATIVES, "negative_cases")
        domains = defaultdict(set)
        guarded = set()
        excluded = set()
        all_edges = set()
        pair_sources = {}
        for row, reference in edges:
            pair = (row["axis"], row["from_state"], row["to_state"])
            require(pair not in all_edges, f"Duplicate edge pair {pair}")
            all_edges.add(pair)
            domains[row["axis"]].update((row["from_state"], row["to_state"]))
            treatment = row["source_reachability"]
            require(
                treatment
                in {
                    "GUARDED candidate",
                    "GUARDED candidate (MASTER_EXTENSION_PENDING)",
                    "EXCLUDED resting-entry",
                },
                f"Unknown graph treatment {treatment}",
            )
            (excluded if treatment.startswith("EXCLUDED") else guarded).add(pair)
            pair_sources[pair] = {
                "candidate_id": row["candidate_id"],
                "member": reference["member"],
                "jsonpath": reference["jsonpath"],
                "line_start": reference["line_start"],
                "sha256": reference["sha256"],
            }
        # ∅ is a pre-state only. Keep the four excluded resting edges in the
        # vocabulary; removing their states would silently shrink the complement.
        combinations = {
            (axis, before, after)
            for axis, states in domains.items()
            for before in states
            for after in states - {"∅"}
        }
        denied = combinations - guarded
        pinned = {(row["axis"], row["from_state"], row["to_state"]) for row, _ in negatives}
        require(len(pinned) == len(negatives), "Duplicate pinned negative pair")
        self.conflict("rederived_guarded_pairs", 38, len(guarded))
        self.conflict("rederived_denied_pairs", 84, len(denied))
        self.conflict("negative_complement_missing_pairs", [], sorted(denied - pinned))
        self.conflict("negative_complement_extra_pairs", [], sorted(pinned - denied))
        self.conflict("excluded_edges_missing_from_denials", [], sorted(excluded - denied))
        return {
            "method": "Derive each axis enum from file01 from/to states; Cartesian "
            "(enum × (enum minus ∅)); subtract only individually GUARDED candidate pairs. "
            "Compare resulting complement against every file02 negative_cases row.",
            "sources": [
                EDGES,
                NEGATIVES,
                D03 + "00_STAGE_D01_INTEGRATED_TECHNICAL_SPECIFICATION.md",
            ],
            "domain_source": "$.edge_contracts[*].{axis,from_state,to_state}",
            "treatment_source": "$.edge_contracts[*].source_reachability",
            "axes": {axis: sorted(states) for axis, states in sorted(domains.items())},
            "candidate_rows_actual": len(edges),
            "candidate_ids": [row["candidate_id"] for row, _ in edges],
            "positive_EDGE_oracle_ids_actual": sum(
                bool(re.fullmatch(r"SD[12]-EDGE-\d{3}-POS", str(row["positive_design_oracle_id"])))
                for row, _ in edges
            ),
            "negative_EDGE_oracle_ids_actual": sum(
                bool(re.fullmatch(r"SD[12]-EDGE-\d{3}-NEG", row["guard_failure_oracle_id"]))
                for row, _ in edges
            ),
            "cartesian_pairs_actual": len(combinations),
            "guarded_pairs_actual": len(guarded),
            "denied_pairs_actual": len(denied),
            "excluded_resting_pairs_actual": len(excluded),
            "preserved_CC1_negative_ids_actual": sum(
                row["negative_id"].startswith("CC1-NEG-") for row, _ in negatives
            ),
            "master_added_negative_ids_actual": sum(
                row["negative_id"].startswith("SD2-MST-NEG-") for row, _ in negatives
            ),
            "guarded_pairs": [
                {"axis": a, "from_state": b, "to_state": c, **pair_sources[(a, b, c)]}
                for a, b, c in sorted(guarded)
            ],
            "denied_pairs": [
                {
                    "axis": row["axis"],
                    "from_state": row["from_state"],
                    "to_state": row["to_state"],
                    "negative_id": row["negative_id"],
                    "member": NEGATIVES,
                    "jsonpath": reference["jsonpath"],
                    "line_start": reference["line_start"],
                    "sha256": reference["sha256"],
                }
                for row, reference in negatives
                if (row["axis"], row["from_state"], row["to_state"]) in denied
            ],
            "missing_pinned_pairs": sorted(denied - pinned),
            "extra_pinned_pairs": sorted(pinned - denied),
            "runtime_transition_authority": False,
        }

    def universe(self):
        rows = []
        ids = set(self.rows)
        for identifier, data in sorted(self.rows.items()):
            references = sorted(
                data["references"],
                key=lambda ref: (ref["member"], ref["line_start"], ref["jsonpath"]),
            )
            # Prefer the actual detailed specification over an earlier mention.
            primary = max(
                references,
                key=lambda ref: (
                    bool(ref["jsonpath"]),
                    ref["text"].lstrip().startswith("|"),
                    len(ref["text"]),
                ),
            )
            related = set()
            for reference in references:
                related.update(
                    token
                    for token in re.findall(r"\b[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+\b", reference["text"])
                    if token in ids and token != identifier
                )
            rows.append(
                {
                    "universe_id": identifier,
                    "source_id": data["source_id"],
                    "requirement_classes": ";".join(sorted(data["classes"])),
                    "source_member": primary["member"],
                    "source_clause": primary["clause"],
                    "source_line_start": str(primary["line_start"]),
                    "source_line_end": str(primary["line_end"]),
                    "source_jsonpath": primary["jsonpath"],
                    "source_sha256": primary["sha256"],
                    "original_text": primary["text"],
                    "source_references_json": packed(references),
                    "related_ids": ";".join(sorted(related)),
                }
            )
        return rows


def csv_bytes(rows, fields):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


def trace_rows(universe):
    previous = {}
    path = ROOT / OUTPUTS["traceability"]
    if path.exists():
        reader = csv.DictReader(io.StringIO(path.read_text(encoding="utf-8")))
        require(reader.fieldnames == TRACE_FIELDS, "Traceability schema differs")
        for row in reader:
            identifier = row["universe_id"]
            require(identifier not in previous, f"Duplicate traceability ID {identifier}")
            previous[identifier] = row
        require(
            set(previous) <= {row["universe_id"] for row in universe},
            "Traceability IDs outside actual universe; no silent drop",
        )
    rows = []
    for source in universe:
        mapping = {
            "implementation_state": "NOT_IMPLEMENTED",
            "final_status": "",
            "applicability": "PENDING_REQUIREMENT_LEVEL_REVIEW",
            "runtime_module_class_function": "",
            "positive_tests": "",
            "negative_fault_tests": "",
            "executed_result": "NOT_RUN",
            "evidence_paths": "",
            "approval_or_signed_proof": "",
            "mapping_notes": "Pending full requirement implementation and source-to-test mapping. "
            "No owner-approval block or passing runtime result is inferred. "
            "A1 is partial foundations, not proof of this entire requirement.",
        }
        if source["universe_id"] in previous:
            mapping.update({key: previous[source["universe_id"]][key] for key in MAPPING_FIELDS})
        status = mapping["final_status"]
        require(not status or status in FINAL_STATUSES, f"Invalid final status {status}")
        require(
            mapping["implementation_state"]
            in {"NOT_IMPLEMENTED", "PARTIALLY_IMPLEMENTED", "IMPLEMENTED", "NOT_APPLICABLE"},
            "Invalid implementation_state",
        )
        if mapping["implementation_state"] in {"NOT_IMPLEMENTED", "PARTIALLY_IMPLEMENTED"}:
            require(
                status not in {"IMPLEMENTED_TESTED", "DENIED_BY_POLICY_TESTED"},
                "Incomplete requirement cannot be marked tested",
            )
        if status in {"IMPLEMENTED_TESTED", "DENIED_BY_POLICY_TESTED"}:
            require(
                mapping["executed_result"] == "PASS"
                and bool(mapping["runtime_module_class_function"])
                and bool(mapping["positive_tests"] or mapping["negative_fault_tests"])
                and bool(mapping["evidence_paths"]),
                "Tested claim missing runtime/tests/results/evidence mapping",
            )
        if status in {"BLOCKED_MISSING_APPROVAL", "NOT_APPLICABLE_WITH_SIGNED_PROOF"}:
            require(
                bool(mapping["approval_or_signed_proof"]),
                "Approval blocker or signed exception requires specific evidence",
            )
        if not status:
            require(mapping["executed_result"] != "PASS", "Pending requirement cannot claim PASS")
        rows.append({**source, **mapping})
    return rows


def artifacts():
    members, integrity = read_archive()
    extractor = Extractor(members)
    graph = extractor.extract()
    universe = extractor.universe()
    trace = trace_rows(universe)
    pending = [row["universe_id"] for row in trace if not row["final_status"]]
    vocabulary = []
    if pending:
        vocabulary.append(
            {
                "status": "BLOCKED_TRACE_STATUS_VOCABULARY_CONFLICT",
                "source": PROMPT + " §4",
                "explanation": "The five final statuses have no honest pending value. "
                "Pending rows retain empty final_status and explicit implementation_state. "
                "They are not approval blockers, final dispositions, or TEST_PASS.",
                "pending_count": len(pending),
            }
        )
    universe_content = csv_bytes(universe, UNIVERSE_FIELDS)
    trace_content = csv_bytes(trace, TRACE_FIELDS)
    report = {
        "schema_version": 1,
        "status": "BLOCKED_SOURCE_CONFLICT"
        if extractor.conflicts
        else ("PENDING_TRACEABILITY" if pending else "COMPLETE"),
        "traceability_complete": not extractor.conflicts and not pending,
        "runtime_stages_blocked_by_this_report": False,
        "controlling_prompt": {"path": PROMPT, "sha256": digest((ROOT / PROMPT).read_bytes())},
        "generator": {
            "path": "tools/extract_requirement_universe.py",
            "sha256": digest(Path(__file__).read_bytes()),
            "mode": "STANDARD_LIBRARY_METADATA_ONLY_NO_V3_OR_ARCHIVE_IMPORT",
        },
        "integrity": integrity,
        "counts": {
            kind: {
                "expected_by_R3": EXPECTED.get(kind),
                "actual_distinct": len(identifiers),
                "ids": sorted(identifiers),
            }
            for kind, identifiers in sorted(extractor.class_ids.items())
        },
        "decision_kinds": dict(sorted(extractor.decision_kinds.items())),
        "extraction_recipes": extractor.recipes,
        "identity_rules": [
            "One row per distinct full ID; repeated references and shared classes are merged.",
            "Components have only local numeric IDs: COMPONENT-<source number>.",
            "Module source names are preserved under MODULE:<exact source name>.",
            "WDA §21 local V1..V6 IDs are qualified as WDA-CF-1:V1..V6.",
            "Edge identities come from file01 $.edge_contracts[*].candidate_id: "
            "42 exact D03-SRC/ADD/MST IDs. They are distinct from the 80 POS/NEG "
            "oracle IDs, which are preserved as their own shared D03-test IDs.",
            "Negative-case identities come from file02 $.negative_cases[*].negative_id: "
            "59 CC1-NEG plus 25 SD2-MST-NEG IDs. Do not silently drop master additions.",
            "No authoritative ID field value matches literal ^EDGE-[0-9]+$ or "
            "^NEG-[0-9]+$. R3's EDGE-/NEG- family wording is not their actual namespace. "
            "Original full IDs are preserved; no bare EDGE-/NEG- IDs are manufactured.",
            "ATC document version IDs are not test IDs. T/C requirements, X tests and "
            "I integration oracle rows are included; J owner rows come from member05.",
            "V3WDA oracle rows and six named canonical vectors are included. Historical "
            "WDA versions, review-finding IDs and anonymous rejection cases are not new IDs.",
            "Inherited G1R IDs are full numeric-unit/single-letter IDs in MASTER and EXT, "
            "not slice labels, family shorthand or invented range expansions.",
            "Original decision columns and byte-faithful CSV records are retained in provenance.",
        ],
        "universe_row_count": len(universe),
        "class_membership_count": sum(len(ids) for ids in extractor.class_ids.values()),
        "shared_ID_membership_excess": sum(len(ids) for ids in extractor.class_ids.values())
        - len(universe),
        "overlap_explanation": "All 80 edge oracle IDs and all 84 negative_case IDs also "
        "occur as D03 test IDs. They each have one universe row with multiple classes. "
        "The 42 D03 candidate_id values are separate edge-identity rows.",
        "traceability_row_count": len(trace),
        "one_to_one_mapping": len(universe) == len(trace),
        "source_conflicts": extractor.conflicts,
        "identifier_field_evidence": {
            "edge": {
                "member": EDGES,
                "jsonpath": "$.edge_contracts[*].candidate_id",
                "distinct_authoritative_ids": len(extractor.class_ids["d03_edge"]),
                "first_id": graph["candidate_ids"][0],
                "last_id": graph["candidate_ids"][-1],
                "literal_EDGE_base_pattern": "^EDGE-[0-9]+$",
                "literal_EDGE_base_matches": sum(
                    bool(re.fullmatch(r"EDGE-[0-9]+", identifier))
                    for identifier in extractor.class_ids["d03_edge"]
                ),
                "suffix_oracle_ids_not_edge_identities": len(extractor.class_ids["edge_oracle"]),
            },
            "negative_case": {
                "member": NEGATIVES,
                "jsonpath": "$.negative_cases[*].negative_id",
                "distinct_authoritative_ids": len(extractor.class_ids["d03_negative_case"]),
                "preserved_ids": "CC1-NEG-001..CC1-NEG-059",
                "added_ids": "SD2-MST-NEG-001..SD2-MST-NEG-025",
                "literal_NEG_base_pattern": "^NEG-[0-9]+$",
                "literal_NEG_base_matches": sum(
                    bool(re.fullmatch(r"NEG-[0-9]+", identifier))
                    for identifier in extractor.class_ids["d03_negative_case"]
                ),
                "expected_59_scope": "Matches the 59 preserved CC1 rows only, not all "
                "84 actual negative_id fields in the named authoritative file.",
            },
            "correction": "Earlier generator incorrectly compared 80 edge oracle IDs "
            "against 42 edge identities and omitted 42 candidate IDs. Corrected universe "
            "includes all 42 exact candidate IDs and all 84 exact negative IDs, merged "
            "only when the complete ID string is identical to a D03 test ID.",
        },
        "status_vocabulary_conflicts": vocabulary,
        "graph_verification": graph,
        "implementation_state_counts": dict(
            sorted(Counter(row["implementation_state"] for row in trace).items())
        ),
        "final_status_counts": dict(
            sorted(
                Counter(row["final_status"] or "PENDING_NO_FINAL_STATUS" for row in trace).items()
            )
        ),
        "pending_ids": pending,
        "runtime_evidence_boundary": {
            "accepted_A1_commit": "1af562df26f60340164ee7a8e04682f1158d7d52",
            "accepted_A1_artifacts": "evidence/stage_a/a1/",
            "context_only": "A1 metadata loader and UTC ReplayClock: 77 tests, "
            "175 statements, 70 branches. Not requirement-level completion evidence. "
            "No A2/uncommitted or future B–G result is inferred.",
            "runtime_tests_executed_by_generator": False,
            "pending_semantics": "NOT_IMPLEMENTED means no full requirement-level implementation "
            "has been mapped and proven here; it does not deny existing partial A1 work.",
        },
        "blocker_record_boundary": "Only assigned script/CSV/report paths are writable for this "
        "deliverable. Parent must mirror source conflicts into evidence/BLOCKED_REQUIREMENTS.md "
        "as R3 §4 requests; this generator does not modify that shared file.",
        "outputs": {
            OUTPUTS["universe"]: {"sha256": digest(universe_content), "rows": len(universe)},
            OUTPUTS["traceability"]: {"sha256": digest(trace_content), "rows": len(trace)},
        },
        "validation": {
            "command": "python -I tools/extract_requirement_universe.py --check",
            "success_requires": "Current artifacts, no source conflicts, no pending mappings.",
            "expected_current_exit_code": 2 if extractor.conflicts or pending else 0,
            "source_counts": {
                "command": "python -I tools/extract_requirement_universe.py --check-source-counts",
                "success_requires": "Current artifacts, source integrity, exact extraction counts "
                "and one traceability row per universe ID. Honest pending mappings are allowed.",
                "expected_current_exit_code": 2 if extractor.conflicts else 0,
                "pending_implementation_is_source_conflict": False,
            },
            "exit_codes": {
                "0": "Requested gate passed; source-count mode permits pending mappings",
                "1": "Integrity/schema failure or stale artifact",
                "2": "Source-count conflict, or pending completeness in --check/--write only",
            },
        },
    }
    return {
        OUTPUTS["universe"]: universe_content,
        OUTPUTS["traceability"]: trace_content,
        OUTPUTS["report"]: (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode(),
    }, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="Write exact metadata; retain mappings")
    mode.add_argument("--check", action="store_true", help="Read-only final completeness check")
    mode.add_argument(
        "--check-source-counts",
        action="store_true",
        help="Read-only source/artifact/cardinality gate; allow pending implementation",
    )
    args = parser.parse_args()
    try:
        content, report = artifacts()
        for name, expected in content.items():
            path = ROOT / name
            if args.write:
                path.write_bytes(expected)
            else:
                require(path.is_file() and path.read_bytes() == expected, f"Stale artifact: {name}")
        source_count_mode = args.check_source_counts
        gate_exit = (
            report["validation"]["source_counts"]["expected_current_exit_code"]
            if source_count_mode
            else report["validation"]["expected_current_exit_code"]
        )
        gate_status = report["status"]
        if source_count_mode:
            gate_status = "BLOCKED_SOURCE_CONFLICT" if report["source_conflicts"] else "PASS"
        print(
            packed(
                {
                    "artifacts": "WRITTEN" if args.write else "EXACTLY_REPRODUCED",
                    "gate": "SOURCE_COUNTS" if source_count_mode else "FINAL_COMPLETENESS",
                    "status": gate_status,
                    "traceability_status": report["status"],
                    "universe_rows": report["universe_row_count"],
                    "traceability_rows": report["traceability_row_count"],
                    "source_conflicts": [
                        {key: conflict[key] for key in ("check", "expected", "actual")}
                        for conflict in report["source_conflicts"]
                    ],
                    "pending_count": len(report["pending_ids"]),
                    "pending_blocks_requested_gate": not source_count_mode,
                    "runtime_stages_blocked": False,
                }
            )
        )
        return gate_exit
    except (ValueError, KeyError, OSError, UnicodeError, zipfile.BadZipFile) as error:
        print(f"FAILED: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
