# Düşük gözlenen rol ve sakatlık fırsatı: iki kuralın denetimi

**Karar:** +2 dakika kuralı ana modele alınmadı. Mevcut sakatlık artışı da
kalibre edilmiş veya kesin bir artış olarak sunulmuyor. İki yaklaşım
prospektif olarak ayrı kaydediliyor; tek oyuncuya göre parametre seçilmedi.

## Vučević örneğinde ne oluyor?

Yerel maç önbelleğinde 21, 23 ve 25 Ekim için 5, 4 ve 15 dakika bulunuyor:
ortalama 8 dakika. Oyuncunun önceki rol önseli yaklaşık 25,9 dakika;
üç gözlemle öğrenilen rol yaklaşık 12,5 dakika. Aktif sakatlık varsayımları
bu rolün üzerine yaklaşık 7,7 dakika ekleyebiliyor. Böylece 20 dakika
civarında bir tahmin oluşuyor. Tam anlık rakamlar `vucevic_diagnostic.json`
dosyasındadır; bunlar gelecekteki gerçek dakikanın doğrulandığı anlamına gelmez.

Rol önseli, gözlenen rol ve sakatlık sonrası fırsat üç farklı unsurdur.
Dakika düşüşünü gözlemek, bunun kalıcı olduğunu veya hangi sakatlıktan
kimin yararlanacağını kesin olarak öğrenmek değildir. Üç maçlık veride
kalıcı rol kaybı, geçici kısıtlama ve dönüş süreci birbirine benzeyebilir.
Mevcut motor bu nedenleri ayrı, kalibre edilmiş olasılıklar olarak modellemiyor.

Eski kodda >=2 gözlem ve <10 MPG durumunda +2 artış sınırı vardı. Yeni
rotasyon yoluna taşınmamış olması bir davranış farkıdır; **eski kuralın
istatistiksel olarak doğru olduğunun kanıtı değildir**. Eski helper'da kalması
da onu kalibre edilmiş Bayesian posterior haline getirmez. Mevcut +7,7
hesabı da pozisyon, boşalan dakika ve paylaşım varsayımlarına dayanır.

## Karşılaştırma

`protocol.json` iki sabit adayı tanımlar: mevcut yöntem ve düşük gözlenen
rolde toplam artışı +2 ile sınırlayan eski kural. Başka eşikler taranmadı.
2024–25 seçim dönemi, 2025–26 değerlendirme dönemidir. İki dönem daha
önce incelendiğinden bu deney retrospektiftir. Aynı maçlar, aynı geçmiş
öğrenme ve aynı dakika bütçesi kullanıldı; hedef maç kadroyu kurmak için
kullanılmadı. Geçmiş pozisyon/kadro vekili nedeniyle bu, canlı sistemin
tam kalibrasyonu değildir.

| 2025–26, gözlenen rol <10 MPG ve >=2 maç | Mevcut | +2 sınırı |
|---|---:|---:|
| Oyuncu-maç | 354 | 354 |
| Dakika MAE | 5,785 | 5,184 |
| Fazla tahmin edilen dakika, ortalama | 4,452 | 3,211 |
| Eksik tahmin edilen dakika, ortalama | 1,332 | 1,973 |

Son iki satır, sırasıyla `max(tahmin-gerçek,0)` ve
`max(gerçek-tahmin,0)` ortalamasıdır; toplamları MAE'dir. +2 sınırı bu
örneklemde fazla beklentiyi azaltıyor, fakat gerçek süreyi düşük tahmin
etme maliyetini artırıyor. Yalnızca "düşük rolü daha iyi yakaladı" demek
bu ikinci maliyeti gizler.

Tüm 4.410 değerlendirme satırında MAE 5,7003 → 5,6941; yaklaşık %0,11
iyileşme. Haftalık bootstrap kazanç aralığı sıfırı içeriyor ve ikinci yarı
kötüleşiyor. Dolayısıyla genel kabul kuralları da geçilmedi.

Önsel MPG >=25 olup güncel rolü <10 olan daha özel grupta 2024–25'te
eşleşen örnek yok; 2025–26'da sadece 21 oyuncu-maç var. Bu grup için
genellenebilir bir eşik seçmek mümkün olduğu iddia edilmiyor. Düşük rol
grubunda 501/354 satır da önceden belirlenen 1.000 gözlem kabul eşiğinin
altında. Bu eşik bir tasarım tercihidir; 1.000 gözlem bile tek başına
doğruluk veya overfit olmama garantisi değildir.

## Canlı kullanım

`low_role_boost_cap=None` ana davranışı korur; +2 sınırı yalnızca ayrı
`low_role_cap2` senaryosundadır. `spillover_off`, eski dakika yöntemi ve
ana model de saklanmaya devam eder. Senaryolara keyfî yüzde ağırlıkları
atanmaz; bunlar güven aralığı veya gerçekleşme olasılığı değildir.

Telegram ve öneri kayıtları gözlenen maç/dakika, model dakika tahmini ve
sakatlık artışını görünür kılar. Böylece düşük süre alan oyuncunun puanı
bir rol geri dönüşü varsayımından besleniyorsa bu açıkça görülür.
Bayesian sezon ağırlıkları veya ESS bu örneğe göre değiştirilmedi; oyuncu
kara listesi eklenmedi. Kalıcı rol değişimi için yeni bir model kabulü,
daha geniş kronolojik değerlendirme ve yeni sonuçlarla doğrulama gerektirir.

Yeniden üretim: `python -m src.role_opportunity_audit`. Oyuncu-maç
tahminleri `.csv.gz`, bütün ölçütler ve kaynak/veri hash'leri `results.json`
içindedir. Eski tahmin arşivleri geriye dönük değiştirilmez.
