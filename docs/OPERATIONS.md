# Veri ve işletim

## Ağsız rapor ve canlı senkronizasyon

`python -m src.forecast` mevcut Parquet/JSON/SQLite önbelleklerini okur;
sakatlık veritabanını salt okunur açar. API çağrısı veya bildirim göndermez.
Tarihli fikstür zorunludur. Canlı skor 24 saatten eskiyse, farklı Eastern
haftasındaysa veya isabet/deneme alanları geçersizse reddedilir. Bu durumda
yalnızca kalan maç projeksiyonu verilir; hafta içi add/drop önerileri bekletilir.

`python -m src.cloud_sync` canlı veri indirir, runtime önbelleklerini günceller
ve ayarlı Telegram/Discord bildirimlerini gönderir. Kod kontrolü için bu komut
yerine `forecast` ve testleri kullanın.

Kaynaklar: NBA Stats maç günlükleri/fikstür, resmi NBA sakatlık PDF'leri, ESPN
sakatlık yanıtı ve Yahoo kadro/skor ekranları veya OAuth API'si. ESPN yanıtında
yer almayan takımların sakatlıkları otomatik temizlenmez. Eksik PDF raporları
health check ile karantinaya alınır. Önbellek güncelliği model güveni değildir.

Geçmiş veri `src.data_fetcher.fetch_and_process_season("2025-26")` ile alınabilir.
`python -m src.data_fetcher` mevcut 2026–27 kadro/fikstür/preseason verilerini
yeniler. Yeni sezon için bu adaptörün sezonu açıkça güncellenmelidir.

## Yahoo ve kimlik bilgileri

`python -m src.yahoo_browser_sync` localhost:8765 üzerinde çalışır. Sayfadaki
bookmarklet giriş yapılmış Yahoo sekmesinden kadro, IL, işlem ve skoru yerel
köprüye iletir. Bu işlem canlı pipeline ve ayarlı bildirimleri tetikleyebilir.

OAuth için `config/yahoo_oauth.template.json` dosyasını `config/yahoo_oauth.json`
olarak kopyalayıp `python -m src.auth_yahoo` kullanın. Bildirim ayarları
`config/telegram.template.json` şablonundan oluşturulur. Gerçek kimlik bilgileri
Git tarafından yok sayılır.

`src/draft_data.py` tarihsel 14×13 draft için tek fallback kaynağıdır. Canlı
`league_state.json` kadroları bunun yerini alır. İsim çözümleme 1:1 olmalıdır;
çözülemeyen veya iki takıma atanan oyuncu sessizce kabul edilmez. Genel NBA
G/F/C pozisyonları tam Yahoo uygunluğunun yerine geçmez.

## Lig ayarları

`config/league.template.json` dosyasını isteğe bağlı `config/league.json`
olarak kopyalayın. Ayar yoksa normal sezon kategori puanı hedefi kullanılır.

- `phase`: `regular_season` veya `playoffs`.
- `playoff_tie_credit`: Normal sezonda kullanılmaz. Playoff'ta gerçek eşitlik
  kuralına göre 0–1 arasında değer zorunludur; null ile playoff açılmaz.
- `playoff_spots`: Bu ligde 4.
- `max_weekly_adds`: Varsayılan 3; gerçek lig limitiyle eşleşmelidir.
- `adds_used_this_week`: Varsayılan 0. Her hafta ve işlem sonrası güncelleyin;
  tüketim sayısı doğrulanmamış işlem geçmişinden uydurulmaz.
- `protected_player_names`: Hiçbir öneride düşürülemeyecek isimler.

Normal sezonda kategori beraberliği her zaman yarım puandır; haftalık
beraberliğin değeriyle karıştırılmaz.

## İlk dört hesabı

