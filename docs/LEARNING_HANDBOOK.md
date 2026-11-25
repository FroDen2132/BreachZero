# BreachZero — Teknik Öğrenme El Kitabı (`LEARNING_HANDBOOK.md`)

> Bu el kitabı, BreachZero üzerinde çalışırken yalnızca "bir ticket kapatmayı" değil; gerçek bir **Security Operations Center (SOC)** analisti ve **güvenlik odaklı yazılım mühendisi** gibi düşünmeyi öğrenmeniz için hazırlanmıştır. Repoda ilk 1–2 Issue'yu çözerken aşağıdaki pratikleri doğrudan üretim kodunda deneyimleyeceksiniz.

---

## Bölüm 1: SOC Triyaj 101 (60 Saniyede Alarm Okuma)

Gerçek bir SOC'ta bir analistin her alarm için 20 dakikası yoktur. İlk **60 saniyede** eldeki ham logu bağlamla birleştirip doğru soruları sorması gerekir.

### 1.1 TP / FP / FN / TN Karar Matrisi

| Gerçek Durum \ Analist Kararı | **TRUE POSITIVE (Eskale Et)** | **FALSE POSITIVE (Kapat)** |
| :--- | :--- | :--- |
| **Gerçek Saldırı (`TP`)** | **Doğru Tespit (TP):** Tehdit yakalandı (`+150/+200` puan, seri devam eder) | **Kritik Hata — False Negative (FN):** Saldırgan içeride kaldı (`-250` puan, `-30` / `-40 HP` → takım **BREACHED** olabilir) |
| **Masum / Planlı İşlem (`FP`)** | **Yanlış Alarm — False Positive (FP):** Ekibin zamanını yaktı, *alert fatigue* yarattı (`-80` puan, seri sıfırlanır) | **Doğru Kapatma (TN):** Gürültü temizlendi (`+100/+140` puan, seri devam eder) |

- **Neden FN Şirketi Batırır?** Tek bir gözden kaçan Kerberoasting veya C2 vakası, Domain Admin yetkisi ve fidye yazılımı (*ransomware*) demektir. BreachZero'da Breach Meter (`100 HP`) doğrudan bunu modeller.
- **Neden Aşırı FP Analist Körlüğü (*Alert Fatigue*) Yaratır?** Korkudan her şeye "Saldırı!" demek çözüm değildir; üst yönetime ve seviye-2 ekibine sürekli yanlış alarm eskalasyonu yapan analist güvenilirliğini yitirir ve gerçek saldırı gürültü içinde boğulur.

### 1.2 60 Saniyelik Triyaj Kontrol Listesi

