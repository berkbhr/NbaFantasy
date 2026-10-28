# Eski ve yeni sürüm: ayrıntılı karşılaştırma

## Sonuç

**Yeni sürüm bazı hesaplama hatalarını düzeltiyor ve tarihsel sayma tahminlerinde küçük MAE kazançları sağlıyor. Her ölçütte üstün değil; daha çok gerçek fantasy kategorisi kazanacağımız henüz kanıtlanmış değil.**

Bu karşılaştırma kullanıcının doğrudan eski/yeni A/B talebinden sonra yapıldı. Önceki EWMA karşılaştırması eski sürüm karşılaştırması değildi.
Üretim modeline bu sonuçlara bakılarak yeni parametre ayarı yapılmadı. Yeni sürümün zayıf çıktıları da raporlandı.

## 1. Deney protokolü

- Eski kaynak: Git commit `d4120fa58808dccdb07e2760f905af0031549900` içindeki `bayesian_model.py`, `simulator.py` ve matematik denetiminde `matchup_engine.py`.
- Yeni kaynak: mevcut çalışma ağacı. Kaynak hash’leri metadata dosyalarında saklanır.
- 2024–25: 26.206; 2025–26: 26.568 oynanmış oyuncu-maç. Toplam **52.774 farklı oyuncu-maç**.
- Her sezon hem yalnızca bir önceki sezon önseliyle, hem iki önceki sezonun harmanıyla karşılaştırıldı. Bunlar aynı gözlemlerin farklı konfigürasyonlarıdır; bağımsız örnek sayısı iki katına çıkarılmadı.
- Her iki sürüm aynı sıralanmış ve tekilleştirilmiş maçları görür. Tahmin önce, o maçın posterior güncellemesi sonra yapılır.
- Oyuncu başına PTS/REB/AST/STL/BLK/3PM/TOV/MIN ve FGM/FGA/FTM/FTA olmak üzere 12 çıktı değerlendirilir.
- MAE ve RMSE düşük olduğunda iyidir. MAE iyileşmesi `100*(eski-yeni)/eski`; pozitif değer yeninin hata azalmasıdır. Bu yüzde fantasy kazanma olasılığı artışı değildir.
- Pozisyonlar iki kolda da pooled tutulur: güncel pozisyon verisini geçmişte biliniyormuş gibi kullanmamak için. Dolayısıyla bu, canlı pozisyonlu modelin tamamının testi değildir.
- MIN>0 koşulu altında üretim ölçülür. Oynama ihtimali, DNP, gerçek IL hamlesi ve kadro optimizasyonu tarihsel A/B’ye dahil değildir.
- Güven aralıkları aynı haftaları iki sürüm için birlikte örnekleyen 2.000 calendar-week block bootstrap tekrarından gelir (seed 42). Haftalar arası oyuncu bağımlılığının tamamını kapsamaz; çoklu karşılaştırma düzeltmesi yapılmamıştır.
- Her iki geçmiş sezon daha önce incelendiği için sonuçlar artık el değmemiş kör test sayılmaz. Yeni hiperparametre ayarlanmadı; yine de genelleme için ileri tarihli, görülmemiş veri gerekir.

## 2. İki sezonluk önsel ile tüm oyuncular

| Çıktı | Eski MAE 2024–25 | Yeni MAE 2024–25 | Hata azalması | Eski MAE 2025–26 | Yeni MAE 2025–26 | Hata azalması |
|---|---:|---:|---:|---:|---:|---:|
| PTS | 4.650011 | 4.637523 | +0.269% | 4.618988 | 4.605620 | +0.289% |
| REB | 1.919588 | 1.917168 | +0.126% | 1.892842 | 1.890130 | +0.143% |
| AST | 1.344282 | 1.340869 | +0.254% | 1.352800 | 1.348188 | +0.341% |
| STL | 0.713507 | 0.713784 | -0.039% | 0.720847 | 0.720917 | -0.010% |
| BLK | 0.521602 | 0.518671 | +0.562% | 0.516505 | 0.513111 | +0.657% |
| FG3M | 0.902603 | 0.893768 | +0.979% | 0.900001 | 0.891996 | +0.889% |
| TOV | 0.886325 | 0.885147 | +0.133% | 0.894674 | 0.893991 | +0.076% |
| MIN | 5.045504 | 5.045504 | +0.000% | 5.026695 | 5.026695 | +0.000% |
| FGM | 1.783438 | 1.783164 | +0.015% | 1.768271 | 1.768017 | +0.014% |
| FGA | 2.833767 | 2.834381 | -0.022% | 2.819195 | 2.819742 | -0.019% |
| FTM | 1.305193 | 1.305369 | -0.013% | 1.352990 | 1.353111 | -0.009% |
| FTA | 1.579750 | 1.580048 | -0.019% | 1.637828 | 1.638283 | -0.028% |

