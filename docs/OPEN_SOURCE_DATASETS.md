# BreachZero — Açık Kaynak Tehdit İstihbaratı & Veri Seti Rehberi (`OPEN_SOURCE_DATASETS.md`)

> Bu rehber, kulüp üyelerinin **kod yazmadan** veya **Enricher eklentileri geliştirirken** gerçek SOC ortamlarına birebir benzeyen, canlı Threat Intelligence API'leriyle (VirusTotal, AbuseIPDB, RDAP) uyumlu ve adil BreachZero senaryoları üretmesi için hazırlanmıştır.

---

## 1. Neden Açık Kaynak Veri Setleri Kullanıyoruz?

Eğitim veya demo amaçlı elle uydurulan göstergeler (IOC — *Indicator of Compromise*), örneğin `a1b2c3d4e5f6...` biçimindeki sentetik SHA256 hash'leri veya rastgele seçilmiş IP adresleri, gerçek bir VirusTotal ya da AbuseIPDB sorgusunda **`404 Not Found`** veya alakasız bir sunucu kaydı döndürür.

Gerçek açık kaynak veri setlerini ve aktif tehdit akışlarını kullanarak senaryo yazdığınızda:
- Oyuncular **gerçek saldırı telemetrisi** (`Sysmon`, `Windows Security Event`, `Linux syslog/auditd`) okumayı öğrenir.
- Canlı Enricher modunda (`hash_vt`, `ip_reputation`, `whois`) sorgulanan göstergeler gerçek istihbarat skorlarıyla eşleşir.
- **False Positive (FP)** vakaları yalnızca "her şey temiz" kolaylığında değil, gerçek SOC'larda analistleri en çok yanıltan gürültülü kurumsal kalıplardan (`Sigma falsepositives:`) doğar.

---

## 2. Önerilen Açık Kaynak Kaynaklar

| Kaynak | URL / Repo | Ne Sağlar? | BreachZero Hedef Alanı |
| :--- | :--- | :--- | :--- |
| **OTRF Security Datasets (Mordor)** | `https://github.com/OTRF/Security-Datasets` | Gerçek saldırı simülasyonlarından (Atomic Red Team vb.) kaydedilmiş Windows Sysmon, Security EventLog ve Linux logları + MITRE etiketleri | `public_alert.raw_log`, `process`, `server_only.mitre_attack` |
| **Splunk Attack Data** | `https://github.com/splunk/attack_data` | Gerçek endpoint/AD/Linux saldırı telemetri ham log arşivleri | `public_alert.raw_log`, `source`, `destination`, `process` |
| **abuse.ch — ThreatFox** | `https://threatfox.abuse.ch/` | Güncel C2 IP:port, zararlı domain ve URL göstergeleri (ücretsiz JSON API) | `public_alert.indicators.ips`, `domains` |
| **abuse.ch — MalwareBazaar** | `https://bazaar.abuse.ch/` | Güncel zararlı dosyaların gerçek SHA256/MD5 hash'leri, dosya adları ve zararlı aile etiketleri | `public_alert.file.sha256`, `indicators.hashes` |
| **abuse.ch — URLhaus** | `https://urlhaus.abuse.ch/` | Aktif zararlı payload dağıtım URL'leri | `public_alert.process.command_line`, `raw_log` |
| **SigmaHQ (`SigmaHQ/sigma`)** | `https://github.com/SigmaHQ/sigma` | Platform bağımsız tespit kuralları ve her kuralın içinde yer alan **`falsepositives:`** listesi | Senaryo fikri, FP tuzağı tasarımı, `mitre_attack` |
| **Splunk BOTS (Boss of the SOC)** | `https://github.com/splunk/botsv3` | Gerçekçi kurumsal arka plan trafiği, HTTP/DNS/Firewall/Endpoint karışık olay zincirleri | Çok aşamalı `raw_log` ve gürültülü kurumsal ortam kurgusu |
| **Temiz Sistem Hash'leri (Windows / Sysinternals / NSRL)** | `https://learn.microsoft.com/sysinternals/` & NIST NSRL | İmzalı meşru Windows, Sysinternals veya açık kaynak ikili dosyaların gerçek SHA256 hash'leri | **FP senaryolarında** VirusTotal'da gerçek `0/72` temiz sonucu görmek için |

