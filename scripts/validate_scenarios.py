#!/usr/bin/env python3
"""Standalone JSON scenario validator for BreachZero (stdlib only).

Usage:
    python scripts/validate_scenarios.py
    python scripts/validate_scenarios.py --dir scenarios
    python scripts/validate_scenarios.py --file scenarios/case_01_fp_backup.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REQUIRED_TOP_KEYS = {"schema_version", "meta", "public_alert", "server_only"}
SPOILER_KEYS = {
    "ground_truth",
    "mitre_attack",
    "debrief_explanation",
    "mock_enrichment",
    "hp_penalty_on_miss",
    "category",
    "required_evidence_hints",
}
REQUIRED_PUBLIC_KEYS = {
    "alert_id",
    "incident_code",
    "title",
    "severity",
    "timestamp_utc",
    "sla_seconds",
    "source",
    "destination",
    "host",
    "user",
    "raw_log",
    "indicators",
    "available_enrichers",
}
VALID_SEVERITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
VALID_EVIDENCE_STATUS = {"OK", "NOT_FOUND", "UNAVAILABLE"}
VALID_VERDICT_SIGNALS = {"BENIGN", "SUSPICIOUS", "MALICIOUS", "INFO"}
REQUIRED_MOCK_CARD_KEYS = {
    "enricher_id",
    "display_name",
    "icon_id",
    "status",
    "verdict_signal",
    "summary",
    "details",
    "source_mode",
}


def validate_scenario_data(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["Kök JSON değeri bir nesne (object) olmalıdır."]

    missing_top = REQUIRED_TOP_KEYS - set(data.keys())
    extra_top = set(data.keys()) - REQUIRED_TOP_KEYS
    if missing_top:
        errors.append(f"Eksik üst düzey alan(lar): {sorted(missing_top)}")
    if extra_top:
        errors.append(f"Beklenmeyen üst düzey alan(lar): {sorted(extra_top)}")

    if data.get("schema_version") != "1.0":
        errors.append(f"schema_version '1.0' olmalıdır (bulunan: {data.get('schema_version')!r}).")

    meta = data.get("meta")
    if not isinstance(meta, dict):
        errors.append("'meta' bir JSON nesnesi olmalıdır.")
    else:
        meta_spoilers = SPOILER_KEYS & set(meta.keys())
        if meta_spoilers:
            errors.append(f"'meta' içinde yasaklı spoiler alan(lar): {sorted(meta_spoilers)}")

    pub = data.get("public_alert")
    if not isinstance(pub, dict):
        errors.append("'public_alert' bir JSON nesnesi olmalıdır.")
    else:
        pub_spoilers = SPOILER_KEYS & set(pub.keys())
        if pub_spoilers:
            errors.append(f"'public_alert' içinde spoiler sızıntısı: {sorted(pub_spoilers)}")
        missing_pub = REQUIRED_PUBLIC_KEYS - set(pub.keys())
        if missing_pub:
            errors.append(f"'public_alert' içinde eksik alan(lar): {sorted(missing_pub)}")
        if pub.get("severity") not in VALID_SEVERITIES:
            errors.append(f"Geçersiz severity: {pub.get('severity')!r}")
        sla = pub.get("sla_seconds")
        if not isinstance(sla, int) or sla <= 0:
            errors.append(f"'sla_seconds' pozitif tam sayı olmalıdır (bulunan: {sla!r}).")
        avail = pub.get("available_enrichers")
        if not isinstance(avail, list) or not all(isinstance(x, str) and x for x in avail):
            errors.append("'available_enrichers' boş olmayan string dizisi olmalıdır.")

    srv = data.get("server_only")
    if not isinstance(srv, dict):
        errors.append("'server_only' bir JSON nesnesi olmalıdır.")
    else:
        gt = srv.get("ground_truth")
        if gt not in ("TP", "FP"):
            errors.append(f"'server_only.ground_truth' yalnızca 'TP' veya 'FP' olabilir (bulunan: {gt!r}).")
        hp_pen = srv.get("hp_penalty_on_miss")
        if not isinstance(hp_pen, int) or hp_pen < 0:
            errors.append(f"'server_only.hp_penalty_on_miss' >= 0 tam sayı olmalıdır (bulunan: {hp_pen!r}).")
        elif gt == "FP" and hp_pen != 0:
            errors.append(f"FP senaryosunda 'hp_penalty_on_miss' 0 olmalıdır (bulunan: {hp_pen}).")
        elif gt == "TP" and hp_pen == 0:
            errors.append("TP senaryosunda 'hp_penalty_on_miss' 0'dan büyük olmalıdır (örn. 30 veya 40).")

        debrief = srv.get("debrief_explanation")
        if not isinstance(debrief, str) or len(debrief.strip()) < 20:
            errors.append("'server_only.debrief_explanation' en az 20 karakter olmalıdır.")

        mocks = srv.get("mock_enrichment")
        if not isinstance(mocks, dict):
            errors.append("'server_only.mock_enrichment' bir JSON nesnesi olmalıdır.")
        else:
            if isinstance(pub, dict) and isinstance(pub.get("available_enrichers"), list):
                avail_set = set(pub["available_enrichers"])
                mock_set = set(mocks.keys())
                if avail_set != mock_set:
                    errors.append(
                        f"available_enrichers ({sorted(avail_set)}) ile mock_enrichment ({sorted(mock_set)}) birebir eşleşmiyor."
                    )
            for eid, card in mocks.items():
                if not isinstance(card, dict):
                    errors.append(f"mock_enrichment['{eid}'] bir nesne olmalıdır.")
                    continue
                missing_c = REQUIRED_MOCK_CARD_KEYS - set(card.keys())
                if missing_c:
                    errors.append(f"mock_enrichment['{eid}'] eksik alan(lar): {sorted(missing_c)}")
                if card.get("enricher_id") != eid:
                    errors.append(f"mock_enrichment['{eid}'].enricher_id anahtar ile uyuşmuyor.")
                if card.get("status") not in VALID_EVIDENCE_STATUS:
                    errors.append(f"mock_enrichment['{eid}'].status geçersiz: {card.get('status')!r}")
                if card.get("verdict_signal") not in VALID_VERDICT_SIGNALS:
                    errors.append(f"mock_enrichment['{eid}'].verdict_signal geçersiz: {card.get('verdict_signal')!r}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="BreachZero senaryo JSON dosyalarını doğrular.")
    parser.add_argument("--dir", type=Path, default=Path("scenarios"), help="Senaryo klasörü (varsayılan: scenarios)")
    parser.add_argument("--file", type=Path, default=None, help="Tek bir JSON dosyasını doğrula")
    args = parser.parse_args()

    files = [args.file] if args.file else sorted(args.dir.glob("*.json"))
    if not files:
        print(f"[HATA] Doğrulanacak JSON dosyası bulunamadı: {args.file or args.dir}", file=sys.stderr)
        return 1

    has_error = False
    for path in files:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[HATA] {path}: JSON okuma hatası -> {exc}")
            has_error = True
            continue

        errs = validate_scenario_data(raw)
        if errs:
            has_error = True
            print(f"[HATA] {path}:")
            for err in errs:
                print(f"   - {err}")
        else:
            gt = raw["server_only"]["ground_truth"]
            aid = raw["public_alert"]["alert_id"]
            print(f"[OK]   {path} (id={aid}, ground_truth={gt}, enrichers={len(raw['public_alert']['available_enrichers'])})")

    return 1 if has_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
