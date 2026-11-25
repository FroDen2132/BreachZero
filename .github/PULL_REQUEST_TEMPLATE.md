## Özet
<!-- Bu PR'ın ne yaptığını ve çözdüğü Issue numarasını kısaca yazın (örn: Closes #12) -->

## Bağlı Olduğunuz Ekip
- [ ] Ekip 1 — Senaryo & Siber Güvenlik (`scenarios/*.json`)
- [ ] Ekip 2 — Backend & Enricher Eklentileri (`backend/app/enrichers/`, `backend/app/cache/`)
- [ ] Ekip 3 — Frontend & Pixel UI (`frontend/`)
- [ ] Ekip 4 — Core WebSocket & Altyapı (`backend/app/core/`, `backend/app/ws/`, CI)

## Lokalde Çalıştırılan Doğrulama Komutları
<!-- Çalıştırdığınız komutları işaretleyin -->
- [ ] `python scripts/validate_scenarios.py` (Senaryo ekibi için zorunlu)
- [ ] `pytest backend/tests -v` (Backend / Core için zorunlu)
- [ ] `cd frontend && npm run build` (Frontend için zorunlu)
- [ ] `cd frontend && npm run test:e2e` (Opsiyonel tam çoklu-sekme E2E testi)

## Tasarım ve Kontrat Kontrol Listesi
- [ ] **Senaryo:** `ground_truth`, `mitre_attack`, `debrief_explanation` ve `mock_enrichment` yalnızca `server_only` bloğunda tutuldu (`public_alert` içinde spoiler yok).
- [ ] **Frontend (`SKILL.md`):** `border-radius: 0`, `0px` blur gölgeler, tam sayı `16×k` sprite ölçekleme, Türkçe metinlerde `Pixelify Sans` (`>= 15px`) ve loglarda `IBM Plex Mono` kurallarına uyuldu; hardcoded `localhost:8000` yok.
- [ ] **Kontratlar:** `docs/CONTRACTS.md` şemaları değiştiyse ilgili ekip liderlerinin onayı alındı.
