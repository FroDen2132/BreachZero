---
name: Yeni Senaryo (TP / FP Vaka)
about: ThreatFox, MalwareBazaar, SigmaHQ veya Mordor tabanlı yeni BreachZero alarm vakası
title: "[SENARYO] <Kısa Vaka Başlığı>"
labels: ["scenario", "seviye:baslangic"]
assignees: []
---

## Vaka Özeti
- **Hedef Dosya Adı:** `scenarios/case_XX_<tp|fp>_<kisa_ad>.json`
- **Gerçek Karar (`ground_truth`):** `TP` / `FP`
- **Zorluk / Tahmini Dalga:** `EASY` | `MEDIUM` | `HARD` — Dalga `#`
- **Önerilen SLA (sn):** `75` – `120`
- **TP Kaçırma Cezası (`hp_penalty_on_miss`):** `0` (FP) / `30` (Standart TP) / `40` (Kritik TP)

## Açık Kaynak Veri Seti & IOC Detayları
> Rehber: [`docs/OPEN_SOURCE_DATASETS.md`](../../docs/OPEN_SOURCE_DATASETS.md) (Issue açıklamasında zararlı URL/IP'leri defang edin: `185[.]220[.]101[.]44`, `hxxp://...`)
- **Referans Kaynak (SigmaHQ / OTRF Mordor / Attack Data / MalwareBazaar / ThreatFox):**
- **Ham Log Özeti (`raw_log`):**
- **Kullanılacak IOC'ler:** IP / SHA256 Hash / Domain / Kullanıcı / Hostname
- **Gerekli Enrichment Araçları (`available_enrichers`):**
  - [ ] `ip_reputation`
  - [ ] `hash_vt`
  - [ ] `internal_cmdb`
  - [ ] `whois`

## Eğitim Çıktısı (Debrief)
- **MITRE ATT&CK Teknikleri (TP ise):** örn. `T1558.003`
- **Maç Sonu Türkçe Açıklama (`debrief_explanation`):** Oyuncunun hangi kanıtlara bakarak karar vermesi gerektiği.

## Teslim Kontrolü
- [ ] `available_enrichers` ile `server_only.mock_enrichment` anahtarları birebir eşleşiyor.
- [ ] Gerçek kurum/kişi verisi (PII) veya canlı zararlı ikili dosyası eklenmedi.
- [ ] `python scripts/validate_scenarios.py` hatasız geçti.
