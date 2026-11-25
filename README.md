# BreachZero — Çoklu Oyunculu Pixel-Art SOC Triyaj Simülasyon Oyunu

> **"Papers, Please" × "Overcooked"** estetiğinde; üniversite siber güvenlik kulübü bünyesinde 1. sınıftan 4. sınıfa farklı deneyim seviyelerindeki öğrencilerin konu ve zorluk bazlı görevlerle birbirini bloklamadan geliştirebileceği, gerçek zamanlı ve açık kaynaklı **SOC War Room** simülasyonu.

---

## 1. Vizyon ve Temel Konsept

**BreachZero**, öğrencilere yalnızca siber güvenlik teorisi öğretmek yerine canlı bir **Security Operations Center (SOC)** nöbetinin stresini, ekip içi koordinasyonunu ve yanlış kararların kurum sağlığına etkisini oyunlaştırır:

- **Ortak Alarm Kuyruğu (*Overcooked* Etkisi):** Her takımda 2–4 analist bulunur. Takım üyeleri aynı kuyruktan alarmı **`CLAIM`** ederek üzerine alır (16×16 piksel avatarıyla kilitlenir) veya devretmek için **`RELEASE`** eder.
- **Modüler Kanıt Masası (*Papers, Please* Hissi):** Ham log tek başına aldatıcıdır. Analist masadaki araç butonlarıyla (`IP İtibar`, `Hash/VT`, `İç CMDB`, `WHOIS` vb.) kanıt toplar ve ardından **`TRUE POSITIVE - ESKALE ET`** ya da **`FALSE POSITIVE - KAPAT`** mührünü basar.
- **Anti-Exploit Puanlama & Breach Meter:** Körlemesine FP veya TP basmak matematiksel olarak cezalandırılır. Gerçek saldırıyı (TP) yanlışlıkla kapatmak **-250 puan** ve kurumun **Breach Meter** sağlığından **-30 HP** (kritik vakalarda **-40 HP**) düşürür; HP sıfırlandığında takım elenir (`BREACHED`).

---

## 2. Kilitli Görsel Tasarım Sistemi ve Canlı Vitrin

Projedeki tüm arayüzler tek bir kilitli 16-bit Retro Cyber War Room görsel sistemine bağlıdır:

- **Tasarım Kuralları ve Skill:** [`.agent/skills/pixel-soc-ui/SKILL.md`](./.agent/skills/pixel-soc-ui/SKILL.md)
- **Canlı Stil Vitrini (Tarayıcıda Doğrudan Açılabilir):** [`docs/pixel-showcase.html`](./docs/pixel-showcase.html)
- **Sprite Üretim Aracı (`NEAREST` PNG + `crispEdges` SVG fallback):** [`.agent/skills/pixel-soc-ui/scripts/render_sprite.py`](./.agent/skills/pixel-soc-ui/scripts/render_sprite.py)

---

## 3. Klasör Mimarisi