`python -m src.playoffs league_outlook.json --simulations 20000` kullanılır.
Girdinin `standings` alanı takım kimliğinden kategori `W`, `L`, `T` toplamlarına
giden sözlüktür. `fixtures`, kalan eşleşmelerin listesidir. Her eşleşmede
`week`, `home`, `away` ve dokuz kategorili `categories` bulunur. Örnek tek
kategori: `"PTS": {"win": 0.6, "tie": 0.01}`. Bütün ihtimaller ev sahibi
perspektifindedir; mağlubiyet `1-win-tie` olarak hesaplanır.

Tam girdi gerçek 14 takımın bütün kalan eşleşmelerini içermelidir. W/L/T
haftalık sonuç sayıları değildir. Sıralama `(W+.5T)/(W+L+T)` ile yapılır.
Gerçek bir `tiebreak_priority` listesi verilmezse kesim noktasında tarafsız
kura varsayılır. Bu Yahoo tiebreak kuralının doğrulandığı anlamına gelmez.
Monte Carlo standart hatası yalnızca örnekleme hatasıdır. Gelecek kategori
sonuçları ve haftalar bağımsız varsayılır. Veri sağlanmadan ilk dört yüzdesi
üretilmez; haftalık kazanma yüzdesi sezon sıralamasının yerine kullanılmaz.

## Otomasyon ve geliştirme

`python -m src.calibrate` ağsız kalibrasyonu yeniden çalıştırır. Önce
`reports/calibration/protocol.json` yazılır; 2024–25'te aşamalı aday seçilir,
seçim dondurulur ve 2025–26'da başlangıç politikasıyla karşılaştırılır.
Komut, kabul kurallarına göre `config/model_policy.json` dosyasını günceller;
bu nedenle mevcut canlı asistan oturumunu yeniden kurmak gerekir.
Doğrulanmış moment formülleri hiçbir adayda eski hatalı haline dönmez.
Karar ve kaynak/veri SHA256 kayıtları `reports/calibration/decision.json`
dosyasındadır. Önceki çekirdek kıyasları kendi kaynak hash'lerine aittir.

`checks.yml` kaynak değişikliklerinde ağsız test, Ruff ve biçim kontrolü yapar.
`daily_fantasy_sync.yml` mevcut canlı otomasyondur: UTC 06:30, 12:30, 18:30,
23:15. Berlin ve Eastern karşılıkları yaz/kış saatine göre değişir; sabit bir
“tip-off'tan 45 dakika önce” garantisi yoktur. Runtime durumları
`nba-fantasy-bot` dalına yazılır. Yerel değişiklikler push yapılmadan buluttaki
otomasyonu değiştirmez.

Her bulut koşusu aynı zamanda sıkıştırılmış tahmin/girdi/sonuç arşivini
`data/archive/` altında üretir ve bot dalında korur. Önceki bot arşivi
koşudan önce geri yüklenir. Ayrıntılar ve geçici kabul protokolü
`docs/PROSPECTIVE.md` içindedir. Telegram uzun tablolar yerine tek kısa
kart gönderir; `reports/telegram_preview.html` gönderimsiz önizlemedir.

Tarihsel sakatlık raporları `python -m src.injury_backtest --backfill`,
etiket örneklemi `--labels`, yerel tekrar `--experiments` ile üretilir.
PDF'ler kalıcı tutulmaz; metin, rapor zamanı ve kaynak hash'i sıkıştırılır.
Bu komutlar canlı sakatlık veritabanına geçmiş kayıt yazmaz.

Eski 12 takımlı simülatörler, kendi tahminlerinden üretilmiş sezon sonuçları,
yinelenen Excel veritabanları, türetilebilir DNP/trade dosyaları ve eski
“tam doğrulanmış” raporlar kaldırıldı. Ham maçlar ve canlı veriler korundu.
Önceki önsel CSV'si `reports/validation/prior_comparison_legacy.csv` olarak
saklanır; yeni deneyin kanıtı değildir. Büyük tahmin Parquet çıktısı Git'e eklenmez.

```powershell
.\.venv\Scripts\python.exe -m src.validation --validation 2024_25 --test 2025_26
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
.\.venv\Scripts\python.exe -m ruff check src tests
.\.venv\Scripts\python.exe -m ruff format --check src tests
```
