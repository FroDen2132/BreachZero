# BreachZero — Konu & Zorluk Bazlı Katkı Rehberi

Bu rehber, üniversite siber güvenlik kulübündeki 1. sınıftan 4. sınıfa kadar tüm öğrencilerin katı ekip duvarları olmadan, **ilgi alanına ve zorluk seviyesine göre** görev seçip birbirini bloklamadan pull request (PR) açabilmesi için hazırlanmıştır.

> **İlk Kez Mi Katkı Yapıyorsun?** Önce [`docs/LEARNING_HANDBOOK.md`](./LEARNING_HANDBOOK.md) el kitabını (SOC Triyaj 101 + Güvenlik Kavramları + Git/CI adımları) okuyarak 10 dakikada tüm sisteme hakim olabilirsin.

---

## 1. Esnek Çalışma Alanları ve Sahiplik Sınırları

Herhangi bir katılımcı ilgi duyduğu alandan başlayabilir; tek kural değiştirdiğin alanın kontratına uymaktır:

| Çalışma Alanı | İlgili Etiketler | Dokunulan Klasörler | Temel Referans & Kural |
| :--- | :--- | :--- | :--- |
| **Senaryo & Tehdit İstihbaratı** *(Kod bilmeden katkı)* | `scenario` | `scenarios/*.json` | [`docs/CONTRACTS.md`](./CONTRACTS.md) `ScenarioFile` şeması + [`docs/OPEN_SOURCE_DATASETS.md`](./OPEN_SOURCE_DATASETS.md) |
| **Backend, Enricher & Veri Araçları** | `backend`, `enricher` | `backend/app/enrichers/`, `backend/app/cache/`, `scripts/` | Yalnızca `BaseEnricher` kontratını uygular; oyun döngüsüne dokunmaz |
| **Frontend & Pixel UI** | `frontend`, `pixel-art` | `frontend/`, `docs/assets/sprites/` | [`.agent/skills/pixel-soc-ui/SKILL.md`](../.agent/skills/pixel-soc-ui/SKILL.md) ve [`docs/pixel-showcase.html`](./pixel-showcase.html) kurallarına kilitli |
| **Güvenlik, WebSocket & Core Altyapı** | `security`, `backend` | `backend/app/core/`, `backend/app/ws/`, `backend/tests/`, CI | `RoomManager`, `asyncio.Lock`, anti-cheat, girdi doğrulama ve kontrat testleri |

### Zorluk Etiketleri
- `seviye:baslangic` (+ `good first issue`): İlk PR için ideal; tek JSON senaryo, RDAP enricher, ses/tablo UI veya yeni pixel avatar.
- `seviye:orta`: API entegrasyonu (VirusTotal v3, Hybrid Enricher Mode, Linux saldırı senaryosu).
- `seviye:ileri`: Eşzamanlılık/TOCTOU kilitleme, anti-cheat IOC whitelist, bellek DoS ve sabit zamanlı güvenlik sertleştirmeleri.

---

## 2. Alan Bazlı Pratik Çalışma Kuralları

### Senaryo & Tehdit İstihbaratı (`scenario`)
- Her senaryo `scenarios/<case_id>.json` olarak eklenir; sunucu yeniden başlatıldığında oyuna otomatik dahil olur.
- Gerçekçi log ve aktif tehdit göstergesi seçmek için mutlaka [`docs/OPEN_SOURCE_DATASETS.md`](./OPEN_SOURCE_DATASETS.md) içindeki **SigmaHQ, OTRF Mordor, ThreatFox, MalwareBazaar** ve **Event ID tablosu** adımlarını takip edin.
- Her vaka gerçekçi `raw_log`, anlamlı `indicators` ve `available_enrichers` içindeki tüm araçlar için `server_only.mock_enrichment` snapshot'ı içermelidir.
- Örnek şablonlar: [`scenarios/case_01_fp_backup.json`](../scenarios/case_01_fp_backup.json) ve [`scenarios/case_02_tp_kerberoast.json`](../scenarios/case_02_tp_kerberoast.json).

### Backend, Enricher & CLI (`backend`, `enricher`)
- Yeni bir sorgu aracı eklemek için yalnızca `BaseEnricher` soyut sınıfından türeyen tek bir Python dosyası yazılır (`backend/app/enrichers/<arac>.py`).
- Canlı API çağrısı yapılıyorsa `timeout_seconds = 3.0` zorunludur ve mutlaka `SqliteIocCache` + zarif hata izolasyonundan (`UNAVAILABLE`, `0` puan) geçmelidir.
- Veri seti/API detayları için [`docs/OPEN_SOURCE_DATASETS.md`](./OPEN_SOURCE_DATASETS.md) ve [`docs/ARCHITECTURE.md`](./ARCHITECTURE.md) dosyalarına bakın.
- Özel PNG ikonu yoksa `icon_id = "fallback-globe"` veya `"fallback-terminal"` seçilir; yeni sprite çizmek isteyenler [`.agent/skills/pixel-soc-ui/scripts/render_sprite.py`](../.agent/skills/pixel-soc-ui/scripts/render_sprite.py) script'ini kullanır.

### Frontend & Pixel UI (`frontend`, `pixel-art`)
- **Kilitli Stil Kuralı:** Modern yuvarlak kartlar (`border-radius > 0`), blur gölgeler, `VT323` ince fontu veya `9–10px` mikro yazılar **kesinlikle yasaktır**.
- Türkçe metinler `Pixelify Sans` (`>= 15px`, `weight 500–600`, `letter-spacing: 0.04em`), yoğun loglar `IBM Plex Mono` (`14px`, `line-height: 1.55`), saf ASCII sayaç/kodlar `Press Start 2P` (`>= 11px–12px`) kullanır.
- Tüm 16×16 sprite'lar yalnızca `16`'nın tam sayı katlarında (`32×32`, `48×48`, `80×80`) render edilir.
- Oyuncu sekmesinde `session_token` mutlaka `sessionStorage` içinde tutulur; `F5` sonrası otomatik `JOIN_ROOM` ile koltuk kurtarılır.

### Güvenlik & Core Altyapı (`security`, `backend`)
- `public_alert` → `server_only` ayrımını bozacak hiçbir serializasyona izin vermez (otomatik sızıntı testi yazar).
- `CLAIM_ALERT` yarışı, `RUN_ENRICHER` TOCTOU/in-flight kilidi, IOC whitelist, DoS limitleri ve sabit zamanlı token karşılaştırması için [`docs/LEARNING_HANDBOOK.md`](./LEARNING_HANDBOOK.md) Bölüm 2'yi referans alır ve `pytest backend/tests -v` testleri yazar.

---

## 3. Git Branch ve PR Akışı

- **Branch İsimlendirme:**
  - `feat/scenario-phishing-v1`
  - `feat/enricher-whois`
  - `feat/ui-sound-fx`
  - `fix/security-enricher-anticheat`
- **Küçük PR Kuralı:** Bir PR ideal olarak **tek bir senaryo**, **tek bir enricher**, **tek bir UI bileşeni** veya **odaklı bir güvenlik düzeltmesi** içermelidir (`< 300` satır diff).
- **Kontrat Değişiklik Protokolü:** `docs/CONTRACTS.md` dosyasını değiştiren her PR için ilgili alan sorumlularının onayı gerekir.
- Adım adım Git, lokal test ve CI hata okuma akışı için [`docs/LEARNING_HANDBOOK.md`](./LEARNING_HANDBOOK.md) Bölüm 3'ü izleyin.
