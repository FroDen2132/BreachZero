---
name: Yeni Senaryo (TP / FP Vaka)
about: Senaryo & Siber Ekibi için BreachZero alarm vakası önerisi
title: "[SENARYO] <Kısa Vaka Başlığı>"
labels: ["scenario", "ekip-1"]
assignees: []
---

## Vaka Özeti
- **Hedef Dosya Adı:** `scenarios/case_XX_<tp|fp>_<kisa_ad>.json`
- **Gerçek Karar (`ground_truth`):** `TP` / `FP`
- **Zorluk / Tahmini Dalga:** `EASY` | `MEDIUM` | `HARD` — Dalga `#`
- **Önerilen SLA (sn):** `75` – `120`
- **TP Kaçırma Cezası (`hp_penalty_on_miss`):** `0` (FP) / `30` (Standart TP) / `40` (Kritik TP)

## Teknik Detaylar ve IOC'ler
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
- [ ] `python scripts/validate_scenarios.py` hatasız geçti.