---

## 3. Gerçek Sigma Kuralı Okuma Örneği (YAML → FP Senaryosu Çıkarma)

Bir SOC analisti yalnızca "kötücül" kalıpları değil, o kalıbın **ne zaman masum (False Positive)** olabileceğini bilmelidir. SigmaHQ kurallarındaki `falsepositives:` bloğu bunun için altın madendir.

Örnek bir Sigma kuralı kesiti (PowerShell ile yürütme politikası atlatma):

```yaml
title: PowerShell Execution Policy Bypass
id: 9c8f1a2d-4b5e-4c7a-8e1f-2a3b4c5d6e7f
status: stable
description: Detects powershell.exe invoked with -ExecutionPolicy Bypass or -ep bypass
logsource:
  category: process_creation
  product: windows
detection:
  selection_img:
    Image|endswith: '\powershell.exe'
  selection_flags:
    CommandLine|contains:
      - '-ExecutionPolicy Bypass'
      - '-ep bypass'
  condition: selection_img and selection_flags
falsepositives:
  - Legitimate administrative scripts and software deployment tools (SCCM, Intune, Ansible)
  - Enterprise backup agents running pre/post snapshot hooks
level: medium
tags:
  - attack.execution
  - attack.t1059.001
```

### Bir Analist Bu Kuralı BreachZero Senaryosuna Nasıl Çevirir?
1. **`detection` bloğu** sana saldırı/alarm tetikleyicisini verir: `powershell.exe -ExecutionPolicy Bypass ...`. Ham bakıldığında tehlikelidir (`HIGH` / `MEDIUM`).
2. **`falsepositives:` bloğu** sana adil bir FP senaryosu verir: *"Kurumsal yedekleme ajanı (`Veeam.Backup.Service.exe`) veya EDR/SCCM güncelleme betiği."*
3. Oyuncuya yalnızca komut satırını gösterirsen kör tahmin yaptırmış olursun; bunun yerine **`internal_cmdb`** kanıtına *"Onaylı bakım penceresi / `CHG-2026-xxxx` değişiklik bileti"* bilgisini ve **`hash_vt`** kanıtına gerçek imzalı temiz bir ikili dosya hash'ini (`0/72`) koyarsın. Böylece kanıt toplayan analist haklı olarak `FALSE POSITIVE`, kanıtsız "PowerShell bypass gördüm!" diye atlayan analist ise haksız `TP` (yanlış alarm cezası `-80` puan) alır.

---

## 4. Kritik Log & Event ID Hızlı Başvuru Tablosu