Sayma kategorilerinin altısında iki sezonda da küçük MAE kazancı var. STL’de çok küçük gerileme, dakikada eşitlik var. Şut hacmi ve isabet tahminlerinde sonuçlar karışık; her alanda iyileşme iddiası yok.
Örneğin 2025–26 PTS farkı oyuncu-maç başına yalnızca 0,01337 mutlak hata birimidir. Bootstrap aralığı yaklaşık [0,00758; 0,02103]. Bu kazanımın büyüklüğü sınırlıdır.
2024–25 iki sezonlu önselde AST ve BLK RMSE’si çok az kötüleşirken MAE iyileşir. Tek bir metriğe dayanarak bütün dağılımın üstün olduğu söylenemez.

## 3. Tek sezonluk önsel duyarlılığı

| Çıktı | MAE iyileşmesi 2024–25 | MAE iyileşmesi 2025–26 |
|---|---:|---:|
| PTS | +0.263% | +0.295% |
| REB | +0.121% | +0.154% |
| AST | +0.204% | +0.342% |
| STL | +0.004% | +0.001% |
| BLK | +0.675% | +0.635% |
| FG3M | +0.921% | +0.909% |
| TOV | +0.117% | +0.055% |
| MIN | +0.000% | +0.000% |
| FGM | -0.004% | -0.005% |
| FGA | -0.006% | -0.008% |
| FTM | -0.003% | -0.003% |
| FTA | -0.002% | -0.002% |

## 4. Oyuncu grupları ve öğrenme dönemi

Gruplar hedef sezondaki sonuca bakılarak seçilmedi. Dakika grubu bir önceki tamamlanmış sezonun gerçek MPG’sinden; ilk 10 maç grubu yalnızca tahmin anında daha önce görülen maç sayısından gelir.
25+ MPG grubu fantasy açısından daha alakalı bir rotasyon vekilidir; gerçek Yahoo draft sırası veya bütün fantasy kadrosu değildir.

| 2025–26 / iki önsel | Oyuncu-maç | PTS hata azalması | REB | AST | STL | 3PM |
|---|---:|---:|---:|---:|---:|---:|
| Tümü | 26568 | +0.289% | +0.143% | +0.341% | -0.010% | +0.889% |
| Önceki sezon 25+ MPG | 9911 | +0.077% | +0.141% | +0.129% | -0.044% | +0.446% |
| Önceki sezon 15–25 MPG | 7952 | +0.400% | +0.167% | +0.575% | +0.019% | +1.420% |
| Önceki sezon <15 MPG / yeni | 8705 | +0.503% | +0.123% | +0.453% | +0.010% | +1.067% |
| Oyuncunun ilk 10 maçı | 5442 | +0.945% | +0.442% | +1.124% | +0.039% | +1.704% |
| Oyuncunun 11. ve sonraki maçları | 21126 | +0.124% | +0.068% | +0.145% | -0.021% | +0.691% |

25+ MPG grubunda PTS MAE kazancı yalnızca %0.077. Mutlak hata farkının %95 bootstrap aralığı [-0.001672; 0.011857] ve sıfırı içeriyor. Bu grupta PTS üstünlüğü için güçlü kanıt yok.
İyileşme ilk 10 maçta daha belirgin, sonraki maçlarda küçülüyor. Bu, önsel/shrinkage değişikliklerinin zamanla yeni gözlemlerin içinde seyrelmesiyle uyumlu; tek başına nedensel ispat değildir.

## 5. Belirsizlik kalibrasyonu ve şut accuracy

Nominal %95 aralık için ideal kapsama %95’tir. Daha yüksek sayı her zaman daha iyi değildir; aşırı geniş aralık da sorun olabilir.

| Çıktı | Eski %95 kapsamı | Yeni %95 kapsamı |
|---|---:|---:|
| PTS | 93.703% | 93.541% |
| REB | 94.986% | 94.960% |
| AST | 95.065% | 94.911% |
| STL | 94.584% | 94.640% |
| BLK | 94.079% | 93.929% |
| FG3M | 95.438% | 95.336% |
| TOV | 95.476% | 95.389% |
| MIN | 92.754% | 92.754% |
| FGM | 95.845% | 95.894% |
| FGA | 96.390% | 96.428% |
| FTM | 94.042% | 94.091% |
| FTA | 94.147% | 94.166% |