1. **Zaman ve Değişiklik Penceresi:** Olay gece `03:15` yedekleme saatinde mi, yoksa öğlen `11:42` mesai ortasında mı gerçekleşti? `internal_cmdb` üzerinde onaylı bir değişiklik bileti (`CHG-...`) var mı?
2. **Parent → Child Süreç Ağacı (*En Güçlü Sinyal*):** Kim kimi başlattı?
   ```text
   [MASUM YEDEKLEME KALIBI — case_01]
   Veeam.Backup.Service.exe
     └── powershell.exe -File C:\ProgramData\Veeam\Scripts\NightlyDbSnapshot.ps1

   [ŞÜPHELİ PHISHING / İSTİSMAR KALIBI — case_02 / Phishing]
   WINWORD.EXE  (veya beklenmedik cmd/powershell)
     └── powershell.exe
           └── C:\Users\e.demir_stajyer\AppData\Local\Temp\svchost_upd.exe --roast-rc4 --c2 ...
   ```
   - `Word`, `Excel`, `Outlook` veya tarayıcının doğrudan `powershell.exe` / `cmd.exe` doğurması neredeyse her zaman alarm sebebidir.
   - Meşru Windows `svchost.exe` her zaman `C:\Windows\System32\` altında ve `services.exe` altından çalışır; **`AppData\Local\Temp`** içinden çalışan `svchost_upd.exe` açık bir **Masquerading (`T1036`)** göstergesidir.
3. **Dosya İmzası ve Hash (`hash_vt`):** Betik veya ikili dosya şirket içi PKI / Microsoft imzalı mı (`0/72`), yoksa imzasız ve yüksek tespit oranlı (`47/72`) mı?
4. **Ağ Hedefi ve Port (`ip_reputation`, `whois`):** Dahili sunucudan dahili veritabanına bilinen `445/SMB` replikasyonu mu, yoksa bir kullanıcı istasyonundan anonim dış IP'ye `4444/TCP` giden beacon mı?
5. **Kullanıcı Rolü ve Hedef Kritikliği (`internal_cmdb`):** Bir stajyer hesabının (`e.demir_stajyer`) **Tier-0 Domain Controller (`AD-DC-01`)** üzerinde toplu `RC4 (0x17)` TGS istemesi hiçbir meşru iş akışıyla açıklanamaz.

---

## Bölüm 2: Bu Kod Tabanındaki 5 Gerçek Güvenlik & Sistem Mühendisliği Kavramı

BreachZero sadece siber güvenlik oyunu değildir; arka ucu ve ön yüzü aynı zamanda gerçek dünya yazılım güvenliği prensiplerinin canlı bir laboratuvarıdır:

### 1. Server-Authoritative Anti-Cheat (`PublicAlert` vs `server_only`)
- **Nedir?** Çok oyunculu veya hassas sistemlerde doğru cevabı, puan kurallarını ve gizli veriyi yalnızca sunucunun bilmesi; istemciye (tarayıcıya) asla ham modelin tamamının gönderilmemesidir.
- **Kötü Yapılırsa Nasıl İstismar Edilir?** Eğer API bütün `ScenarioFile` JSON'unu tarayıcıya yollayıp `ground_truth`'ı sadece React arayüzünde gizleseydi, herhangi bir öğrenci `F12 DevTools → Network / WS` sekmesini açıp cevabı `TP` / `FP` olarak anında okuyabilirdi.
- **BreachZero'da Nerede Görürsün?**
  - [`backend/app/models/contracts.py`](../backend/app/models/contracts.py): `PublicAlert` (`extra="forbid"`) ile `ScenarioServerOnly` kesin çizgiyle ayrılmıştır.
  - [`backend/app/core/room_manager.py`](../backend/app/core/room_manager.py): `TeamAlertState.to_public_alert()` ve `build_room_state_payload()` yalnızca `public_alert` alanlarını serileştirir; maç bitene (`ADMIN_END_MATCH` → `MATCH_DEBRIEF`) kadar hiçbir `server_only` alanı dışarı çıkmaz.
  - [`backend/tests/test_core_rules.py`](../backend/tests/test_core_rules.py): `test_zero_server_only_leakage_across_rest_and_ws` testi REST ve WebSocket çıktılarında bu kelimelerin sızmadığını otomatik doğrular.

### 2. Race Condition & TOCTOU (`asyncio.Lock`)
- **Nedir?** İki eşzamanlı isteğin paylaşılan bir durumu okuyup (*Time-of-Check*) güncelleme yapana kadar geçen sürede (*Time-of-Use*) durumun değişmesiyle oluşan yarış koşuludur (**TOCTOU**).
- **Kötü Yapılırsa Nasıl İstismar Edilir?**
  - İki takım arkadaşı aynı milisaniyede `CLAIM_ALERT` gönderirse ikisi de bileti almış sanabilir.
  - Aynı kullanıcı WS konsolundan milisaniyeler içinde iki kez `SUBMIT_DECISION` basarsa ikisinden de `+150` puan kazanabilir (veya çift `-40 HP` yer).
  - Bir işlem dış HTTP çağrısı yaparken kilit bırakılırsa (`await registry.execute(...)`), o arada bilet kapatılmış (`RESOLVED`) veya takım elenmiş (`BREACHED`) olabilir ya da ikinci paralel istek harici API'ye çift istek fırlatır.
- **BreachZero'da Nerede Görürsün?**
  - [`backend/app/core/room_manager.py`](../backend/app/core/room_manager.py): `claim_alert` ve `submit_decision` tamamen `async with room.lock:` içinde atomik çalışır. Buna karşılık `run_enricher` (`L478–516`) dış ağ çağrısını kilitsiz yaptığı için **in-flight kilidi** ve **ikinci kilit bloğunda durum tekrar kontrolü** iyileştirmeye açık gerçek bir mühendislik noktasıdır.

### 3. Cache-First & API Rate-Limit Kalkanı
- **Nedir?** Dış tehdit istihbaratı servislerinin sıkı ücretsiz kota sınırlarını (örneğin VirusTotal: **4 istek/dakika, 500 istek/gün**; AbuseIPDB: 1000 istek/gün) aşmamak için sorgu sonuçlarını kalıcı yerel önbellekte tutup dış API'ye yalnızca eksik/bayat kayıtlarda gitmektir.
- **Kötü Yapılırsa Nasıl İstismar Edilir?** Amfide 50 öğrenci aynı anda `[HASH / VT]` butonuna bastığında önlem yoksa saniyeler içinde `429 Too Many Requests` alınır ve tüm salonun oyunu kilitlenir.
- **BreachZero'da Nerede Görürsün?**
  - [`backend/app/cache/sqlite_cache.py`](../backend/app/cache/sqlite_cache.py): TTL tabanlı kalıcı SQLite cache katmanı.
  - [`backend/app/cache/prewarm.py`](../backend/app/cache/prewarm.py) & [`backend/app/enrichers/registry.py`](../backend/app/enrichers/registry.py): Turnuva öncesi önbellek ısıtma ve `Cache → Canlı API → Mock Fallback` mimarisi.

### 4. Timing Attack (`!=` vs `secrets.compare_digest`)
- **Nedir?** İki gizli token'ı standart `==` / `!=` operatörüyle karşılaştırmak ilk farklı karakterde erken dönüş yapar. Teorik saldırgan, yanıt süresindeki nanosaniye/mikrosaniye farklarını ölçerek token'ı byte byte tahmin edebilir.
- **Kötü Yapılırsa Nasıl İstismar Edilir?** Gizli oturum/admin anahtarlarında zamanlama yan kanalı (*timing side-channel*) oluşur; bu nedenle kriptografik token doğrulamasında her zaman sabit zamanlı (*constant-time*) karşılaştırma standarttır.
- **BreachZero'da Nerede Görürsün?**
  - [`backend/app/core/room_manager.py`](../backend/app/core/room_manager.py): `join_room` ve `admin_*` metodlarında `admin_token != room.admin_token` kontrolleri bulunur; bunu `secrets.compare_digest(admin_token or "", room.admin_token)` ile değiştirmek temiz bir güvenlik sertleştirmesidir.

### 5. Input Validation & Bellek/Kota DoS
- **Nedir?** İstemciden gelen her REST JSON gövdesinin ve WebSocket payload'ının tip, uzunluk, eleman sayısı ve izinli değer kümesi (*allowlist*) açısından sınırlandırılmasıdır.
- **Kötü Yapılırsa Nasıl İstismar Edilir?**
  - `POST /api/rooms` ucuna 5000 karakterlik 50 takım adı göndererek veya art arda 10.000 oda açarak sunucu belleğini tüketmek (**Memory DoS**).
  - `RUN_ENRICHER` paketinde `ioc_value` alanını DevTools'tan değiştirip senaryoda olmayan yüzlerce rastgele IP/hash yollayarak sunucunun VirusTotal/AbuseIPDB API kotasını tüketmek (**Quota Exhaustion**).
- **BreachZero'da Nerede Görürsün?**
  - [`backend/app/models/contracts.py`](../backend/app/models/contracts.py) (`CreateRoomRequest`), [`backend/app/ws/router.py`](../backend/app/ws/router.py) ve [`backend/app/core/room_manager.py`](../backend/app/core/room_manager.py) (`create_room`, `join_room`, `run_enricher`).

---

## Bölüm 3: İlk Kez Açık Kaynak PR Açacaklar İçin Git & CI Rehberi

`main` dalı **Branch Protection** ile korunmaktadır (doğrudan `main`'e push kapalıdır, her değişiklik Pull Request + yeşil CI gerektirir).

### 1. Görev Seçimi ve Klonlama
GitHub **Issues** sekmesinden ilgi alanına (`scenario`, `backend`, `enricher`, `frontend`, `pixel-art`, `security`) ve seviyene (`seviye:baslangic`, `seviye:orta`, `seviye:ileri`) göre bir Issue seç, altına *"Bunu üstleniyorum"* yorumu bırak. Ardından repoyu klonla ve yeni branch aç:
```bash
git clone https://github.com/FroDen2132/BreachZero.git
cd BreachZero
git checkout -b feat/kisa-gorev-adi
```

### 2. Lokalde Değişiklik Yap ve İlgili Testi Koş
Değişiklik yaptığın alana göre PR açmadan önce lokalde şu komutları çalıştır:

- **Senaryo eklediysen/düzenlediysen:**
  ```bash
  python scripts/validate_scenarios.py
  ```
- **Backend / Enricher / Güvenlik düzenlediysen:**
  ```bash
  pytest backend/tests -v
  ```
- **Frontend / Pixel-Art düzenlediysen:**
  ```bash
  cd frontend
  npm ci
  npm run build
  ```

### 3. Commit, Push ve Pull Request Açma
```bash
git status
git add <degistirdigin-dosyalar>
git commit -m "feat: <ne yaptigini aciklayan kisa mesaj>"
git push -u origin feat/kisa-gorev-adi
```
GitHub'da **Compare & pull request** butonuna bas, PR şablonunu doldur ve özet kısmına çözdüğün Issue numarasını yaz (örneğin `Closes #4` — PR merge edildiğinde Issue otomatik kapanır).

### 4. GitHub Actions CI Kırmızı Yanarsa Ne Yapmalı?
PR açıldığında 3 kontrol otomatik çalışır:
1. `Senaryo JSON & Spoiler Doğrulama`
2. `Backend Testleri (Pytest)`
3. `Frontend Build (TypeScript + Vite)`

Birisi kırmızı (`X`) yanarsa panik yapma:
1. PR sayfasının altındaki başarısız check'in yanındaki **Details** linkine tıkla ve hata satırını oku (ör. eksik TypeScript tipi, kırık JSON virgülü veya `server_only` dışı spoiler).
2. Hatayı kendi bilgisayarında düzelt, yukarıdaki lokal komutu tekrar çalıştır.
3. Aynı branch'e yeni bir commit atıp `git push` yap — açtığın PR ve CI otomatik yeniden çalışır.
