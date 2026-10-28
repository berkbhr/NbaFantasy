# Eski skor ile yeni fikstürün karıştırılması

Kullanıcının "Wembanyama maça çıkmadan da avantajı beklenmeliydi" itirazı
üzerine zaman sınırı ayrıca incelendi. İlk inceleme, skorun 6–5'ten 6–16'ya
geçişini açıklamakla yetiniyordu. Bu, ilk tahminin doğru olduğunu kanıtlamaz.

## Hata

Eski 6–5 skoru `2026-10-27T15:57:51Z` tarihinde yakalanmış. 28 Ekim
`12:34Z` tahmini bu skoru 24 saatten yeni olduğu için kabul etmiş; ancak
kalan fikstürü 28 Ekim'den başlatmış. Böylece 27 Ekim maçları ne
gerçekleşen skora ne de kalan projeksiyona girmiş.

Arşivdeki aynı skorla 27 Ekim'i kapsayan kayıt, BLK kazanımını %26,30
hesaplıyor. Eastern takvim günü değişip eski skor yeniden kullanıldığında
%43,04'e yükseliyor. Bu iki kaydın güncel sezon logları, kadro ve sakatlık
kaynak hash'leri aynı; takvim başlangıcı değişmiş. Bu, ilk %43 değerinin
gerçek bir kadro veya performans gelişmesi olarak okunamayacağını gösterir.

## Wembanyama'nın beklenen katkısı zaten var mıydı?

Evet. Modelin başlangıç önseli oynadığı maç başına yaklaşık 2,98 blok;
27 Ekim sonuçları kullanılmadan önceki tahmin yaklaşık 3,21 blok.
Etkin oynama ihtimali yaklaşık %84 olduğundan planlanan maç başına
koşulsuz katkı yaklaşık 2,70 blok. Model, gerçekleşen 5 bloğu önceden
bilmiyor; yüksek blok oranını geçmiş veriden zaten kullanıyor.

Arşivdeki kadro, takım, pozisyon ve sağlık bilgileri sabit tutularak,
güncel sezon gözlemleri 27 Ekim'den önce kesildi. Sadece fikstür başlangıcı
değiştirildi:

| Aynı 6–5 skoru ve aynı oyuncu durumu | 27 Ekim'den | 28 Ekim'den |
|---|---:|---:|
| Wembanyama kalan maç | 3 | 2 |
| Wembanyama beklenen toplam BLK | 8,10 | 5,40 |
| Sen / rakip beklenen final BLK | 25,55 / 30,02 | 22,88 / 23,57 |
| Senin BLK kazanman | %26,57 | %43,31 |

Doğru kapsama sahip senaryoda kaybetme olasılığı %69,15, beraberlik %4,28.
Bu hesap 27 Ekim'in gerçekleşen 5 bloğunu kullanmıyor. Senaryo, takvim
etkisini ayıran tanısal bir tekrardır; eski kodun birebir tekrarı veya yeni
bir bağımsız tarihsel test değildir. Önbellekteki eski satırlarda sonradan
yapılmış kaynak düzeltmeleri bulunabileceğinden arşivdeki %26,30 ile küçük
farkı gizlenmemiştir. Ayrıntılar `wemby_temporal_audit.json` içindedir.

## Düzeltme ve sınırları

Skor, kalan projeksiyonun başladığı Eastern takvim gününden önce
yakalanmışsa artık birleştirilmez. Bu, rastgele daha kısa saat eşiği
seçmek yerine günlük fikstür sınırını korur. UTC gece yarısı Eastern
günü değişmiyorsa geçerli skoru tek başına geçersizleştirmez.

Geçersiz skorla tam hafta tahmini/hamle önerisi yerine, yeniden Yahoo
senkronizasyonu gerektiği bildirilir; kalan maç projeksiyonu ayrı etiketlenir.
Önsel ağırlıkları Wembanyama'nın bu maçına bakılarak değiştirilmedi.
Güncel 28 Ekim skoru geçerlidir ve güncel BLK %5,08 hesabı korunur.

Bu koruma gün değişimindeki atlamayı kapatır. Gün içindeki canlı maçların
kısmi skor ve kalan sürelerinin tam modellenmesini sağlamaz; mevcut motor
gün bazında çalışır. Bu nedenle sonuç, tüm canlı zaman sorunlarının veya
haftalık olasılık kalibrasyonunun çözüldüğü anlamına gelmez.

Regresyon testleri: 24 saatten yeni olsa bile önceki Eastern gününden
skoru reddetme; UTC günü değişirken aynı Eastern günündeki skoru kabul
etme. Tam test paketi 95 testle başarılı; Ruff kontrolü de başarılı.