PTS ve dakika aralıkları hedef %95’in altında. Yeni PTS kapsaması eskiye göre biraz daha kötü. Bu nedenle yeni belirsizlik hesabına topluca “daha iyi kalibre edilmiş” denemez.
Bu A/B ham varyansları karşılaştırır. Önceki validation raporundaki validation ölçekleri iki sürümden yalnızca birine uygulanarak kıyas avantajı yaratılmadı.

| Accuracy skoru, 2025–26 | Eski | Yeni |
|---|---:|---:|
| FG deneme başına Bernoulli log loss | 0.68632721 | 0.68633054 |
| FG Beta–Binomial NLL / en az bir denemeli maç | 1.64316526 | 1.64318829 |
| FT deneme başına Bernoulli log loss | 0.50985029 | 0.50985337 |
| FT Beta–Binomial NLL / en az bir denemeli maç | 1.06002555 | 1.06004266 |

Accuracy skorlarında yeni model çok az daha kötü; farklar küçük ve bu skorlar için ayrıca güven aralığı hesaplanmadı. Takım FG% karşılaştırmasının düzelmesi, oyuncunun şut isabet becerisinin daha iyi tahmin edildiği anlamına gelmez.
Gerçek deneme sayısı accuracy skorunda koşullama/ölçüm maruziyetidir; üretim tahmininin girdisine verilmez. Model kendi dakika ve deneme beklentisiyle forecast yapar.

## 6. Sonucu bilinen FG% hesaplama deneyi

Sabit denemeli bağımsız Binomial dünyada 35 hacim/accuracy senaryosu tam ayrık toplamla çözüldü. Ölçülen değer `P(kazanım)+.5P(beraberlik)` kategori puanıdır.
Ortalama mutlak hata: eski varsayılan **3.279 yüzde puan**, eski varyans şişirmesi kapalı **2.268**, yeni **0.197**.
Bu, seçilen kontrollü ızgaranın sonucudur; NBA maçlarında ölçülmüş kalibrasyon sonucu değildir.

Örnek: A 100 denemede %55, B 1.000 denemede %50 isabet olasılığına sahip.

| Hesap | FG kategori puanı |
|---|---:|
| Tam ayrık gerçek | 0.830634 |
| Eski varsayılan | 0.684750 |
| Eski, varyans çarpanı kapalı | 0.708309 |
| Yeni delta yöntemi | 0.830925 |

Burada yeni hesap belirgin biçimde daha doğru. Küçük hacimlerde normal/delta yaklaşımı hâlâ tam ayrık çözüm değildir.

## 7. Haftalık ortak belirsizlik: kontrollü Monte Carlo

26 senaryo, her birinde 30.000 deneme. Oyuncu sayısı 1/10, maç sayısı 1/4, prior exposure 60/650 dakika, oynama ihtimali 1/.8. İki ayrı stres senaryosu yokluk korelasyonunu .65 kabul eder.
Ortak Gamma oranları ve Beta accuracy her oyuncunun haftalık maçlarında paylaşılır. Dakika 24/36, deneme compound-Poisson olarak üretilir. Bu dünya açıkça tanımlanmıştır; gerçek NBA dağılımı olduğu varsayılmaz.
Yeni STL varyansı doğru korelasyon verildiğinde 26 senaryonun tamamında bağımsız kapalı form özdeşliğini sayısal toleransla sağladı. Generator ayrıca ayrı bir testte kapalı form ortalama/varyansla doğrulandı.

| Kategori | Gerçek yokluk korelasyonu | Eski ortalama mutlak hata (yp) | Yeni varsayılan (yp) | Yeni, gerçek rho biliniyorsa (yp) |
|---|---:|---:|---:|---:|
| FG_PCT | 0.00 | 3.017 | 1.386 | 1.386 |
| FG_PCT | 0.65 | 0.177 | 0.561 | 0.173 |
| STL | 0.00 | 1.254 | 0.399 | 0.399 |
| STL | 0.65 | 2.084 | 2.670 | 0.240 |

