---
name: pixel-soc-ui
description: >-
  Pixel-art UI tasarımı, retro CRT/War Room bileşenleri, ızgara kilitli SVG/PNG sprite üretimi ve görsel stil örnekleri (showcase) oluştururken kullan. Kullanıcı "pixel art", "styleguide", "UI örneği", "sprite", "avatar", "damga" veya "pixel bileşen" istediğinde aktive et.
---

# Pixel SOC UI (`pixel-soc-ui`)

Bu skill, **BreachZero** ve benzeri retro siber güvenlik / SOC arayüzleri için 16-bit Retro Cyber War Room estetiğini (*Papers, Please* + *Overcooked* birleşimi) zorunlu kılar. Modern SaaS şablonlarına kaymayı ("AI slop") engeller ve her bileşenin piksel ızgarasına sadık kalmasını sağlar.

---

## 1. Tasarım Kuralları (Anti-Slop)

- **Estetik Kimlik:** 16-bit Retro Cyber War Room (*Papers, Please* belge/damga ciddiyeti + *Overcooked* yüksek okunabilirlikli ekip/alarm enerjisi). Modern yuvarlak SaaS kartları, glassmorphism, `backdrop-filter: blur(...)`, pill butonlar ve pastel gradyanlar **kesinlikle yasaktır**.
- **Sıfır Yuvarlama:** Tüm bileşenlerde (kartlar, butonlar, rozetler, inputlar, barlar, modal ve toast'lar) `border-radius: 0` zorunludur.
- **Sert Piksel Gölgeleri & Adım Kenarlıklar:** Yumuşak blur gölge yasaktır (`box-shadow` ve `text-shadow` içinde 3. parametre/blur her zaman `0px` olmalıdır). Derinlik için yalnızca sert ofsetli piksel gölge (`box-shadow: 4px 4px 0px #070912`) ve `2px`/`4px` adım kenarlıklar (stepped pixel borders / inner bevel) kullan.
- **Piksel Keskinliği:** Tüm `<img>`, `<canvas>` ve sprite elemanlarında aşağıdaki CSS zorunludur:
  ```css
  img, canvas, .pixel-sprite {
    image-rendering: pixelated;
    image-rendering: crisp-edges;
  }
  ```
- **Adımlı Animasyonlar:** Pürüzsüz easing yerine `steps(2, end)` veya `steps(3, end)` zamanlaması ve tam sayı piksel ofsetleri kullan.
- **Fiziksel Buton Tepkisi:** Aksiyon ve damga butonları `:active` / basılma anında gölge yönünde aşağı çökmelidir (`transform: translate(4px, 4px); box-shadow: 0px 0px 0px #070912;`).
- **CRT Scanline Kuralı:** CRT scanline katmanı kullanılacaksa çizgi opaklığı en fazla `0.10` (`rgba(7, 9, 18, 0.10)`) olmalıdır; amfi/projektör ortamında moiré ve okuma sorunu oluşmaması için varsayılan olarak **kapalı** (`<body class="scanlines-off">`) gelmeli ve kullanıcı kontrolüyle isteğe bağlı açılıp kapatılabilmelidir.

---

## 2. Tipografi, Okunabilirlik ve Türkçe Karakter Ayrımı

- **Minimum Font Boyutları (Kritik):** `9px–10px` boyutunda piksel yazı **kesinlikle yasaktır**.
  - **`Press Start 2P` (`--font-display`):** En az **`11px–12px`** (tercihen `12px`, `16px`, `24px` keskin katlar).
  - **`Pixelify Sans` (`--font-tr`):** Tüm etiket, buton, rozet ve gövde metinlerinde en az **`15px–16px`**.
  - **`IBM Plex Mono` / `JetBrains Mono` (`--font-log`):** Oyuncunun hızla okuması gereken yoğun teknik metinlerde (alarm logları, IP/SHA256 IOC satırları, kanıt günlüğü çıktıları, dosya adları, HEX kodları) **`14px–15px`** ve **`line-height: 1.55`** kullan.
- **Küçük Boyutlu `Pixelify Sans` Ağırlık Kuralı:** `14px–16px` aralığındaki `Pixelify Sans` metinlerde `font-weight: 700` harflerin içini doldurup yapıştırdığı için **`font-weight: 500` veya `600`** kullan ve **`letter-spacing: 0.04em`** ekle.
- **Saf ASCII/Sayısal vs Türkçe Font Ayrımı:** `--font-display` (`Press Start 2P`) Türkçe karakterlerde fallback'e düşüp harf genişliğini bozduğu için **yalnızca saf ASCII ve sayısal** alanlarda (`BREACHZERO`, `00:25`, `#1`, `1450`, `ALT-4091`, `INC-2026-0842`) kullanılmalıdır. Türkçe karakter içeren tüm rozet, mühür, alt başlık ve etiketler (`YÜKSEK`, `GÜVENLİ`, `KANIT GÜNLÜĞÜ`, `İNCELEME BEKLİYOR`, `ESKALE EDİLDİ`) doğrudan `--font-tr` (`Pixelify Sans`) kullanmalıdır.

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&family=Pixelify+Sans:wght@400..700&family=Press+Start+2P&family=Silkscreen:wght@400;700&display=swap" rel="stylesheet">
```

```css
:root {
  --font-display: 'Press Start 2P', monospace;
  --font-tr: 'Pixelify Sans', monospace;
  --font-log: 'IBM Plex Mono', 'JetBrains Mono', monospace;
  --font-ui: 'Silkscreen', 'Pixelify Sans', monospace;
}
```

---

## 3. Kilitli Renk Paleti (Dark CRT War Room)

Tasarımda aşağıdaki palet dışına çıkma (yalnızca piksel avatar/sprite içindeki cilt ve saç gölgeleri istisnadır). Alarm ve vaka log kutularındaki ana metinlerde doğrudan `--text-primary` (`#e6ecff`) kullan:

```css
:root {
  --bg-crt: #0c0f1d;        /* Arka Plan (CRT Deep) */
  --bg-panel: #171c33;      /* Panel Yüzeyi */
  --bg-card: #232a4a;       /* İkincil Kart Yüzeyi */
  --border-light: #4b588a;  /* Kenarlık (Açık) */
  --border-shadow: #070912; /* Kenarlık (Gölge) */
  --text-primary: #e6ecff;  /* Ana Metin (Log kutuları dahil) */
  --text-secondary: #b2bfe8;/* İkincil Metin (Yüksek Kontrast) */
  --safe: #2de370;          /* FALSE POSITIVE / Güvenli (Yeşil) */
  --safe-dark: #157a3b;     /* Yeşil Koyu / Gölge */
  --threat: #ff3864;        /* TRUE POSITIVE / Tehdit / Breach (Kırmızı) */
  --threat-dark: #991636;   /* Kırmızı Koyu / Gölge */
  --warn: #ffb84d;          /* Uyarı / SLA / Claim (Kehribar) */
  --warn-dark: #9c6314;     /* Kehribar Koyu / Gölge */
  --cyan: #38d9ff;          /* Enrichment / Terminal (Camgöbeği) */
}
```

---

## 4. Özel Piksel Asset Üretim Kuralları

### A. Standart UI İkonları (Inline Piksel SVG)
- Standart UI ikonlarında `pixelarticons` (`24×24` grid) tarzı kullan.
- Inline piksel SVG çizerken **yalnızca** tam sayılı `viewBox="0 0 16 16"` veya `viewBox="0 0 24 24"` ve `shape-rendering="crispEdges"` kullan.
- `<path>`, `<circle>`, `<ellipse>`, `<polygon>`, `<polyline>` etiketleri **kesinlikle yasaktır**; pikseller yalnızca tam sayı koordinatlı `<rect x="..." y="..." width="..." height="..." fill="..." />` bloklarıyla çizilmelidir.

```xml
<svg viewBox="0 0 24 24" width="24" height="24" shape-rendering="crispEdges" aria-hidden="true">
  <rect x="4" y="3" width="16" height="2" fill="#38d9ff"/>
  <rect x="4" y="5" width="2" height="10" fill="#38d9ff"/>
  <rect x="18" y="5" width="2" height="10" fill="#38d9ff"/>
  <rect x="6" y="15" width="12" height="2" fill="#38d9ff"/>
</svg>
```

### B. PNG Sprite ve Avatar Üretimi (`render_sprite.py`)
- PNG sprite veya analist avatarı üretirken tarayıcıda veya elle çizim yerine [render_sprite.py](./scripts/render_sprite.py) aracını kullan.
- Giriş olarak `16×16` (veya `NxM`) ASCII karakter matrisi ve HEX renk paleti içeren JSON dosyası verilir; örnek format için [analyst-ali.json](./examples/analyst-ali.json) dosyasına bak.
- Ölçekleme daima `Image.Resampling.NEAREST` (`--scale 8` → `128×128`) ile şeffaf arka planlı PNG olarak yapılır.
- Pillow kurulu değilse script otomatik olarak temiz bir uyarı verip aynı matrisi `<rect>` tabanlı `crispEdges` `.svg` dosyasına dönüştürür.

```bash
python .agent/skills/pixel-soc-ui/scripts/render_sprite.py \
  --input docs/assets/sprites/sources/analyst-ali.json \
  --output docs/assets/sprites/analyst-ali.png \
  --scale 8
```

### C. Tam Sayı Sprite Ölçekleme (Mixel Önleme)
- `16×16` sprite'ları tarayıcıda **yalnızca `16`'nın tam sayı katlarında** (`16×16`, `32×32`, `48×48`, `64×64`, `80×80`, `96×96`, `128×128`) render et. Kesirli ölçekleme (ör. `24px = 1.5×` veya `40px = 2.5×`) mixel bozulmasına yol açar ve yasaktır.
- `box-sizing: border-box` uygulanan kapsayıcılarda `padding` ve `border`, iç `<img>` boyutundan kesinti yapmamalıdır (ör. `2px` padding + `2px` border varsa: `48×48` iç sprite için kapsayıcı `56×56`, `32×32` iç sprite için kapsayıcı `40×40` olmalıdır).

### D. `file://` Doğrudan Açılabilirlik Kuralı
- Statik HTML styleguide ve vitrin sayfalarında (ör. `docs/pixel-showcase.html`) yerel sunucu gerektirmemek için sprite veya JSON dosyalarını `fetch()` ile çekme; görselleri doğrudan göreceli `<img src="assets/sprites/..." alt="...">` etiketleriyle bağla.

---

## 5. Teslim Öncesi Doğrulama Kontrol Listesi

1. Tüm CSS kurallarında `border-radius` yalnızca `0` mı? (Sıfır dışı yuvarlama veya `backdrop-filter: blur` yok.)
2. Tüm `box-shadow` ve `text-shadow` tanımlarında 3. parametre (blur) `0px` mi?
3. `9px–10px` piksel yazı tamamen kaldırıldı mı? (`Press Start 2P >= 11px–12px`, `Pixelify Sans >= 15px–16px` ve `weight: 500–600`, `letter-spacing: 0.04em`.)
4. Yoğun teknik loglar, IOC satırları ve dosya adları `--font-log` (`IBM Plex Mono`, `14px–15px`, `line-height: 1.55`) ile ve yüksek kontrastla (`--text-primary`, `--text-secondary: #b2bfe8`) mı yazıldı?
5. `--font-display` (`Press Start 2P`) yalnızca saf ASCII/sayısal alanlarda kullanılıp tüm Türkçe etiket/rozet/mühürler `--font-tr` (`Pixelify Sans`) ile mi ayrıldı?
6. CRT scanline katmanı en fazla `0.10` opaklıkta ve varsayılan olarak kapalı (`scanlines-off`) mı?
7. Tüm `16×16` sprite `<img>` alanları `border`/`padding` kesintisi olmadan `16`'nın tam sayı katlarında (`32`, `48`, `80` px) ve `image-rendering: pixelated; crisp-edges;` ile mi render ediliyor?
8. Tüm inline `<svg>` etiketlerinde `shape-rendering="crispEdges"`, tam sayılı `viewBox` ve sıfır `<path>/<circle>/<ellipse>` var mı?
9. Sayfa yerel sunucu olmadan doğrudan `file://` üzerinden hatasız açılıyor mu?
