# BreachZero — Kulüp Çalışma Modeli ve 6 Haftalık Yol Haritası

Bu rehber, üniversite siber güvenlik kulübündeki 1. sınıftan 4. sınıfa kadar tüm öğrencilerin **birbirini bloklamadan**, paralel ve temiz pull request'lerle (PR) katkı verebilmesi için hazırlanmıştır.

---

## 1. Dört Bağımsız Ekip ve Sahiplik Sınırları

| Ekip | Hedef Seviye | Sahip Olduğu Klasörler | Bağımlılık & Kural |
| :--- | :--- | :--- | :--- |
| **1. Senaryo & Siber Ekibi** | 1–4. Sınıf *(Kod bilmeden katkı)* | `scenarios/*.json` | [`docs/CONTRACTS.md`](./CONTRACTS.md) `ScenarioFile` şemasına %100 uyum |
| **2. Backend & Enricher Ekibi** | 2–3. Sınıf Python | `backend/app/enrichers/`, `backend/app/cache/` | Yalnızca `BaseEnricher` arayüzünü uygular; oyun döngüsüne dokunmaz |
| **3. Frontend & Pixel UI Ekibi** | 1–4. Sınıf React/CSS | `frontend/` | [`.agent/skills/pixel-soc-ui/SKILL.md`](../.agent/skills/pixel-soc-ui/SKILL.md) ve [`docs/pixel-showcase.html`](./pixel-showcase.html) kurallarına kilitli |
| **4. Core WebSocket & Altyapı Ekibi** | 3–4. Sınıf | `backend/app/core/`, `backend/app/ws/`, CI | `RoomManager`, `asyncio.Lock`, F5 reconnect, SLA loop ve kontrat testleri |

---

## 2. Ekip Bazlı Pratik Çalışma Kuralları

### Ekip 1 — Senaryo & Siber Güvenlik Ekibi
- Her senaryo `scenarios/<case_id>.json` olarak eklenir; eklenen dosya sunucu yeniden başlatıldığında oyuna otomatik dahil olur.
- Her vaka gerçekçi ham log (`raw_log`), en az 2–3 anlamlı IOC (`indicators`) ve tüm `available_enrichers` araçları için `server_only.mock_enrichment` verisi içermelidir.
- `FP` vakaları tuzaklı ama adil olmalı (kanıtla doğrulanabilmeli); `TP` vakalarında MITRE ATT&CK tekniği ve maç sonu Türkçe `debrief_explanation` yazılmalıdır.
- Örnek şablonlar: [`scenarios/case_01_fp_backup.json`](../scenarios/case_01_fp_backup.json) ve [`scenarios/case_02_tp_kerberoast.json`](../scenarios/case_02_tp_kerberoast.json).

### Ekip 2 — Backend & Enricher Ekibi
- Yeni bir araç eklemek için yalnızca `BaseEnricher` soyut sınıfından türeyen tek bir Python dosyası yazılır (`backend/app/enrichers/<arac>.py`).
- Canlı API çağrısı yapılıyorsa `timeout_seconds = 3.0` zorunludur ve mutlaka SQLite Cache-First katmanından geçmelidir.
- Özel PNG ikonu yoksa `icon_id = "fallback-globe"` veya `"fallback-terminal"` seçilir; kendi sprite'ını çizmek isteyenler [`.agent/skills/pixel-soc-ui/scripts/render_sprite.py`](../.agent/skills/pixel-soc-ui/scripts/render_sprite.py) script'ini kullanır.

### Ekip 3 — Frontend & Pixel UI Ekibi
- **Kilitli Stil Kuralı:** Modern yuvarlak kartlar (`border-radius > 0`), blur gölgeler, `VT323` ince fontu veya `9–10px` mikro yazılar **kesinlikle yasaktır**.
- Türkçe metinler `Pixelify Sans` (`>= 15px`, `weight 500–600`, `letter-spacing: 0.04em`), yoğun loglar `IBM Plex Mono` (`14px`, `line-height: 1.55`), saf ASCII sayaç/kodlar `Press Start 2P` (`>= 11px–12px`) kullanır.
- Tüm 16×16 sprite'lar yalnızca `16`'nın tam sayı katlarında (`32×32`, `48×48`, `80×80`) render edilir.
- Oyuncu sekmesinde `session_token` mutlaka `sessionStorage` içinde tutulur; `F5` sonrası otomatik `JOIN_ROOM` ile koltuk kurtarılır.

### Ekip 4 — Core WebSocket & Altyapı Ekibi
- `public_alert` → `server_only` ayrımını bozacak hiçbir serializasyona izin vermez (otomatik sızıntı testi yazar).
- `CLAIM_ALERT` yarışı için `asyncio.Lock`, `SUBMIT_DECISION` / `RELEASE_ALERT` için `NOT_CLAIM_OWNER` kontrolü ve `ADMIN_PAUSE_WAVE` için SLA dondurma testlerini korur.

---

## 3. Git Branch ve PR Akışı

- **Branch İsimlendirme:**
  - `feat/scenario-phishing-v1`
  - `feat/enricher-whois`
  - `feat/ui-stamp-desk`
  - `feat/core-room-manager`
- **Küçük PR Kuralı:** Bir PR ideal olarak **tek bir senaryo**, **tek bir enricher** veya **tek bir UI bileşeni** içermelidir (`< 300` satır diff).
- **Kontrat Değişiklik Protokolü:** `docs/CONTRACTS.md` dosyasını değiştiren her PR için **4 ekip temsilcisinden en az 2'sinin** (Core + Frontend veya Backend + Senaryo) onayı gerekir.

---

## 4. 6 Haftalık Vize-Dayanıklı Sprint Yol Haritası

| Hafta | Dönem Durumu | Hedefler ve Teslimatlar |
| :--- | :--- | :--- |
| **Hafta 1** | Normal Ders | İskelet kurulumu: Core Pydantic modelleri, `ScenarioFile` JSON doğrulayıcı CLI, Vite + Tailwind `SKILL.md` tema tokenları, ilk 2 senaryo testi. |
| **Hafta 2** | Normal Ders | Çekirdek çalışma: `RoomManager` WebSocket döngüsü (`JOIN`, `CLAIM`, `RELEASE`, `SUBMIT_DECISION`), mock WS ile `/play` Masası ve `/host` Projektörü prototipi, ilk 6 senaryo. |
| **Hafta 3** | **Vize Haftası 1 (Tampon)** | *Bloklayıcı iş yok!* Öğrenciler yalnızca bağımsız küçük PR'lar açar: tekil senaryo JSON'ları, tekil `BaseEnricher` eklentileri (`whois`, `hash_vt`), bağımsız pixel UI bileşenleri (`BreachMeter`, `StampSeal`). |
| **Hafta 4** | **Vize Haftası 2 (Tampon)** | *Düşük yoğunluk:* Cache pre-warming CLI, `F5` `15s` reconnect + `ADMIN_PAUSE_WAVE` uçtan uca testleri, toplam 12 dengeli senaryo paketi. |
| **Hafta 5** | Final Öncesi Entegrasyon | Backend ↔ Frontend tam entegrasyon, `/admin` maç sonu debrief ekranı, kulüp içi 20 kişilik kapalı playtest ve puan/HP denge ayarı. |
| **Hafta 6** | Lansman Haftası | 80–100 eşzamanlı bağlantı yük testi, SQLite cache pre-warming, projektör kontrast kontrolü ve **Amfi Canlı Turnuvası**. |