```text
BreachZero/
├── .agent/skills/pixel-soc-ui/   # Kilitli pixel-art UI skill'i ve render_sprite.py
├── docs/
│   ├── GDD.md                    # Oyun tasarımı, ekranlar, puanlama ve anti-exploit dengesi
│   ├── ARCHITECTURE.md           # FastAPI RoomManager, anti-cheat ve Cache-First mimarisi
│   ├── CONTRACTS.md              # OCSF/ECS Alert, ScenarioFile, WebSocket ve BaseEnricher kontratları
│   ├── CONTRIBUTING_TEAMS.md     # Konu & zorluk bazlı katkı alanları ve PR kuralları
│   ├── LEARNING_HANDBOOK.md      # SOC Triyaj 101, 5 güvenlik/sistem kavramı ve Git/CI rehberi
│   ├── OPEN_SOURCE_DATASETS.md   # Sigma/Mordor/abuse.ch kaynakları, Event ID tablosu ve IOC rehberi
│   ├── pixel-showcase.html       # Kilitli canlı UI stil vitrini (6 etkileşimli bölüm)
│   └── assets/sprites/           # 16x16 JSON kaynakları ve 128x128 NEAREST PNG varlıkları
├── scenarios/                    # Kod gerektirmeyen bağımsız JSON senaryo paketleri
├── scripts/
│   └── validate_scenarios.py     # Senaryo Ekibi için sıfır bağımlılıklı JSON doğrulayıcı
├── backend/                      # FastAPI + Native WebSockets + Pydantic v2 + SQLite Cache
│   ├── app/
│   │   ├── main.py
│   │   ├── models/contracts.py
│   │   ├── core/                 # scenario_loader.py, scoring.py, room_manager.py
│   │   ├── cache/                # sqlite_cache.py, prewarm.py
│   │   ├── enrichers/            # base.py, ip_reputation.py, registry.py
│   │   └── ws/router.py
│   └── tests/test_core_rules.py
└── frontend/                     # React + Vite + TypeScript + Tailwind CSS (SKILL.md kilitli)
    ├── public/sprites/           # Kilitli PNG sprite kopyaları
    └── src/
        ├── contracts/types.ts
        ├── hooks/useRoomSocket.ts
        ├── components/           # PixelShell, BreachMeter, ToolIcon, AlertQueue
        └── pages/                # HomePage (/), PlayPage (/play), HostPage (/host), AdminPage (/admin)
```

---

## 4. Hızlı Kurulum ve Çalıştırma Komutları

### A. Senaryoları Doğrulama (Kodlama Bilmeyen Senaryo Ekibi İçin)
```bash
python scripts/validate_scenarios.py
```

### B. Backend Kurulumu, Test ve Başlatma (Python 3.11+)
```bash
cd backend
pip install -r requirements.txt
python -m app.cache.prewarm --scenarios ../scenarios
pytest tests -v
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### C. Frontend Kurulumu ve Başlatma (Node 20+)
Yeni bir terminalde:
```bash
cd frontend
npm install
npm run dev -- --host
```

### D. Tarayıcıdan Oynanış Testi (LAN / Amfi Hazır)
1. Ana giriş ekranını açın: `http://localhost:5173/` (veya aynı ağdan `http://<sunucu-ip>:5173/`).
2. **`/admin`** üzerinden **Yeni Oda Oluştur** deyin; çıkan 6 haneli oda koduyla hızlı butonları kullanarak **`/host`** ve birden fazla **`/play`** sekmesi açın.
3. Aynı tarayıcıda her `/play` sekmesi `sessionStorage` ile ayrı `session_token` tutar; `F5` yenilemesinde `15s` içinde elinizdeki bilet kaybolmaz.

---

## 5. Başlangıç Dokümantasyonu ve Kulüp Katkı Özeti

| Doküman | Odak Noktası | Hedef Kitle |
| :--- | :--- | :--- |
| [`docs/GDD.md`](./docs/GDD.md) | Oyun döngüsü, Breach Meter, puanlama matematiği, V1/V2 kapsamı | Tüm ekipler & oyun tasarımcıları |
| [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) | `RoomManager`, disconnect/F5, anti-cheat sınırları, Cache-First | Core & Backend ekipleri |
| [`docs/CONTRACTS.md`](./docs/CONTRACTS.md) | Dondurulmuş JSON şemaları, WebSocket mesajları, `BaseEnricher` | Tüm geliştirici ekipler |
| [`docs/CONTRIBUTING_TEAMS.md`](./docs/CONTRIBUTING_TEAMS.md) | Çalışma alanları, etiket sistemi, PR kuralları ve yol haritası | Tüm katılımcılar & yeni üyeler |
| [`docs/LEARNING_HANDBOOK.md`](./docs/LEARNING_HANDBOOK.md) | SOC Triyaj 101, kod tabanındaki 5 güvenlik kavramı, ilk PR & CI rehberi | Projeye katılan tüm öğrenciler |
| [`docs/OPEN_SOURCE_DATASETS.md`](./docs/OPEN_SOURCE_DATASETS.md) | Sigma, Mordor, ThreatFox/MalwareBazaar rehberi & kritik Event ID tablosu | Senaryo ve Enricher geliştiricileri |
