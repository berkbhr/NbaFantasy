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
Kategori sıralamasındaki ilk dört takım playoff'a katılır. Playoff hedefi ve
beraberlik bozma kuralı ayrıca yapılandırılır.

## Kurulum ve kullanım

Python 3.11 veya üzeri, proje kök dizininde:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -t . -p "test_*.py"
.\.venv\Scripts\python.exe -m ruff check src tests research
```

**Yerel önbelleklerden rapor üretmek** ağ erişimi veya bildirim gönderimi yapmaz:

```powershell
.\.venv\Scripts\python.exe -m src.forecast
```

Çıktılar: `reports/latest_cloud_summary.md` ve `reports/latest_forecast.json`.
Geçerli canlı skor yoksa yalnızca kalan maçlar gösterilir; hafta içi add/drop
önerileri bekletilir. Rapor üretmek Yahoo senkronizasyonu yapmak değildir.

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
research/               Ağsız deney çalıştırıcıları; geçici çıktılar research/runs/
tests/unit/             Birim testleri
tests/integration/      Senkronizasyon ve arşiv entegrasyon testleri
tests/research/         Kalibrasyon ve backtest kontrolleri
src/
  bayesian_model.py     Oyuncu önselleri, güncellemeler ve tahmin momentleri
  priors.py             Geçmiş sezon önselleri ve popülasyon shrinkage tahmini
  model_policy.py       Canlı motor ve deney için ortak önsel/rol politikası
  calibrate.py          Sınırlı aday seçimi, kronolojik değerlendirme ve kabul kuralları
  probability.py        Kategori W/L/T ve haftalık W/L/D hesabı
  rotation.py           Dakika bütçeli sakatlık rol ayarlaması
  matchup_engine.py     Haftalık projeksiyon, kadro ve add/drop değerlendirmesi
  settings.py           Normal sezon / playoff karar politikası
  playoffs.py           Kategori puanlarından ilk dört olasılığı
  validation.py         Kronolojik geçmiş sezon doğrulaması
  forecast.py           Ağsız yerel rapor
  snapshots.py          Canlı skor kontrolü ve hafta sınırları
  live_draft_assistant.py  Draft ve sezon içi gözlem işleme
  draft_data.py         Tarihsel draft için tek fallback kaynağı
  cloud_sync.py         Canlı senkronizasyon ve bildirimler
  ...                   NBA, sakatlık ve Yahoo adaptörleri
tests/                  Sentetik ve izole entegrasyon regresyonları
```

## Doğrulama

```powershell
.\.venv\Scripts\python.exe -m src.validation --validation 2024_25 --test 2025_26
.\.venv\Scripts\python.exe -m src.playoffs path/to/league_outlook.json
```

Playoff hesabı gerçek kategori puan durumunu ve kalan eşleşmelerin kategori
olasılıklarını ister; olmayan fikstür veya puan durumu uydurmaz.

2025–26 için 26.568 oynanmış oyuncu-maç üzerinde PTS MAE, Bayesian modelde
4,61; basit EWMA'da 4,64'tür. Model her ölçütte üstün değildir. Bu deney
haftalık olasılık kalibrasyonu veya lig üstünlüğü kanıtı değildir.

Kategori olasılıkları moment/normal yaklaşımları içerir. Sakatlıktan dönüş,
rotasyon ve aday sıralaması varsayımlar taşır. Kadro ataması doğrusal bir
alt problemi çözer; tüm haftanın global optimumunu garanti etmez. Kategori
puanı beklentisi için kategori bağımsızlığı gerekmez; haftalık W/L/D ve ilk
dört simülasyonu bu varsayımı kullanır.

- [Matematik ve karar hedefleri](docs/MODEL.md)
- [Veri, ayarlar ve otomasyon](docs/OPERATIONS.md)
- [Doğrulama yöntemi ve sonuçlar](docs/VALIDATION.md)
- [Eski/yeni doğrudan karşılaştırma ve sınırlar](reports/validation/comparison_report.md)
- [Önsel ve rol kalibrasyonu](reports/calibration/report.md)
- [Prospektif kayıt ve geçici dakika kabulü](docs/PROSPECTIVE.md)
- [Tarihsel sakatlık deneyleri ve kapsam sınırları](reports/injury_calibration/report.md)
- [Düşük rol ile sakatlık fırsatının karşılaştırması](reports/role_opportunity/report.md)
- [Kontrollü rotasyon tuning'i ve kabul kararı](reports/rotation_tuning/report.md)
- [Genişletilmiş availability kalibrasyonu](reports/availability_tuning/report.md)

Dakika önselinin zamanla azalması **geçici kabulde**. Eski rol yöntemi ve
spillover kapalı alternatif gerçek zaman damgalı olarak paralel saklanır.
Yıldız grubunda yeterli yeni sonuç birikmeden kalıcı üstünlük iddiası yoktur.
Normal sezon amacı beklenen kategori puanı olarak korunur.
