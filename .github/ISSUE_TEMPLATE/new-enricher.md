---
name: Yeni Enricher Eklentisi
about: Backend Ekibi için BaseEnricher tabanlı yeni IOC sorgu aracı
title: "[ENRICHER] <enricher_id> Eklentisi"
labels: ["enricher", "backend", "ekip-2"]
assignees: []
---

## Eklenti Kimliği ve Kontratı
- **`enricher_id`:** (örn. `dns_passive`, `ssl_cert`)
- **`display_name` (UI Buton Etiketi):** (örn. `Pasif DNS`)
- **`supported_ioc_types`:** `ip` | `hash` | `domain` | `hostname` | `username`
- **`icon_id`:** Kayıtlı PNG sprite (`tool-ip-radar`, `tool-hash-scanner`, `tool-cmdb-server`) veya SVG fallback (`fallback-globe`, `fallback-terminal`)

## Cache-First ve Hata İzolasyonu
- **Veri Kaynağı / Harici API:** (ücretsiz kota limiti ve ortam değişkeni adı, örn. `VT_API_KEY`)
- **Zaman Aşımı:** `timeout_seconds = 3.0`
- **Offline / Hata Davranışı:** API anahtarı yoksa veya ağ hatası oluşursa `EvidenceCard(status="UNAVAILABLE", query_cost_applied=0)` döndürüp oyunu kesintiye uğratmaz.

## Teslim Kontrolü
- [ ] `backend/app/enrichers/base.py` içindeki `BaseEnricher` sınıfından türetildi ve `registry.py`'ye kaydedildi.
- [ ] SQLite Cache-First katmanı (`SqliteIocCache`) ile entegre edildi.
- [ ] `pytest backend/tests -v` geçti.
