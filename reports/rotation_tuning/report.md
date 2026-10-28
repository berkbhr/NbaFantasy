# Kontrollü rotasyon tuning'i ve kabul kararı

**Sonuç:** Ortalama dakika tahmininde anlamlı kazanç bulundu; bütün
belirsizlik denetimleri geçilmedi. Bu nedenle yeni katsayılar ana motora
otomatik alınmadı. Öğrenilen aday, gerçek zamanlı ayrı karşılaştırma koluna
eklendi. "Fark çıkmadı" ile "tam kabul şartları geçilmedi" aynı şey değildir.

## Veri ve zaman ayrımı

Önceki pazartesi/perşembe örneklemi bütün maç günlerine genişletildi.
327 günlük açık final kadro/DNP/pozisyon dosyasında 64.519 kayıt var;
bu yeni arşiv yaklaşık 1,35 MB. PDF biriktirilmedi. Eski arşivler kendi
deneylerinin hash'lerini korumak için değiştirilmedi.

Seçim: **2024–25, 19.208 oyuncu-maç**. Sabit aday değerlendirmesi:
**2025–26, 19.555 oyuncu-maç**. Sadece pozitif dakika gözlemleri dakika
skoruna girer; availability ayrı değerlendirilir. Önsel tamamlanmış
sezonlardan gelir. Hedef maçın final kadrosu/pozisyonu tahmin girdisi yapılmaz:
pozisyon ve kadro bilgisi ancak sonraki gün kullanılabilir. Değerlendirmede
geçmişten bilinen takım pozisyonlarının ortalama kapsamı %97,70'tir.

NBA raporunun gerçek başlığı öğlen kesiminden sonra olamaz; skorlanan
maçın tipoff'u kesimden sonra olmalıdır. G League satırları, canlı sağlık
beslemesindeki gibi tıbbi sakatlık fırsatı olarak kullanılmaz. Takım
değişiklikleri rapor/önceki gözlemlerle işlenir; ilk yeni takım gözlemi
eski takım rol geçmişiyle birleştirilmez.

İki sezon daha önce incelendiği için bu **retrospektif araştırmadır**.
Gerçek tarihsel Yahoo pozisyon uygunluğu ve işlemlerinin tam arşivi yoktur.
NBA üretim/dakika hatasının azalması daha fazla fantasy kategorisi
kazanılacağını tek başına kanıtlamaz.

## Neyin tuning'i yapıldı?

13 sabit aday: ek dakika havuzunun payı 0, 0,25, 0,50, 0,75, 1;
pozitif paylarda rol kanıtı yumuşatması kapalı / 3 / 8 maç. Sıfır pay
için gereksiz aynı adaylar tekrarlanmadı. Başlangıç, pay=1 ve rol kanıtı
azaltması kapalıdır. +2 sınırı bu çalışmanın seçilecek sabit cevabı değildir.

Ek dakika payı `gamma`, yeni sakatlığın zaten gözlenmiş role gömülmemiş
bölümüne uygulanır. İsteğe bağlı rol azaltması:

```
w = gözlenen_maç / (gözlenen_maç + k)
r = min(1, gözlenen_MPG / eski_rol_önseli)
rol_faktörü = 1 - w * (1 - r)
```

Böylece üç düşük süreli maç kalıcı rol kaybı diye kesinleştirilmez; veri
biriktikçe gözlenen rol daha fazla ağırlık taşır. Gözlenen dönem takım
değişiminde sıfırlanan rol geçmişidir. Bu faktör kalıcı düşüşün posterior
olasılığı değildir; deneyle ayarlanan bir fırsat paylaşım heuristiğidir.

Mevcut pozisyon yakınlığı, bireysel artış tavanları ve beklenen 240 dakika
bütçesi korunur. Bütün bu yapının parametreleri optimum bulundu iddiası
yoktur. Özellikle **gamma=0,25 sezon ağırlığı veya oynama ihtimali değildir**;
sadece sakatlıkla açılan ek dakika havuzunun katsayısıdır.

Ana ölçüt dakika **MSE**'sidir; ortalamayı hedefler. MAE medyanı hedeflediği
için tek başına ortalama üretim tahminini seçmekte kullanılmadı. MAE,
PTS MSE, eksik tahmin, dönem yarıları ve önemli alt gruplar koruma ölçütüdür.
Kabul eşikleri `protocol.json` dosyasında sonuçlardan önce yazılmıştır.

## Dondurulmuş adayın ortalama tahmin sonuçları

2024–25'te seçilen tek aday: **gamma=0,25, k=3**. Daha sonra başka bir
aday 2025–26 sonucuna bakılarak seçilmedi.

