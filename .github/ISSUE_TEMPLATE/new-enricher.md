---
name: Yeni Enricher Eklentisi
about: BaseEnricher tabanlı yeni IOC sorgu aracı (Cache-First + Timeout İzolasyonu)
title: "[ENRICHER] <enricher_id> Eklentisi"
labels: ["enricher", "backend", "seviye:orta"]
assignees: []
---

## Eklenti Kimliği ve Kontratı
> Referans: [`docs/CONTRACTS.md`](../../docs/CONTRACTS.md) ve [`docs/LEARNING_HANDBOOK.md`](../../docs/LEARNING_HANDBOOK.md)
- **`enricher_id`:** (örn. `hash_vt`, `whois`, `dns_passive`)
- **`display_name` (UI Buton Etiketi):** (örn. `Hash / VT`, `WHOIS`)
- **`supported_ioc_types`:** `ip` | `hash` | `domain` | `hostname` | `username`
- **`icon_id`:** Kayıtlı PNG sprite (`tool-ip-radar`, `tool-hash-scanner`, `tool-cmdb-server`) veya SVG fallback (`fallback-globe`, `fallback-terminal`)

## Cache-First, Rate-Limit ve Hata İzolasyonu
- **Veri Kaynağı / Harici API:** (ücretsiz kota limiti ve ortam değişkeni adı, örn. `VIRUSTOTAL_API_KEY` veya anahtarsız `rdap.org`)
- **Zaman Aşımı:** `timeout_seconds = 3.0`
- **Offline / Hata Davranışı:** API anahtarı yoksa, `404`/`429` veya ağ hatası oluşursa `EvidenceCard(status="UNAVAILABLE", query_cost_applied=0)` döndürüp oyunu kesintiye uğratmaz.

## Teslim Kontrolü
- [ ] `backend/app/enrichers/base.py` içindeki `BaseEnricher` sınıfından türetildi ve `registry.py`'ye kaydedildi.
- [ ] SQLite Cache-First katmanı (`SqliteIocCache`) ve mock `httpx` testleriyle doğrulandı.
- [ ] `pytest backend/tests -v` geçti.