Bağımsız yokluk senaryolarında yeni yaklaşım daha iyi. Korelasyon .65 iken varsayılan yeni model bazı durumlarda eski modelden kötü. “Gerçek rho biliniyor” kolu oracle duyarlılığıdır; gerçek NBA yaralanmalarından fit edilmiş veya üretime geçirilmiş bir çözüm değildir.
Örneğin 10’a 10 oyuncu, dört maç, exposure 650 dakika ve oynama ihtimali .8 için korelasyon .65 iken STL kategori puanı:

- Monte Carlo gerçek: 0.80178; standart hata 0.00226.
- Eski: 0.79741; yeni varsayılan: 0.83717; doğru rho ile yeni: 0.80503.

Bu stres testi yeni sürümün bütün koşullarda üstün olmadığını açıkça gösteriyor. Düşük hacim / sıfır deneme ihtimali bulunan senaryolarda da yüzde oranının normal yaklaşımı sapabilir.
Senaryo ortalamaları eşit ağırlıklıdır; NBA’de bu senaryoların gerçekleşme sıklığına göre ağırlıklandırılmış kazanç olarak yorumlanamaz.

## 8. Veri sızıntısı ve deney doğruluk kontrolleri

- Eski/yeni aynı oyuncu-maç kimlikleri üzerinde one-to-one birleştirildi; eşleşmeyen gözlem varsa deney durur.
- İki sezonda da pozitif dakikalı kayıtlarda yinelenen PLAYER_ID/GAME_ID veya aynı gün oyuncu kaydı yok.
- Sekiz kontrol kolunda geçmiş önsel dosyalarının okuma yolları izlendi; dosyadaki en geç tarih hedef sezonun ilk maçından önce olmak zorunda.
- Sekiz kontrol kolunda ilerideki maçın dakika, PTS, FGM, FGA ve 3PM değerleri değiştirildi; o maça kadar üretilen ortalama ve varyans tahminleri değişmedi.
- `predict_next_game` gerçek maç dakikası veya gerçek deneme sayısını girdi olarak almıyor; yalnızca tahmin tarihi veriliyor.
- Pozisyon popülasyonu ve shrinkage hiperparametreleri yalnızca tamamlanmış önceki sezonlardan geliyor.
- Güncel sakatlık DB, 2026–27 kadro bilgisi ve canlı Yahoo skoru tarihsel karşılaştırmada kullanılmadı.
- Deney özetinin hata yönü, tam Binomial referansı ve Monte Carlo generator momentleri bağımsız regresyon testleriyle kontrol edildi. Toplam test takımı 60/60 geçti.
- Seed, veri hash’leri, model hash’leri, bootstrap yöntemi ve kapsam metadata’da kayıtlı.

Bu kontrollerde ileriye bakma sızıntısı saptamadım. Ancak bu, tüm yazılımın hatasız olduğunun ispatı değildir. Final cache ile replay yapıyoruz; geçmişte ilk yayınlanan verinin tüm revizyonlarını ve o günkü haber akışını yeniden kuran eksiksiz bir point-in-time arşiv yok.

## 9. Hangi yıllar ve ağırlıklar?

| Kullanım | Birincil geçmiş sezon | İkincil geçmiş sezon | Sonraki gözlemler |
|---|---|---|---|
| Canlı 2026–27 | 2025–26 | 2024–25 | 2026–27 tamamlanmış maçlar |
| A/B 2024–25, tek önsel | 2023–24: %100 kişisel ham geçmiş | Yok | 2024–25 kronolojik |
| A/B 2024–25, iki önsel | 2023–24: w | 2022–23: 1-w | 2024–25 kronolojik |
| A/B 2025–26, tek önsel | 2024–25: %100 kişisel ham geçmiş | Yok | 2025–26 kronolojik |
| A/B 2025–26, iki önsel | 2024–25: w | 2023–24: 1-w | 2025–26 kronolojik |

İki sezon bulunan oyuncuda `w = clip(GP_birincil / 65, 0.35, 0.80)`. Bu, kişisel geçmiş dakika başına oranların başlangıç ağırlığıdır; pozisyon shrinkage ve güncel posterior güncellemeleri sonrası toplam model ağırlığı değildir.

| Birincil sezonda GP | Birincil ağırlık | İkincil ağırlık |
|---:|---:|---:|
| 70 | %80.00 | %20.00 |
| 52 | %80.00 | %20.00 |
| 50 | %76.92 | %23.08 |
| 40 | %61.54 | %38.46 |
| 30 | %46.15 | %53.85 |
| 20 | %35.00 | %65.00 |

