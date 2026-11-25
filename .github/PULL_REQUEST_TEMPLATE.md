## Özet
<!-- Bu PR'ın ne yaptığını ve çözdüğü Issue numarasını kısaca yazın (örn: Closes #12) -->

## Katkı Alanı
- [ ] Senaryo & Tehdit İstihbaratı (`scenarios/*.json`)
- [ ] Backend, Enricher & CLI (`backend/app/enrichers/`, `backend/app/cache/`, `scripts/`)
- [ ] Frontend & Pixel UI (`frontend/`, `docs/assets/sprites/`)
- [ ] Güvenlik & Core WebSocket (`backend/app/core/`, `backend/app/ws/`, `backend/tests/`, CI)
- [ ] Dokümantasyon (`docs/`, `README.md`)

## Lokalde Çalıştırılan Doğrulama Komutları
<!-- Çalıştırdığınız komutları işaretleyin -->
- [ ] `python scripts/validate_scenarios.py` (Senaryo değişikliklerinde zorunlu)
- [ ] `pytest backend/tests -v` (Backend / Enricher / Güvenlik değişikliklerinde zorunlu)
- [ ] `cd frontend && npm run build` (Frontend değişikliklerinde zorunlu)
- [ ] `cd frontend && npm run test:e2e` (Opsiyonel tam çoklu-sekme E2E testi)

## Tasarım, Veri Seti ve Kontrat Kontrol Listesi
- [ ] **Senaryo:** `ground_truth`, `mitre_attack`, `debrief_explanation` ve `mock_enrichment` yalnızca `server_only` bloğunda tutuldu (`public_alert` içinde spoiler yok); [`docs/OPEN_SOURCE_DATASETS.md`](../docs/OPEN_SOURCE_DATASETS.md) kurallarına (canlı zararlı binary / PII yasağı) uyuldu.
- [ ] **Frontend (`SKILL.md`):** `border-radius: 0`, `0px` blur gölgeler, tam sayı `16×k` sprite ölçekleme, Türkçe metinlerde `Pixelify Sans` (`>= 15px`) ve loglarda `IBM Plex Mono` kurallarına uyuldu; hardcoded `localhost:8000` yok.
- [ ] **Kontratlar & Güvenlik:** [`docs/CONTRACTS.md`](../docs/CONTRACTS.md) ve [`docs/LEARNING_HANDBOOK.md`](../docs/LEARNING_HANDBOOK.md) sınırları korundu.
