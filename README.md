# NBA Fantasy

14 takımlı, 9 kategorili Yahoo NBA Fantasy ligi için Bayesian oyuncu tahminleri,
günlük kadro değerlendirmesi ve add/drop karar desteği.

**Normal sezon hedefi:**

\[
U=\sum_{c=1}^{9}\left[P(\text{kategori galibiyeti})
+\tfrac12P(\text{kategori beraberliği})\right].
\]

8–1 sonucu 5–4'ten, 4–5 sonucu 1–8'den daha değerlidir. Haftalık eşleşme
galibiyeti ana hedef değildir; haftalık W/L/D ikincil bir rapor metriğidir.
Kategori sıralamasındaki ilk sekiz takım playoff'a katılır. Playoff hedefi ve
beraberlik bozma kuralı ayrıca yapılandırılır.

## Kurulum ve kullanım

Python 3.11 veya üzeri, proje kök dizininde:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -t . -p "test_*.py"
node --test tests/yahoo_fixtures.test.cjs tests/yahoo_fixture_capture.test.cjs tests/report_panel.test.cjs
.\.venv\Scripts\python.exe -m ruff check src tests
.\.venv\Scripts\python.exe -m ruff format --check src tests
```

Ortak yerel paneli açmak için:

```powershell
.\.venv\Scripts\python.exe -m src.report_panel
```

Bu komut ana rapor/Excel ekranını, Yahoo köprüsünü ve mevcut takas panelini
birlikte başlatır. Yahoo Matchup sayfasındaki yer imi kullanılmaya devam eder.
Kullanım ve Telegram ayarları: [Yerel panel](docs/LOCAL_PANEL.md).

**Yerel önbelleklerden rapor üretmek** ağ erişimi veya bildirim gönderimi yapmaz:

```powershell
.\.venv\Scripts\python.exe -m src.forecast
```

Çıktılar: `reports/latest_cloud_summary.md` ve `reports/latest_forecast.json`.
Ana rapor, doğrulanmış Yahoo fikstürü varsa kalan tam normal sezon haftalarını
gerçek rakiplere göre de değerlendirir. Kaynak ve kurulum:
[Fantasy fikstürü](docs/FANTASY_CALENDAR.md).
Geçerli canlı skor yoksa yalnızca kalan maçlar gösterilir; hafta içi add/drop
önerileri bekletilir. Rapor üretmek Yahoo senkronizasyonu yapmak değildir.

Takas modülü güncel Yahoo tekliflerini ana rapor ve bildirimlerde değerlendirir;
gerçek puan durumu ve kalan fikstür tam olduğunda playoff katılım etkisini ekler.
Geniş fırsat taraması ayrı ve isteğe bağlıdır: [Aşama 0–5 ve çalışma periyodu](docs/TRADES.md).

Canlı veri ve hesap bağlantıları:

```powershell
.\.venv\Scripts\python.exe -m src.yahoo_browser_sync
.\.venv\Scripts\python.exe -m src.auth_yahoo
.\.venv\Scripts\python.exe -m src.cloud_sync
```

`cloud_sync` canlı önbellekleri günceller ve yapılandırılmışsa Telegram/Discord
bildirimi gönderir. `forecast`, testler ve doğrulama komutu bunları yapmaz.

## Proje düzeni

```text
config/                 Lig ayarı ve hesap bağlantısı şablonları
data/raw/               Geçmiş ve güncel maç günlükleri
data/processed/         Fikstür, pozisyon, kadro, skor ve sakatlık verileri
docs/                   Model, işletim ve doğrulama açıklamaları
reports/                Güncel rapor ve doğrulama özetleri
tests/                  Dağıtıma dahil edilmesi gereken kök testler (Git takibi ayrıca doğrulanır)
src/
  bayesian_model.py     Oyuncu önselleri, güncellemeler ve tahmin momentleri
  priors.py             Geçmiş sezon önselleri ve popülasyon shrinkage tahmini
  model_policy.py       Canlı motor ve deney için ortak önsel/rol politikası
  rotation_policy.py    Rotasyon/sakatlık yeniden dağıtım ve varyans politikası
  probability.py        Kategori W/L/T ve haftalık W/L/D hesabı
  rotation.py           Dakika bütçeli sakatlık rol ayarlaması
  matchup_engine.py     Haftalık projeksiyon, kadro ve add/drop değerlendirmesi
  settings.py           Normal sezon / playoff karar politikası
  playoffs.py           Kategori puanlarından ilk sekiz olasılığı
  prospective.py        Değiştirilemez prospektif tahmin, gölge aday ve sonuç arşivi
  forecast.py           Ağsız yerel rapor
  report_panel.py       Yahoo köprüsü, rapor/Excel ve takas ekranı için ortak giriş
  snapshots.py          Canlı skor kontrolü ve hafta sınırları
  live_draft_assistant.py  Draft ve sezon içi gözlem işleme
  draft_data.py         Tarihsel draft için tek fallback kaynağı
  cloud_sync.py         Canlı senkronizasyon ve bildirimler
  ...                   NBA, sakatlık, takas, streaming ve Yahoo adaptörleri
research/               Yalnızca yerel geliştirme (tools/, experiments/, tests/); Git deposuna eklenmez
```

## Model ve doğrulama

Canlı kaynak kodu ve gerekli çalışma verileri bu depodadır. Deney kodları,
araştırma testleri, özel protokoller ve sonuçlar yerelde `research/legacy/`
ve `research/current/` altında saklanır; uygulama bu klasörler olmadan çalışır.
Git geçmişinde daha önce yayımlanmış araştırma kopyaları bulunabilir;
mevcut daldan kaldırmak geçmiş commit'leri silmez.

```powershell
.\.venv\Scripts\python.exe -m src.playoffs path/to/league_outlook.json
```

Playoff hesabı gerçek kategori puan durumunu ve kalan eşleşmelerin kategori
olasılıklarını ister; olmayan fikstür veya puan durumu uydurmaz.

Kategori olasılıkları moment/normal yaklaşımları içerir. Sakatlıktan dönüş,
rotasyon ve aday sıralaması varsayımlar taşır. Kadro ataması doğrusal bir
alt problemi çözer; tüm haftanın global optimumunu garanti etmez. Kategori
puanı beklentisi için kategori bağımsızlığı gerekmez; haftalık W/L/D ve ilk
sekiz simülasyonu bu varsayımı kullanır.

- [Matematik ve karar hedefleri](docs/MODEL.md)
- [Veri, ayarlar ve otomasyon](docs/OPERATIONS.md)
- [Prospektif kayıt ve geçici dakika kabulü](docs/PROSPECTIVE.md)

Dakika önselinin zamanla azalması **geçici kabulde**. Eski rol yöntemi ve
spillover kapalı alternatif gerçek zaman damgalı olarak paralel saklanır.
Yıldız grubunda yeterli yeni sonuç birikmeden kalıcı üstünlük iddiası yoktur.
Normal sezon amacı beklenen kategori puanı olarak korunur.
