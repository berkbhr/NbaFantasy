# Doğrulama raporu

Eski kodla doğrudan A/B, oyuncu alt grupları, şut accuracy skorları ve kontrollü
matematik deneyleri için [ayrı karşılaştırma raporuna](../reports/validation/comparison_report.md)
bakın. Aşağıdaki sezon ortalaması / EWMA deneyi eski sürüm karşılaştırması değildir.

Bu rapor `python -m src.validation --validation 2024_25 --test 2025_26` çıktılarından hazırlanır.
2024–25 yalnızca varyans ölçeklerini belirlemek için kullanılır; ölçekler 2025–26 testinde yeniden fit edilmez.
Her maç için tahmin gözlemden önce üretilir, ardından posterior güncellenir. Yalnızca önceki tamamlanmış sezon önseldir.
Güncel sakatlık DB veya güncel pozisyonlar tarihsel bilgi gibi kullanılmaz. Geçmiş pozisyon dosyası yoksa pooled önsel kullanılır.

## Kapsam

Yeni gerçek zamanlı değerlendirme `docs/PROSPECTIVE.md` ile tanımlanır.
Normal sezon kategori puanı amacı korunur; yalnızca gerçek sonuç biriktirme
başlatılmıştır. Geçmiş availability/spillover deneyleri
`reports/injury_calibration/report.md` içindedir ve retrospektiftir.

**Güncel politika kalibrasyonu:** `reports/calibration/report.md` ve
`decision.json` ayrı deneyin kayıtlarıdır. 2024–25 seçim, 2025–26 retrospektif
değerlendirme kullanıldı. Küçük aday kümesinde yalnızca zamanla azalan
dakika önsel ankrajı kabul edildi. Aşağıdaki tablolar önceki çekirdek
deneyine aittir; canlı dakika güncellemesiyle aynı deney olarak okunmamalıdır.

2025–26 testinde MIN>0 olan **26.568 oyuncu-maç** değerlendirilmiştir. DNP maçları bu deneye dahil değildir.
Bu sonuçlar oynama koşuluyla oyuncu üretimini ölçer; sakatlık, IL, waiver, draft üstünlüğü veya haftalık H2H kalibrasyonu kanıtlamaz.
Tüm oyuncular dahil olduğu için bench oyuncuları da ağırlık taşır; yalnızca fantasy yıldızları için ayrı bir üstünlük sonucu çıkarılamaz.

## Ortalama mutlak hata (MAE)

| İstatistik | Sezon ortalaması | Son 5 | EWMA | Bayesian |
|---|---:|---:|---:|---:|
| PTS | 5.229 | 4.801 | 4.636 | 4.611 |
| REB | 2.066 | 1.989 | 1.920 | 1.891 |
| AST | 1.478 | 1.402 | 1.360 | 1.348 |
| STL | 0.740 | 0.753 | 0.734 | 0.722 |
| BLK | 0.524 | 0.518 | 0.511 | 0.513 |
| FG3M | 0.942 | 0.928 | 0.899 | 0.894 |
| TOV | 0.947 | 0.940 | 0.911 | 0.895 |
| MIN | 6.614 | 5.053 | 5.019 | 5.025 |

PTS, REB, AST, STL, FG3M ve TOV için bu testte Bayesian MAE, EWMA’dan biraz düşüktür.
BLK ve dakika MAE’sinde EWMA hafif daha iyidir. Farklar küçük; anlamlılık veya başka sezona genellenme iddiası yoktur.
Sezon ortalaması statik önceki sezon tahminidir; last5 ve EWMA yalnızca tahminden önce gözlenen maçlarla güncellenir.

## Tahmin aralığı kapsaması

| İstatistik | Ham %95 aralık kapsamı | Validation ölçekli %95 kapsamı | Ölçek |
|---|---:|---:|---:|
| PTS | 93.6% | 95.7% | 1.267 |
| REB | 95.0% | 95.6% | 1.090 |
| AST | 95.0% | 95.4% | 1.066 |
| STL | 94.7% | 95.1% | 1.083 |
| BLK | 93.8% | 94.1% | 1.038 |
| FG3M | 95.4% | 95.5% | 1.018 |
| TOV | 95.4% | 95.3% | 0.970 |
| MIN | 92.7% | 95.1% | 1.299 |

Ölçekler oyuncu-maç artıklarına aittir; canlı haftalık motora otomatik uygulanmaz.
Canlı motorda role özel dakika güncellemeleri ve haftalık ortak posterior belirsizliği vardır; günlük ölçeği körlemesine haftaya taşımak uygun değildir.
Düşük sayılı BLK/STL gibi istatistiklerde normal aralıkların kapsaması ayrık dağılım nedeniyle hedef seviyeden farklı olabilir.
`normal_bin_log_loss`, normal yaklaşımın yarım birimlik sayı hücrelerinden hesaplanan tanısal skordur; tam bir joint count üretici modelinin log likelihood’u değildir.

## Yeniden üretilebilir dosyalar

- `reports/validation/player_metrics.csv`: MAE, RMSE, %50/%80/%95 kapsama ve tanısal skorlar.
- `reports/validation/metadata.json`: Validation/test sezonları, veri ve model kaynak SHA256’ları, ortam sürümleri ve varyans ölçekleri.
- `reports/validation/validation_residual_correlation.csv`: Validation sezonunda tahmin hataları kontrol edilerek hesaplanan standartlaştırılmış artık korelasyonları. Bunlar kategori kazanma korelasyonu değildir.
- `reports/validation/player_forecasts.parquet`: Her tahmin anı için gerçek değer, ortalama, varyans ve baselines. Büyük dosya Git tarafından yok sayılır; komutla yeniden üretilir.
- `reports/validation/prior_comparison_legacy.csv`: Önceki çalışmadan korunan karşılaştırma. Üretici deney kodu bu sürümde bulunmadığından yeni sonuçlara karıştırılmaz.

## Haftalık olasılıkların doğrulanması

`src.validation.score_matchups(forecasts, outcomes)` tarihli, tamamlanmadan önce üretilmiş haftalık W/L/D tahminlerini actual sonuçlarla karşılaştırır.
Multiclass Brier, log loss ve win reliability binleri döndürür. Her kayıtta aynı `id`, `forecast_at`, `completed_at` ve sonuç gerekir.
Tamamlandıktan sonra üretilen tahminler reddedilir. Farklı tahmin ufukları çağıran tarafından ayrı gruplandırılmalıdır.
`python -m src.forecast` tahminleri `reports/forecasts/` altında zaman damgasıyla arşivler. Gerçek sonuç arşivi henüz bağlanmadığından canlı haftalık yüzdelerin kalibre olduğu iddia edilmez.

## Regresyon kapsamı

Testler kategori puanı ile playoff hedefi ayrımını, kesin W/L/D sınırlarını, kategori beraberliklerini, farklı şut hacimlerini, moment formüllerini Monte Carlo ile, haftalık ortak oran belirsizliğini, boş slot seçimini, korumaları ve waiver tarihlerini kapsar.
Ayrıca idempotent/kronolojik gözlem işleme, ileriye bakmama, DNP, dönüş tarihi, 240 dakika bütçesi, sağlıksız rapor reddi ve kısmi ESPN clearance kontrol edilir.
Testler ağ veya canlı hesap kullanmaz; PDF fixture doğrudan pypdf ile üretilir. Canlı Yahoo/NBA erişimi ve gerçek bildirim gönderimi bu çalışmada uçtan uca denenmemiştir.