| Platform & Event ID / Kaynak | Ne Kaydeder? | Hangi Saldırı Tekniğini (MITRE) Ele Verir? | Normalde Neyle Karışır (FP Tuzağı)? |
| :--- | :--- | :--- | :--- |
| **Windows Event `4624` / `4625`** | Başarılı (`4624`) / Başarısız (`4625`) oturum açma; `LogonType` (`3`: ağ, `10`: RDP), kaynak IP, hedef hesap | Brute Force (`T1110`), Password Spraying (`T1110.003`), Pass-the-Hash / Yetkisiz Yatay Hareket (`T1021`) | Kullanıcının şifre değiştirdikten sonra eski önbellekli telefon/Outlook oturumunun `4625` üretmesi veya servis hesabı yanlış şifresi |
| **Windows Event `4688`** | Yeni süreç başlatma (`NewProcessName`, `ParentProcessName`, `CommandLine` — audit açıksa) | Living-off-the-Land / LOLBins (`T1059.001` PowerShell, `T1218` mshta/rundll32) | BT otomasyonu (SCCM, GPO logon script, Veeam/EDR bakım betikleri) |
| **Windows Event `4769`** | Active Directory Domain Controller üzerinde **Kerberos Service Ticket (TGS)** talebi ve şifreleme türü (`TicketEncryptionType`) | **Kerberoasting (`T1558.003`)** — Normal kurumsal AD ortamında **AES (`0x11` / `0x12`)** kullanılırken saldırgan kırmak için zayıf **RC4 (`0x17`)** şifrelemeye düşürür (downgrade) ve kısa sürede onlarca farklı SPN için TGS ister | Çok eski (legacy) Windows/Linux sistemleri veya yanlış yapılandırılmış MSSQL/IIS servis hesaplarının tekil `0x17` RC4 TGS talebi |
| **Sysmon Event `1`** | Süreç oluşturma; `Image`, `ParentImage`, `CommandLine`, `CurrentDirectory` ve **SHA256 `Hashes`** | Phishing sonrası Ofis → Kabuk zinciri (`WINWORD.EXE -> cmd.exe` — `T1566.001`, `T1204`), `AppData\Temp` ikili çalıştırma (`T1036` Masquerading) | Yazılım güncelleyicilerin (`Teams`, `Chrome`, `Zoom` updater) kullanıcı `AppData\Local` altından imzalı geçici ikili çalıştırması |
| **Sysmon Event `3`** | Sürecin başlattığı ağ bağlantısı (`Image`, `SourceIp`, `DestinationIp`, `DestinationPort`) | Dış C2 Beacon / Komuta-Kontrol (`T1071.001`), ters kabuk (`4444/TCP`, `8443/TCP`), veri sızdırma (`T1041`) | EDR/Antivirüs bulut telemetrisi, CDN (`443/TCP`) veya geliştiricilerin `npm`/`pip`/`curl` paket indirmeleri |
| **Sysmon Event `10`** | Bir sürecin başka bir sürecin belleğine erişmesi (`SourceImage`, `TargetImage`, `GrantedAccess`) | **`TargetImage: ...\lsass.exe`** + yüksek erişim maskesi (`0x1010`, `0x1FFFFF`, `0x1410`) → Bellekten kimlik bilgisi dökümü (**`T1003.001` LSASS Dump / Mimikatz**) | Windows Defender / kurumsal EDR sensörlerinin (`MsMpEng.exe`, `csfalcon.exe`) veya Task Manager/Process Explorer'ın rutin düşük yetkili (`0x1000` / `0x0400`) bellek denetimi |
| **Linux `/var/log/auth.log`** | SSH oturum denemeleri (`Failed password`, `Accepted publickey`), `sudo` komutları, `su` geçişleri | SSH Brute Force (`T1110`), çalıntı SSH anahtarıyla sızma (`T1078`), `sudo` yetki yükseltme (`T1548.003`) | CI/CD (Jenkins/GitLab Runner) veya Ansible otomasyon hesaplarının belirli bir bastion IP'den otomatik SSH anahtarıyla bağlanması |
| **Linux `cron` (`/var/log/syslog` CRON, `/etc/crontab`, `/var/spool/cron/`)** | Zamanlanmış görevlerin tetiklenme zamanı, kullanıcı adı ve çalıştırılan komut | **Scheduled Task/Job Persistence (`T1053.003`)** — `/tmp` veya gizli dizinden `@reboot` / her dakika çalışan arka kapı | Sistem bakım görevleri (`logrotate`, `certbot renew`, onaylı `rsync` veritabanı yedekleme cron'ları) |
| **Linux Şüpheli `curl \| bash` / `wget -qO- \| sh`** | Auditd/bash history/EDR süreç logunda uzaktan indirilen betiği diske yazmadan kabuğa aktarma | Command & Scripting Interpreter (`T1059.004`) + Ingress Tool Transfer (`T1105`) — Tek satırlık drop & beacon | Geliştirici makinelerinde resmi dokümandan `Homebrew`, `nvm`, `rustup` veya `Docker` kurulum scripti çalıştırılması |

---

## 5. Threat Intelligence & Skor Okuma Rehberi

Canlı API'lerden (veya mock karşılıklarından) gelen veriyi yorumlarken şu 4 analist kuralını uygulayın:

1. **VirusTotal Tespit Oranı (`X/72`) Tek Başına Kanıt Değildir:**
   - **`1/72` – `3/72` (özellikle "Generic", "Heuristic", "AI.Suspicious"):** Çoğunlukla imzasız yeni derlenmiş bir betik veya yönetici aracında çıkan **Heuristic False Positive**'dir. Mutlaka dijital imza (`signer`), dosya yolu ve `first_seen` tarihine bakılır.
   - **`30/72` – `65/72` (bilinen aile adlarıyla, örn. `Trojan.Sliver`, `AgentTesla`):** Çoklu motor konsensüsüdür; yüksek güvenle kötücül (`MALICIOUS`) değerlendirilir.
   - **FP senaryosu için `0/72`:** Temiz Windows/Sysinternals ikili hash'i kullanırsanız canlı VT sorgusu gerçek `0/72` ve Microsoft/kurumsal imza bilgisini döner.

2. **AbuseIPDB Güven Skoru (`abuseConfidenceScore`) & Rapor Sayısı:**
   - `%100` skor ama **yalnızca 1–2 rapor** → yeni veya yanlış raporlanmış tekil bir IP olabilir (`SUSPICIOUS`).
   - `%95+` skor ve **yüzlerce farklı kullanıcıdan (`numDistinctUsers`) rapor** → aktif C2, botnet veya tarayıcı (`MALICIOUS`).
   - Tor çıkış düğümü (`185.220.101.0/24` gibi) veya paylaşımlı bulut VPS IP'si kurumsal sunucunun **dışarı doğru (`outbound`)** `4444/TCP` bağlandığı bir logda görünüyorsa çok daha kritiktir; buna karşılık halka açık web sunucusuna **içeri doğru (`inbound`)** gelen tekil tarama paketleri çoğu zaman arka plan internet gürültüsüdür.

3. **RFC1918 Özel IP Kuralı (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`):**
   - Bu adresler yalnızca yerel kurum ağı içinde anlamlıdır; **dış itibar API'lerine (AbuseIPDB, VirusTotal, RDAP) ASLA gönderilmemelidir**.
   - Sebepleri: (a) Kurum içi ağ topolojisi/IP şeması 3. partiye sızdırılmaz, (b) Global itibar veritabanında anlamlı kayıt yoktur, (c) Günlük API kotasını boşa harcar. BreachZero içinde `IpReputationEnricher` bu adresleri lokal yakalayıp `INFO` kartı döner.

4. **IOC Defanging Kuralı (Tıklanabilir Tehlikeyi Önleme):**
   - **Dokümanlarda, GitHub Issue/PR açıklamalarında ve sohbet kanallarında** gerçek zararlı URL, domain veya C2 IP'leri yanlışlıkla tıklanıp zararlı indirmemesi için **defang** edilir:
     - `http://evil.example.com/payload.exe` → `hxxp://evil[.]example[.]com/payload.exe`
     - `185.220.101.44` → `185[.]220[.]101[.]44`
   - **Buna karşılık**, doğrudan Python/API tarafından okunan **`scenarios/*.json`** içindeki `indicators` ve `raw_log` alanlarında ayrıştırıcıların bozulmaması için standart ham format (`185.220.101.44`) kullanılır.

---

## 6. Adım Adım Senaryo Üretim İş Akışı (5 Adım)

1. **Adım 1 — Ham Log Kalıbı Seçimi:**
   - Saldırı vakası (TP) için **OTRF Security Datasets** veya **Splunk Attack Data** üzerinden gerçek bir saldırı logu seçin; FP vakası için **SigmaHQ**'daki ilgili kuralın `falsepositives:` maddesini seçin.
2. **Adım 2 — Güncel Gerçek IOC Yerleştirme:**
   - TP için **ThreatFox / MalwareBazaar** üzerinden son 7 gün içindeki aktif bir C2 IP ve zararlı SHA256 hash'i alın (veya `scripts/fetch_ioc_seed.py` CLI aracıyla taslak çekin).
   - FP için Windows/Sysinternals veya meşru imzalı bir aracın gerçek temiz SHA256 hash'ini alın.
3. **Adım 3 — Şirket İçi `internal_cmdb` Hikayesi Giydirme:**
   - Rastgele IP/host yerine BreachZero evrenine uygun mantıklı varlık ve kullanıcı bağlamı kurun (`BACKUP-SRV-01`, `FIN-DB-02`, `e.demir_stajyer`, `CHG-2026-...` onaylı bakım penceresi veya `Tier-0 Domain Controller`).
4. **Adım 4 — `mock_enrichment` Snapshot Alma:**
   - Senaryo ister offline amfi modunda ister canlı API çöktüğünde çalışsın, oyunun bozulmaması için `available_enrichers` listesindeki **her araç** için `server_only.mock_enrichment` içine gerçekçi özet ve `verdict_signal` snapshot'ı yazın.
   - Tüm `ground_truth`, `mitre_attack`, `hp_penalty_on_miss` ve Türkçe `debrief_explanation` alanlarını **yalnızca `server_only`** içine koyun.
5. **Adım 5 — Lokal Doğrulama ve PR Açma:**
   - Komutu çalıştırın ve tüm dosyaların `[OK]` verdiğini görün:
     ```bash
     python scripts/validate_scenarios.py
     ```
   - `git checkout -b feat/scenario-<vaka-adi>` açıp yalnızca yeni JSON dosyanızla PR gönderin.

---

## 7. İki Kritik Tuzak ve Etik / Güvenlik Kuralı

> [!WARNING]
> **Tuzak 1 — IOC Çürümesi (Aging):**
> Açık kaynak veri setlerindeki 2–3 yıl öncesine ait bir C2 IP'si bugün temiz bir bulut müşterisine yeniden atanmış olabilir; eski bir zararlı URL'si kapanıp `404` dönebilir. Bu yüzden canlı API uyumu için **son günlere ait ThreatFox/MalwareBazaar IOC'leri** seçilmeli, turnuva öncesinde **`python -m app.cache.prewarm`** ile SQLite önbellek ısıtılmalı ve her senaryoda güncel **`mock_enrichment` fallback** snapshot'ı tutulmalıdır.

> [!CAUTION]
> **Kural 2 — Telif, Kişisel Veri (PII) ve Canlı Zararlı Yasağı:**
> - Repoya **ASLA** gerçek bir şirketin/kişinin özel logu, gerçek e-posta adresi, parola, API anahtarı veya gerçek çalışan adı (`PII`) eklenmez — tüm host/kullanıcı adları anonimleştirilir.
> - MalwareBazaar/URLhaus üzerinden indirilebilen **canlı zararlı ikili dosyalar (`.exe`, `.dll`, `.ps1` payloadları) repoya ASLA yüklenmez**; yalnızca SHA256 hash, C2 IP/domain ve metin tabanlı log satırı kullanılır.

---

## 8. Örnek Dönüşüm Haritası (Sigma / Mordor → `CONTRACTS.md`)

Aşağıdaki tablo, Sysmon Event `1` + Mordor/ThreatFox çıktısının [`docs/CONTRACTS.md`](./CONTRACTS.md) içindeki `ScenarioFile` alanlarına nasıl aktarıldığını özetler:

| Kaynak Olay Alanı (Sysmon / Sigma / Intel) | BreachZero `ScenarioFile` Alanı | Örnek Değer |
| :--- | :--- | :--- |
| `UtcTime` | `public_alert.timestamp_utc` | `"2026-11-25T11:42:08Z"` |
| `SourceIp` / `Computer` | `public_alert.source` & `public_alert.host` | `ip: "10.10.22.45"`, `hostname: "WKSTN-STAJYER-04"` |
| `DestinationIp` / `DestinationPort` | `public_alert.destination` | `ip: "185.220.101.44"`, `port: 4444` |
| `User` (anonimleştirilmiş) | `public_alert.user` | `name: "e.demir_stajyer"`, `department: "Yazılım Stajyeri"` |
| `Image`, `ParentImage`, `CommandLine` | `public_alert.process` | `name`, `parent_name`, `command_line` |
| `Hashes.SHA256` (MalwareBazaar/NSRL) | `public_alert.file.sha256` & `indicators.hashes` | Gerçek 64 karakterlik hex SHA256 |
| Tüm çıkarılan IP / Hash / Domain / User / Host | `public_alert.indicators` | Enricher'ların hedefleyeceği tekil listeler |
| Olay özeti tek satır (ECS/Sysmon tarzı) | `public_alert.raw_log` | Terminal ekranında `IBM Plex Mono` ile gösterilecek log |
| Analist kararı (`TP` / `FP`) & Risk | `server_only.ground_truth` & `hp_penalty_on_miss` | `"TP"` / `40` (veya `"FP"` / `0`) |
| Sigma `tags: attack.tXXXX` | `server_only.mitre_attack` | `["T1566.001", "T1059.001"]` |
| Maç sonu eğitim açıklaması | `server_only.debrief_explanation` | Analistin hangi kanıtlarla sonuca varması gerektiğini açıklayan Türkçe metin |
