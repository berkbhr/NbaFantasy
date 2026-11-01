# Ekteki Yahoo okuyucularının karşılaştırılması

## Hata sınıflandırması ve 10 sayfalık FA kapsamı

Son ayar: FA taraması en fazla **10 ardışık sayfa** okur; son sayfaya daha erken
ulaşılırsa durur. Yalnız en yakın sonraki sayfa bağlantısı izlenir; son sayfa
bağlantısına atlayarak ilk 10 sayfanın yerine rastgele bir alt küme okunmaz.
Oyuncular Yahoo kimliğine göre tekilleştirilir. Bantta gerçek oyuncu/sayfa
sayısı ve tam/kısmi kapsam gösterilir. Ana tahmin ve takas raporlarında da
kısmi FA havuzunun anlamlı adayları kaçırabileceği belirtilir. İlk 250 adayın
sonrasının değersiz olduğu veya bu değişikliğin süreyi kesin yarıladığı
varsayılmaz.

Ağ hatası, zaman aşımı ve açık ret içermeyen 5xx yanıtları yalnız mevcut
çalıştırmayı durdurur; sonraki çalıştırmayı kilitleyen kalıcı kayıt yazmaz.
401/403/429 veya gerçek ret/CAPTCHA içeriği kalıcı engel korumasını korur.
503 yanıtının gövdesi de kontrol edilir: doğrulama sayfası varsa sıradan
sunucu hatası sayılmaz. Hiçbir hata türünde otomatik tekrar yapılmaz.
Önceden kaydedilmiş engel bayrağı otomatik silinmez.

`capture_metrics.yahoo_requests`, gerçek Yahoo isteği, tekilleştirme isabeti,
ağ/HTTP hatası ve ret sayılarını kaydeder. Bu sayaçlar yalnız yeni senkronda
dolar; bu geliştirmede canlı senkronizasyon çalıştırılmadı. Yeni dosya
oluşturmadan yapılan yedi bellek içi senaryoda geçici/kalıcı hata ayrımı,
sonraki çalıştırma ve bağımsız Response klonları kontrol edildi.

## Son güncelleme — kullanıcının tek tık isteği

Önceki ayrı tarama/18–40 sayfa ayarları aşağıdaki değişikliklerle yürürlükten
kalktı. Ana bookmarklet artık kadro, güncel skor, fikstür, işlemler ve FA
sayfalarını aynı çalıştırmada okur. Ortak üst sınır 96 istektir. URL
tekilleştirme, en fazla iki eşzamanlı istek ve ortak 400 ms başlangıç aralığı
kullanılır. Bu sayılar Yahoo'nun onayladığı güvenli eşikler değildir.

FA sayfalaması gerçek bağlantılar takip edilerek en fazla 30 sayfaya kadar
sürer; sekiz sayfa okundu diye eksiksiz havuz ilan edilmez. Fikstür okuyucusu
Schedule bağlantılarındaki `scmid` kimliğini ve tablo sahibinin açık matchup
kanıtını kullanır. Tarihler yine gerçek Yahoo dönemlerinden doğrulanır.
Erişim reddi veya CAPTCHA'da otomatik tekrar yoktur; devam eden istekler de
iptal edilir. Eski engel kaydı kendiliğinden silinmez.

Kullanıcının açık isteğiyle `tests/yahoo_transport.test.cjs` ve
`tests/test_yahoo_bookmarklet.py` silindi; CI referansı kaldırıldı. Bu değişiklik
sonrasında kalan 11 JavaScript testi geçti. Üretilen iki bookmarklet bellekten
Node ile derlendi; tekilleştirme, kilit ve 429 sonrasında sıranın durması
dosya oluşturmadan sahte yanıtlarla kontrol edildi. Yahoo'ya istek gönderilmedi.

Aşağıdaki karşılaştırma, önceki incelemenin tarihsel kaydıdır; ayrı fikstür
çalıştırma ve 18/40 sayfa kararları yukarıdaki ayarlarla değiştirilmiştir.

31 Ekim 2026. İncelenen ekler: `gemini-code-1793399099070.py` ve
`gemini-code-1793398848860.js`. Dosyalar doğrudan mevcut sürümün üzerine
kopyalanmadı; aşağıdaki kararlar kod karşılaştırmasına dayanır.

| Öneri | Karar ve gerekçe |
|---|---|
| Aynı GET adresini tek istekle okumak | Korundu. Her tüketici bağımsız okunabilir yanıt alır. |
| Dört paralel kanal, 160–180 ms aralık, 160 sayfa | Alınmadı. Önceki erişim reddinden sonra daha yoğun tarama uygun değil. Tek kuyruk ve sınırlı okuma korunur. Bunlar Yahoo tarafından onaylanmış güvenli eşikler olarak sunulmaz. |
| 429/503 sonrası otomatik tekrar | Alınmadı. İlk ret veya doğrulama sayfasında bütün kuyruk durur. |
| Önceki engel kaydını otomatik silmek | Alınmadı. Okuyucu erişim engelini kendiliğinden sıfırlamaz. |
| Kuyruk boşalınca çalışma kilidini kaldırmak | Düzeltilerek uygulandı. Geçici kuyruk boşluğu yerine bookmarklet'in tamamının `finally` bölümünde kaldırılır. Böylece aşamalar arasında ikinci tarama başlayamaz. |
| Hafta bilinmiyorsa 1 yazmak | Alınmadı. Hafta doğrulanamadığında kayıt yenilenmez. |
| Görünen DOM'u güncel canlı skor saymak | Alınmadı. Eski sekmeye yeni yakalama zamanı verilmez. |
| Sekiz FA sayfasını eksiksiz havuz saymak | Alınmadı. Sabit sayıda sayfa bütün havuzun okunduğunu kanıtlamaz. |
| Waiver metnini yalnız birkaç HTML niteliğinden okumak | Alınmadı. Mevcut tooltip/waiver kanıtlarını kaybetme riski var. |
| Normal senkronda otomatik ek fikstür taraması | Alınmadı. Kadro ve fikstür işlemleri ayrı kalır. |

Ek düzeltmeler: yalnız fikstür modundaki 14 oyuncu kadrosu isteği kaldırıldı.
İstek kuyruğunun dışından ağ trafiği üreten iframe yedeği devre dışı bırakıldı.
Normal modun 18 ve yalnız fikstür modunun 40 sayfalık üst sınırları ayrı tutuldu;
üst sınır dolarsa eksik veri tamamlanmış gibi kaydedilmez. Kayıtlı güncel
haftalar tekrar taranmaz.

Doğrulama: **16 JavaScript testi**, **19 Python fikstür testi** ve gerçek
sunulan iki bookmarklet betiğinin Node sözdizimi kontrolü geçti. Çift tıklama,
HTTP 429/403, HTTP 200 içinde ret sayfası, GET tekilleştirme, çalışma kilidinin
serbest bırakılması ve ret bilgisinin korunması kontrol edildi. Python Ruff
kontrolü de geçti.

Bu incelemede Yahoo'ya istek gönderilmedi, bookmarklet çalıştırılmadı ve canlı
veriler değiştirilmedi. Testler mevcut erişim engelinin kalktığını veya canlı
HTML uyumluluğunun bütünüyle doğrulandığını göstermez. Yahoo normal gezinmede
de ret gösteriyorsa bookmarklet yeniden çalıştırılmamalıdır. Güncel Python
kodunu yüklemek için köprü yeniden başlatılmalıdır.