| 2025–26 | Başlangıç | Seçilen aday |
|---|---:|---:|
| Dakika MSE | 47,0599 | 41,1857 |
| Dakika MAE | 5,3385 | 4,9197 |
| Eksik tahmin edilen dakika, ortalama | 2,0062 | 2,1939 |
| PTS MSE | 36,5541 | 35,5935 |

MSE kazancı **%12,48**, MAE kazancı **%7,84**. Haftalık eşli bootstrap
MSE kazanç aralığı [4,663; 6,936] dakika²; iki dönem yarısında da kazanç
pozitif. Bunlar 2.000 takvim haftası bootstrap örneği, seed42 ile hesaplanır.
Haftadan uzun bağımlılık ve araştırmacının önceki sezon bilgisi tamamen
ortadan kaldırılmış değildir.

Düşük gözlenen rol grubunda 1.799 örnek vardır: MSE 55,463 → 46,175;
MAE 5,976 → 5,239. Buna karşılık eksik dakika tahmini 1,976 → 2,606 olur.
Güçlü önsel/düşük rol grubunda 100 örnek vardır; örneklem hâlâ sınırlıdır.
Kazançların yanında gerçek fırsatları düşük tahmin etme maliyeti sürer.

## Belirsizlik denetimi ve neden ana modele alınmadı?

Ham adayın %95 dakika aralığı kapsamı %94,02 → %93,27 geriledi.
Sadece daha düşük ortalama hata gördüğümüz için belirsizliği görmezden
gelmedik. Sabit ortalama adayı değiştirmeden ayrı bir kontrol yapıldı.

Tek bir varyans ölçeği her iki yöntemde de **yalnızca 2024–25** artıklarından
hesaplandı. Standartlaştırılmış kare artıkların ortalaması 10 gözlem gücüyle
1'e yumuşatılır; [1,2] sınırı güvenlik tercihidir ve bu koşuda etkinleşmedi.
Başlangıç ölçeği 1,215803; aday ölçeği 1,250402. Bunlar varyans çarpanıdır,
standart sapma çarpanı değildir. Gamma/Beta önsel güveni veya haftalık ortak
oran kovaryansı bu çarpanla çarpılmaz. Aynı işlemi başlangıca da uygulamak,
yalnızca adayı kalibre ederek haksız karşılaştırma yapmayı önler.

| Tüm değerlendirme örnekleri | Eski ham | Eski kalibre | Aday kalibre |
|---|---:|---:|---:|
| Normal moment NLL | 3,35544 | 3,35117 | 3,29484 |
| %95 kapsam | %94,02 | %95,86 | %95,49 |

Genelde skorlar iyileşiyor. Ancak ilk 10 gözlem grubunda %95 kapsam
eski ham yöntemde %96,03, kalibre adayda %97,05. Nominal %95'ten sapma
artışı **1,0245 yüzde puanı**, önceden konan 1 puanlık grup toleransını
çok küçük farkla aşıyor. Bu, adayın kötü olduğunun istatistiksel kanıtı
değildir; muhafazakâr kabul kuralının geçilmediği anlamına gelir.

Eşik sonucu gördükten sonra gevşetilmedi. Bu testteki erken/geç ayrımına
bakarak yeni grup varyansları denenip "başarı" aranmadı. Normal moment
kontrolü de tam haftalık olasılık kalibrasyonu veya bağımsız üretici model
doğrulaması değildir.

## Kullanım ve yeniden üretim

- `config/rotation_policy.json`: mevcut ana davranış; 1 / kapalı / varyans1.
- `config/rotation_candidate.json`: öğrenilmiş 0,25 / 3 / varyans1,250402;
  ana kullanım için kabul edilmediği ve nedeni açıkça yazılıdır.
- `rotation_candidate` gerçek zamanlı araştırma koludur; yeni sonuçlarla
  MSE, MAE, NLL ve özellikle ilk 10 gözlem kapsamı ayrı izlenir.
- `rotation_untuned` sabit başlangıcı korur; `low_role_cap2` de aynı eski
  başlangıç üstündedir. Senaryolara keyfî olasılık ağırlığı verilmez.

```
python -m src.tune_rotation
python -m src.check_rotation_safety
```

İlk komut tek başına ana ayarı değiştirmez. İkinci komut, bütün kabul
denetimlerinden sonra karar verir. `selection.json`, `frozen_selection.json`,
`frozen_variance_scales.json`, `uncertainty_safety.json` ve `decision.json`
ara sonuçları ve kaynak/veri hash'lerini tutar. Eski tahminler değiştirilmez.
