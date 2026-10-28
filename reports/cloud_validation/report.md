# Canlı bulut doğrulaması — 28 Ekim 2026

[Gerçek koşu](https://github.com/berkbhr/NbaFantasy/actions/runs/40689582772)
`b9e3e93d57d450fa267b912dc244ea74149350df` koduyla başarıyla tamamlandı.
Çalıştırma, Telegram bildirimi ve `nba-fantasy-bot` dalına kalıcı kayıt
adımları başarılıdır. Aynı kodun ayrı GitHub Offline model checks koşusu da geçti.

- Tahmin kimliği: `20261028T124149015310Z` (28 Ekim, Berlin 13:41:49).
- Telegram API bir mesajı kabul etti: mesaj kimliği 48, Berlin 13:41:58.
  Bu, API kabul kanıtıdır; kullanıcının mesajı okuduğu anlamına gelmez.
- Teslim makbuzundaki sıkıştırılmış tahmin SHA256'sı, uzak arşivle aynı.
- Arşivdeki tahminden yeniden üretilen Telegram metninin SHA256'sı,
  teslim makbuzuyla aynı. Renderer sürümü de doğrulandı.
- Koşudan önceki dört tahminin Git blob kimlikleri değişmedi.
- Yeni tahminler ve bildirim makbuzu bot dalında saklandı.

Makine tarafından toplanan kanıtlar `before_dispatch.json` ve `status.json`
içindedir. Erişim anahtarları veya Telegram sohbet kimliği bu raporlara alınmaz.

Henüz oynanmamış maçların gerçekleşen sonuçları beklenmektedir. Bu koşu
gelecekteki sonuçlarla eşleşmenin gerçekleştiği iddiasını taşımaz. Sonuç
eşleme, açık DNP, tekrar çalıştırma ve sonradan düzeltilen sonuçların eski
kayıtları bozmadan eklenmesi ayrı, izole testlerde doğrulandı. Canlı sonuçlar
geldikçe zaman damgalı tahminlerle eşleşecektir.

Yerel doğrulama: 84 unittest başarılı; Ruff kontrolü ve biçim kontrolü başarılı.
Tarihsel tuning'in matematiksel sonuçları ve kabul edilmeyen adayların
gerekçeleri `../rotation_tuning/report.md` ve
`../availability_tuning/report.md` dosyalarındadır. Ana modele otomatik
aday terfisi yapılmaz.