Canlı önselde dolayısıyla iki sezonu da olan sağlıklı oyuncuların çoğu %80 2025–26 / %20 2024–25 ile başlar. Örneğin mevcut cache’te Maxey 70 GP, Kawhi 65 GP, Harden 70 GP, Ingram 77 GP; bu dört oyuncunun kişisel ham oran önseli %80/%20’dir.
Kod yorumundaki sabit %75/%25 ifadesi çalışan formülü doğru anlatmıyor; hesapta yukarıdaki değişken ağırlık kullanılıyor.
2026–27 preseason verisi çaylak / çok az geçmişi olan oyuncular içindir; bütün oyunculara verilen sabit bir üçüncü yüzde değildir. Bir geçmiş sezon eksikse diğer sezon fallback olur. Geçmiş dakika rolünde ayrıca %65 tam sezon MPG + %35 son 15 maç MPG harmanı vardır; bu sezon ağırlığıyla karıştırılmamalıdır.
Güncel 2026–27 maçlarının payı sabit değildir. Sayma kategorilerinde güncelleme, etkili eski exposure beta ve yeni dakika m ile `eski pay=beta/(beta+m)`, `yeni maç pay=m/(beta+m)` biçimindedir. Beta zamanla unutulur; şut accuracy’sinde maruziyet dakikadan ziyade deneme sayısıdır.

## 10. Gerçek fantasy performansı için kanıt sınırı

Elimizde 2024–25 / 2025–26 boyunca tarihli Yahoo kadro, IL, waiver ve karar anı sakatlık arşivi yok. Mevcut injury_snapshots DB yalnızca 2026-10-22 ile 2026-10-27 arasını kapsıyor. Bu yüzden geriye dönük tam lig başarısı veya kaç ek kategori kazanılacağını güvenilir şekilde hesaplayamam.
Bu raporun tarihsel bölümü BayesianPlayer + önsel inşasıdır. Canlı son maç dakika harmanı, gerçek pozisyon kısıtları, IL ve add/drop motorunun tamamının üstünlüğü ölçülmüş değildir. Sentetik matematik deneyleri de gerçek lig sonucunun yerine geçmez.
Yeni sürümü **hesaplama hataları düzeltilmiş, bazı nokta tahminleri az iyileşmiş ama belirsizlik ve canlı karar üstünlüğü henüz bütünüyle doğrulanmamış aday sürüm** olarak değerlendiriyorum.
Gerçek faydayı doğrulamak için aynı karar anında eski/yeni tahminleri saklayıp gerçek haftalık kategori sonuçlarıyla karşılaştırmak gerekir. Bu yapılmadan otomatik olarak daha fazla kategori veya daha yüksek playoff olasılığı vaat edilemez.

## 11. Kesinleşmiş kategori sonuçlarında haftalık W/L/D

Bu kontrolde gelecek belirsizlik yoktur. Eski motor, beraberliği yarım kategori olasılığıyla temsil eder; yeni motor gerçek kategori beraberliğini ayrı taşır.

| Kesin kategori skoru | Eski hafta kazanma | Yeni hafta kazanma | Yeni hafta beraberliği |
|---|---:|---:|---:|
| 5-4-0 | 84.134% | 100.0% | 0.0% |
| 4-5-0 | 15.866% | 0.0% | 0.0% |
| 4-3-2 | 76.025% | 100.0% | 0.0% |
| 0-0-9 | 50.000% | 0.0% | 100.0% |

Yeni sonuçlar bu sınır durumlarında kesindir. Bu kontrol, haftalık sonuç fonksiyonunun matematik hatasını doğrular; normal sezonda ana amaç yine kategori puanıdır.

Veri: [deterministik sonuç kontrolü](deterministic_outcome_audit.csv).

## Yeniden çalıştırma

```powershell
.\.venv\Scripts\python.exe -m src.compare_versions --old-ref d4120fa58808dccdb07e2760f905af0031549900
.\.venv\Scripts\python.exe -m src.mathematical_audit --old-ref d4120fa58808dccdb07e2760f905af0031549900
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
```

Eski commit Git geçmişinde bulunmalıdır. Komutlar ağ, canlı Yahoo veya bildirim gönderimi kullanmaz; üretim model parametrelerini değiştirmez.

Kaynaklar: [Tarihsel metrikler](version_comparison.csv), [protokol ve sızıntı kontrolleri](version_comparison_metadata.json), [tam Binomial deneyi](fixed_attempt_audit.csv), [haftalık moment deneyi](weekly_moment_audit.csv), [sentetik deney varsayımları](mathematical_audit_metadata.json).
