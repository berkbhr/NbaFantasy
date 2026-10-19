# 🏀 2026-27 Yahoo NBA Fantasy (9-Cat H2H) — 8. Sıra (Slot #8) Gerçekçi Draft & Tam Sezon Simülasyon Raporu

## 1. Yönetici Özeti & Metodoloji

Bu rapor, **2026-27 NBA Sezonu** resmi fikstürü (`1,217 maç`, `20 Ekim 2026 – 11 Nisan 2027`, `22 Fantezi Haftası`) ve **gerçekçi Yahoo 12-Takım Snake Draft ADP konsensüsü** kullanılarak **8. sıradan (`Slot #8`, 1. Tur #8 ve 2. Tur #17 dönüşü)** gerçekleştirilen **8 farklı gerçekçi masa senaryosunun** uçtan uca simülasyon sonuçlarını içerir.

### Gerçekçilik Kısıtları ve Kalibrasyonlar
1. **Gerçekçi Yahoo İlk 7 Konsensüsü (`ADP_Z`):**
   - *Nikola Jokić (#1), Victor Wembanyama (#2), Shai Gilgeous-Alexander (#3), Luka Dončić (#4)* ve *Giannis Antetokounmpo (#5)* konsensüs ilk 5 süperstarı olarak masada 8. sıraya **asla gerçek dışı şekilde düşmez** (yalnızca Senaryo 8'de Giannis'in FT% çekincesiyle #8'e kaydığı ekstrem "What-If" senaryosu test edilmiştir).
   - *Jamal Murray*, *Kevin Durant* veya 2. tur oyuncuları hiçbir senaryoda *Luka Dončić* veya *SGA* gibi ilk 5 süperstarlarının önüne geçmez; *Jamal Murray* gerçekçi biçimde 2. tur ortasında (`#15–#19` bandı) seçilir.
2. **Dinamik Marjinal Punt & Sinerji Motoru ([`LiveDraftAssistant`](file:///D:/Github%20Projects/NbaFantasy/src/live_draft_assistant.py)):**
   - Her seçimde ileriye dönük (`Rollout`) simülasyon, tam kadro varyans ölçeğini (`sqrt(2 * 13)`) ve yapısal 1-kategori punt esnekliğini (`Punt AST`, `Punt BLK` veya `Punt FT%`) kullanarak ilk turda seçilen çapa oyuncunun (`Anchor`) etrafında en yüksek H2H eşleşme kazanma olasılığını (`Expected Matchup Win Probability`) veren kadroyu inşa eder.
   - Çoklu kategori çöküşünü önlemek için temel hacim/verimlilik kategorilerine (`FG%`, `REB`, `PTS`) taban koruma (`core_floor_penalty`) uygulanmıştır.
3. **22 Haftalık Tam Sezon + Bayesyen Waiver Simülasyonu ([`simulate_slot8_scenarios.py`](file:///D:/Github%20Projects/NbaFantasy/src/simulate_slot8_scenarios.py)):**
   - Draft tamamlandıktan sonra 12 takımın tamamı **2026-27 NBA gerçek maç takvimi** üzerinden **22 hafta boyunca** karşılıklı H2H maçları oynar.
   - Her senaryo için **100 bağımsız Monte Carlo sezonu (toplam 800 tam sezon / 17,600 fantezi haftası)** koşulmuş; haftalık sakatlık/dinlendirme (`DNP`) dalgalanmaları, günlük 10 kişilik aktif kadro optimizasyonu (`PG, SG, G, SF, PF, F, C, C, UTIL, UTIL`) ve [`FantasyAIModel.get_bayesian_waiver_moves`](file:///D:/Github%20Projects/NbaFantasy/src/model_ai.py#L430-L535) üzerinden haftalık Bayesyen serbest oyuncu (`Waiver/Streaming`) hamleleri simüle edilmiştir.

---

## 2. Tüm Senaryoların Karşılaştırmalı Özet Tablosu

| Senaryo | 1. Tur (#8) Çapa Seçimimiz | 2. Tur (#17) Dönüş Seçimimiz | Aktif Punt Stratejisi | Draft Sonu Beklenen Kat. (`E[Wins]/9`) | Sezon Sonu Sıralaması (Beklenen Sıra) | Ort. Sıra (`100 Sezon`) | Şampiyonluk / İlk 3 Oranı | Haftalık Maç Galibiyeti (`G-M`) | Kategori Galibiyet Oranı |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Senaryo 1** | **Tyrese Maxey** (`PHI - G`) | **Karl-Anthony Towns** (`NYK - C/F`) | `Punt AST` | **5.17 / 9.0** | **🏆 #1 / 12** | `3.10` *(Med: 2)* | **%30 Şampiyon** / **%66 İlk 3** | **13.4G - 8.6M (%60.8)** | **%54.4** (`107.7G - 90.3M`) |
| **Senaryo 6** | **Kevin Durant** (`HOU - F`) | **Bam Adebayo** (`MIA - C/F`) | `Punt AST` | **5.06 / 9.0** | **🥉 #3 / 12** | `4.52` *(Med: 4)* | **%12 Şampiyon** / **%47 İlk 3** | **12.2G - 9.8M (%55.4)** | **%52.0** (`103.0G - 95.0M`) |
| **Senaryo 8** | **Giannis Antetokounmpo** (`MIA - F`) | **Jamal Murray** (`DEN - G`) | `Punt FT% & STL` | **4.92 / 9.0** *(4.70/8)* | **🥉 #3 / 12** | `4.65` *(Med: 4)* | **%17 Şampiyon** / **%40 İlk 3** | **12.0G - 10.0M (%54.5)** | **%52.1** (`103.2G - 94.8M`) |
| **Senaryo 4** | **Donovan Mitchell** (`CLE - G`) | **Jalen Duren** (`DET - C`) | `Punt AST` | **5.01 / 9.0** | **#4 / 12** | `5.58` *(Med: 5)* | **%16 Şampiyon** / **%36 İlk 3** | **11.7G - 10.3M (%53.0)** | **%51.3** (`101.6G - 96.4M`) |
| **Senaryo 3** | **Cade Cunningham** (`DET - G`) | **Karl-Anthony Towns** (`NYK - C/F`) | `Punt BLK` | **4.89 / 9.0** | **#4 / 12** | `5.99` *(Med: 6)* | **%5 Şampiyon** / **%28 İlk 3** | **11.4G - 10.6M (%52.0)** | **%50.6** (`100.2G - 97.8M`) |
| **Senaryo 5** | **Anthony Edwards** (`MIN - G`) | **Jalen Duren** (`DET - C`) | `Punt AST` | **4.94 / 9.0** | **#4 / 12** | `6.10` *(Med: 6)* | **%10 Şampiyon** / **%27 İlk 3** | **11.0G - 11.0M (%50.0)** | **%50.4** (`99.7G - 98.3M`) |
| **Senaryo 2** | **Scottie Barnes** (`TOR - F/G`) | **Karl-Anthony Towns** (`NYK - C/F`) | `Punt BLK` | **4.99 / 9.0** | **#6 / 12** | `6.26` *(Med: 6)* | **%10 Şampiyon** / **%23 İlk 3** | **11.4G - 10.6M (%51.8)** | **%50.3** (`99.6G - 98.4M`) |
| **Senaryo 7** | **Jalen Johnson** (`ATL - F`) | **Bam Adebayo** (`MIA - C/F`) | `Punt BLK` *(veya Dengeli)* | **5.07 / 9.0** | **#6 / 12** *(Chet ile **#1/12**)* | `6.65` *(Med: 7)* | **%9 Şampiyon** / **%19 İlk 3** | **10.9G - 11.1M (%49.4)** | **%49.8** (`98.6G - 99.4M`) |

> **Kritik Stratejik Çıkarım:** 8. sıradan (`Slot #8`) **en yüksek şampiyonluk (%30) ve #1/12 sezon sonu liderliği** getiren kurgu, 1. turda elit üçlük/sayı/FT%/düşük top kaybı sağlayan bir Guard/Kanat (**Tyrese Maxey**, **Kevin Durant** veya **Donovan Mitchell**) seçip 2. ve 3. turlarda elit şutör/blokçu uzunlarla (**Karl-Anthony Towns + Chet Holmgren** veya **Bam Adebayo + Donovan Clingan**) **`Punt AST` (Asist Punt)** omurgasına oturmaktır.

---

## 3. Senaryo Bazlı Detaylı Draft Kadroları ve Sezon Sonu Raporları

---

### 🏆 SENARYO 1: Standart Yahoo ADP Masası (Tyrese Maxey Çapası) — **Sezon Sonu: #1 / 12**

* **Senaryo Hikayesi:** İlk 5 sıra konsensüs süperstarları (*Jokić, Wembanyama, SGA, Dončić, Giannis*) alır. 6. sıradaki menajer *Anthony Edwards*'a, 7. sıradaki menajer *Cade Cunningham*'a yönelir ve #8'de bize **Tyrese Maxey** kalır.
* **Bizden Önceki İlk 7 Seçim:**
  1. `#1` Nikola Jokić (`DEN - C`)
  2. `#2` Victor Wembanyama (`SAS - C`)
  3. `#3` Shai Gilgeous-Alexander (`OKC - G`)
  4. `#4` Luka Dončić (`LAL - G`)
  5. `#5` Giannis Antetokounmpo (`MIA - F`)
  6. `#6` Anthony Edwards (`MIN - G`)
  7. `#7` Cade Cunningham (`DET - G`)

#### 📋 13 Turluk Draft Kadromuz (Slot #8)
| Tur | Genel Sıra | Seçilen Oyuncu | Takım / Pozisyon | DraftZ | Seçim Anı `E[Wins]` | Rol ve Sinerji Açıklaması |
| :---: | :---: | :--- | :---: | :---: | :---: | :--- |
| **1** | **#8** | **Tyrese Maxey** | `PHI - G` | `+5.53` | `4.677` | Elit PTS, FG3M, FT%, STL ve çok düşük TOV çapası |
| **2** | **#17** | **Karl-Anthony Towns** | `NYK - C/F` | `+3.43` | `4.777` | Elit REB, FT%, FG3M ve PTS ile `Punt AST` uzun ikilisi |
| **3** | **#32** | **Chet Holmgren** | `OKC - C/F` | `+2.99` | `4.918` | BLK, REB ve FG% sigortası; KAT ile kusursuz ikiz kuleler |
| **4** | **#41** | **OG Anunoby** | `NYK - F/G` | `+1.94` | `4.980` | Elit STL, FG3M ve düşük TOV kanat kilidi |
| **5** | **#56** | **DeMar DeRozan** | `DEN - G/F` | `+1.35` | `5.049` | Elit FT% çıpası, orta mesafe FG% ve düşük TOV |
| **6** | **#65** | **Kon Knueppel** | `CHA - G/F` | `+2.02` | `5.044` | Yüksek üçlük hacmi, elit FT% ve düşük TOV |
| **7** | **#80** | **Jabari Smith Jr.** | `HOU - F` | `+1.67` | `5.060` | Stretch-4: REB, FG3M, BLK ve FT% sinerjisi |
| **8** | **#89** | **Myles Turner** | `MIL - C/F` | `+1.51` | `5.106` | BLK ve FG3M kategorilerini tamamen domine eden hamle |
| **9** | **#104** | **Toumani Camara** | `POR - F` | `+0.60` | `5.140` | Savunma uzmanı (STL + REB + düşük TOV) |
| **10** | **#113** | **Ayo Dosunmu** | `MIN - G` | `+1.07` | `5.146` | Yüksek FG% guard, STL ve verimli rotasyon |
| **11** | **#128** | **Royce O'Neale** | `CHA - F` | `+0.56` | `5.158` | 3&D kanat (FG3M, STL, REB, düşük TOV) |
| **12** | **#137** | **Moussa Diabaté** | `CHA - F` | `+0.87` | `5.161` | Yüksek REB, FG% ve BLK derinliği |
| **13** | **#152** | **Keldon Johnson** | `SAS - F/G` | `+0.60` | `5.168` | PTS, REB ve yüksek FG% bench katkısı |

#### 📊 Sezon Sonu Performansı ve Kategori Karnesi
* **Sezon Sonu Sıralaması:** **#1 / 12** (`Ort. Sıra: 3.10`, `Medyan: 2`, `%30 Şampiyonluk`, `%66 İlk 3`)
* **22 Haftalık Maç Karnesi:** **13.4 Galibiyet – 8.6 Mağlubiyet (`%60.8`)**
* **Kategori Bazlı Kazanma Oranları (22 Hafta Ortalaması):**
  * **FG3M:** `%74.0` (Dominant) | **FT%:** `%62.3` (Çok Güçlü) | **TOV:** `%60.4` (Çok Güçlü) | **BLK:** `%59.4` (Güçlü) | **REB:** `%57.8` (Güçlü) | **STL:** `%55.2` (Güçlü) | **PTS:** `%52.0` (Artıda) | **FG%:** `%41.9` (Rekabetçi) | **AST:** `%26.5` *(Planlı Punt)*
* **Örnek Sezon İçi Bayesyen Waiver Hamleleri:**
  * *Hafta 1:* `-Keldon Johnson` $\rightarrow$ `+Mitchell Robinson` (`Δ E[Wins]: +0.043`, FG% ve REB takviyesi)
  * *Hafta 2:* `-Mitchell Robinson` $\rightarrow$ `+Peyton Watson` (`Δ E[Wins]: +0.025`, BLK ve STL streaming)

---

### 🥉 SENARYO 6: Yüksek Verimli Süperstar (Kevin Durant Çapası) — **Sezon Sonu: #3 / 12**

* **Senaryo Hikayesi:** İlk 7'de *Tyrese Maxey (#6)* ve *Anthony Edwards (#7)* seçilir. 8. sırada elit verimlilik, sayı, üçlük ve blok katkısı sunan **Kevin Durant** (`HOU - F`) seçilir ve 2. tur dönüşünde **Bam Adebayo** (`MIA - C/F`) ile eşleştirilir.
* **Bizden Önceki İlk 7 Seçim:** `#1 Jokić, #2 Wembanyama, #3 SGA, #4 Luka Dončić, #5 Giannis, #6 Tyrese Maxey, #7 Anthony Edwards`

#### 📋 13 Turluk Draft Kadromuz (Slot #8)
| Tur | Genel Sıra | Seçilen Oyuncu | Takım / Pozisyon | DraftZ | Seçim Anı `E[Wins]` | Rol ve Sinerji Açıklaması |
| :---: | :---: | :--- | :---: | :---: | :---: | :--- |
| **1** | **#8** | **Kevin Durant** | `HOU - F` | `+3.47` | `4.696` | Elit PTS, FT%, FG%, FG3M ve BLK kanat çapası |
| **2** | **#17** | **Bam Adebayo** | `MIA - C/F` | `+2.97` | `4.777` | Elit REB, STL ve FT% bozmayan mobil pivot |
| **3** | **#32** | **Donovan Clingan** | `POR - C` | `+3.62` | `4.859` | Elit BLK, REB ve FG% çapa uzunu |
| **4** | **#41** | **Mikal Bridges** | `NYK - G/F` | `+2.65` | `4.864` | Demir adam (82 maç), STL, FG3M, FT% ve düşük TOV |
| **5** | **#56** | **Brandon Ingram** | `TOR - F` | `+2.04` | `4.922` | PTS, FT% ve kanat skor üretimi |
| **6** | **#65** | **Kon Knueppel** | `CHA - G/F` | `+2.02` | `4.970` | Elit FG3M ve FT% keskin nişancı |
| **7** | **#80** | **Naz Reid** | `CHA - C/F` | `+1.84` | `4.996` | Stretch-Big: FG3M, REB, BLK katkısı |
| **8** | **#89** | **Andrew Wiggins** | `MIA - F` | `+1.41` | `5.000` | FG3M, PTS, BLK ve düşük TOV |
| **9** | **#104** | **Julian Champagnie** | `SAS - F` | `+1.53` | `5.041` | Yüksek hacimli FG3M, REB, STL ve düşük TOV |
| **10** | **#113** | **Ayo Dosunmu** | `MIN - G` | `+1.07` | `5.039` | Verimli Guard (FG%, STL) |
| **11** | **#128** | **Tobias Harris** | `DET - F` | `+1.06` | `5.046` | İstikrarlı FT%, REB, PTS ve düşük TOV |
| **12** | **#137** | **Royce O'Neale** | `CHA - F` | `+0.56` | `5.052` | 3&D kanat derinliği |
| **13** | **#152** | **Sandro Mamukelashvili** | `LAL - F/C` | `+1.35` | `5.059` | Yüksek verimli F/C rotasyon parçası |

#### 📊 Sezon Sonu Performansı ve Kategori Karnesi
* **Sezon Sonu Sıralaması:** **#3 / 12** (`Ort. Sıra: 4.52`, `Medyan: 4`, `%12 Şampiyonluk`, `%47 İlk 3`)
* **22 Haftalık Maç Karnesi:** **12.2 Galibiyet – 9.8 Mağlubiyet (`%55.4`)**
* **Kategori Bazlı Kazanma Oranları:**
  * **FG3M:** `%72.0` | **BLK:** `%58.2` | **TOV:** `%57.0` | **REB:** `%55.8` | **FT%:** `%55.8` | **PTS:** `%52.3` | **STL:** `%44.3` | **FG%:** `%40.6` | **AST:** `%32.0` *(Planlı Punt)*

---

### 🥉 SENARYO 8: Agresif Punt FT% Sinerjisi (Giannis Antetokounmpo #8'e Düşerse) — **Sezon Sonu: #3 / 12**

* **Senaryo Hikayesi:** İlk 7'deki menajerler serbest atış (`FT%`) yüzdesini bozmak istemedikleri için *Tyrese Maxey (#5), Anthony Edwards (#6)* ve *Cade Cunningham (#7)* seçerler ve **Giannis Antetokounmpo** 8. sıraya düşer. Modelimiz anında otomatik **`Punt FT%`** moduna geçerek *Giannis + Evan Mobley + Donovan Clingan + Zion Williamson* dörtlüsünü kurar.
* **Bizden Önceki İlk 7 Seçim:** `#1 Jokić, #2 Wembanyama, #3 SGA, #4 Luka Dončić, #5 Tyrese Maxey, #6 Anthony Edwards, #7 Cade Cunningham`

#### 📋 13 Turluk Draft Kadromuz (Slot #8)
| Tur | Genel Sıra | Seçilen Oyuncu | Takım / Pozisyon | DraftZ | Seçim Anı `E[Wins]` | Rol ve Sinerji Açıklaması |
| :---: | :---: | :--- | :---: | :---: | :---: | :--- |
| **1** | **#8** | **Giannis Antetokounmpo** | `MIA - F` | `+3.43` | `4.544` | `Punt FT%` süperstar çapası (PTS, REB, FG%, AST, BLK) |
| **2** | **#17** | **Jamal Murray** | `DEN - G` | `+2.52` | `4.700` | Giannis'in yanına elit FG3M, PTS ve AST tamamlayıcısı |
| **3** | **#32** | **Evan Mobley** | `CLE - C` | `+2.65` | `4.756` | `Punt FT%` içinde 1. tur değerine çıkan elit BLK, REB, FG% uzunu |
| **4** | **#41** | **Donovan Clingan** | `POR - C` | `+3.62` | `4.828` | FG%, REB ve BLK kategorilerini tamamen kilitleyen kule |
| **5** | **#56** | **Brandon Ingram** | `TOR - F` | `+2.04` | `4.843` | PTS ve AST üreten skorer kanat |
| **6** | **#65** | **Payton Pritchard** | `BOS - G` | `+2.05` | `4.887` | Giannis/Mobley ikilisinin üçlük (`FG3M`) açığını kapatan guard |
| **7** | **#80** | **Matas Buzelis** | `CHI - F` | `+1.41` | `4.883` | BLK, FG3M ve REB katkısı veren genç kanat |
| **8** | **#89** | **Naz Reid** | `CHA - C/F` | `+1.84` | `4.886` | Üçlükçü uzun (FG3M, REB, BLK) |
| **9** | **#104** | **Brandin Podziemski** | `GSW - G` | `+0.94` | `4.892` | REB, AST ve FG3M destekli guard |
| **10** | **#113** | **Zion Williamson** | `NOP - F` | `+1.29` | `4.902` | `Punt FT%` kurgusunda 10. turdan devasa PTS ve FG% (`%58+`) çalımı |
| **11** | **#128** | **Royce O'Neale** | `CHA - F` | `+0.56` | `4.909` | FG3M ve REB |
| **12** | **#137** | **Sandro Mamukelashvili** | `LAL - F/C` | `+1.35` | `4.916` | Yüksek FG% ve REB |
| **13** | **#152** | **Duncan Robinson** | `DET - F` | `-0.41` | `4.917` | Saf üçlük (`FG3M`) uzmanı |

#### 📊 Sezon Sonu Performansı ve Kategori Karnesi
* **Sezon Sonu Sıralaması:** **#3 / 12** (`Ort. Sıra: 4.65`, `Medyan: 4`, `%17 Şampiyonluk`, `%40 İlk 3`)
* **22 Haftalık Maç Karnesi:** **12.0 Galibiyet – 10.0 Mağlubiyet (`%54.5`)**
* **Kategori Bazlı Kazanma Oranları:**
  * **PTS:** `%63.2` | **BLK:** `%62.9` | **REB:** `%62.6` | **FG3M:** `%59.7` | **FG%:** `%58.0` | **AST:** `%53.7` | **TOV:** `%45.2` | **STL:** `%41.2` | **FT%:** `%22.5` *(Planlı Punt)*

---

### 🏅 SENARYO 4: Patlayıcı Skorer & Top Çalma (Donovan Mitchell Çapası) — **Sezon Sonu: #4 / 12**

* **Senaryo Hikayesi:** İlk 7'de *Tyrese Maxey (#6)* ve *Scottie Barnes (#7)* seçilir. 8. sırada elit sayı, üçlük ve top çalma (`STL`) üreten **Donovan Mitchell** (`CLE - G`) alınır; 2. tur dönüşünde **Jalen Duren** (`DET - C`) ile ribaund ve saha içi isabet (`FG%`) dengelenir.
* **Bizden Önceki İlk 7 Seçim:** `#1 Jokić, #2 Wembanyama, #3 SGA, #4 Luka Dončić, #5 Giannis, #6 Tyrese Maxey, #7 Scottie Barnes`

#### 📋 13 Turluk Draft Kadromuz (Slot #8)
* **R1 (#8):** Donovan Mitchell (`CLE - G`)
* **R2 (#17):** Jalen Duren (`DET - C`)
* **R3 (#32):** Desmond Bane (`ORL - G`)
* **R4 (#41):** Mikal Bridges (`NYK - G/F`)
* **R5 (#56):** VJ Edgecombe (`PHI - G`)
* **R6 (#65):** Kel'el Ware (`MIL - C`)
* **R7 (#80):** Jabari Smith Jr. (`HOU - F`)
* **R8 (#89):** Naz Reid (`CHA - C/F`)
* **R9 (#104):** Brook Lopez (`LAC - C`)
* **R10 (#113):** Ayo Dosunmu (`MIN - G`)
* **R11 (#128):** Tobias Harris (`DET - F`)
* **R12 (#137):** Kyle Filipowski (`UTA - C`)
* **R13 (#152):** Bobby Portis Jr. (`MIA - F`)
* **Aktif Punt:** `Punt AST` (`E[Wins]: 5.011 / 9.0`)
* **Sezon Sonu Sıralaması:** **#4 / 12** (`Ort. Sıra: 5.58`, `Medyan: 5`, `%16 Şampiyonluk`, `%36 İlk 3` | `Maç: 11.7G - 10.3M (%53.0)`)
* **Kategori Kazanma Oranları:** `TOV %70.0, FG3M %56.8, REB %55.4, BLK %54.2, FT% %54.1, FG% %51.3, STL %48.6, PTS %43.8, AST %27.4`

---

### 🏅 SENARYO 3: Elit Oyun Kurucu Çapası (Cade Cunningham Çapası) — **Sezon Sonu: #4 / 12**

* **Senaryo Hikayesi:** 6. sırada *Tyrese Maxey*, 7. sırada *Kevin Durant* seçilir ve #8'de bize **Cade Cunningham** (`DET - G`) kalır. Model, Cade'in elit `PTS + AST + FG3M + FT%` profilini **Karl-Anthony Towns** (`#17`) ve **Desmond Bane** (`#32`) ile birleştirerek **`Punt BLK`** kurgusuna yönelir.
* **Bizden Önceki İlk 7 Seçim:** `#1 Jokić, #2 Wembanyama, #3 SGA, #4 Luka Dončić, #5 Giannis, #6 Tyrese Maxey, #7 Kevin Durant`

#### 📋 13 Turluk Draft Kadromuz (Slot #8)
* **R1 (#8):** Cade Cunningham (`DET - G`)
* **R2 (#17):** Karl-Anthony Towns (`NYK - C/F`)
* **R3 (#32):** Desmond Bane (`ORL - G`)
* **R4 (#41):** Kon Knueppel (`CHA - G/F`)
* **R5 (#56):** VJ Edgecombe (`PHI - G`)
* **R6 (#65):** Brandon Ingram (`TOR - F`)
* **R7 (#80):** Christian Braun (`DEN - G`)
* **R8 (#89):** Saddiq Bey (`NOP - F`)
* **R9 (#104):** Wendell Carter Jr. (`ORL - C/F`)
* **R10 (#113):** Ayo Dosunmu (`MIN - G`)
* **R11 (#128):** Julian Champagnie (`SAS - F`)
* **R12 (#137):** Royce O'Neale (`CHA - F`)
* **R13 (#152):** Sandro Mamukelashvili (`LAL - F/C`)
* **Aktif Punt:** `Punt BLK` (`E[Wins]: 4.892 / 9.0`)
* **Sezon Sonu Sıralaması:** **#4 / 12** (`Ort. Sıra: 5.99`, `Medyan: 6`, `%28 İlk 3` | `Maç: 11.4G - 10.6M (%52.0)`)
* **Kategori Kazanma Oranları:** `FG3M %68.6, FT% %66.7, PTS %56.4, AST %54.6, REB %49.6, STL %49.0, TOV %47.9, FG% %38.7, BLK %24.1`

---

### 🏅 SENARYO 5: Anthony Edwards Çapası (Yüksek Hacimli Skorer Guard) — **Sezon Sonu: #4 / 12**

* **Senaryo Hikayesi:** İlk 7'de *Maxey* ve *Durant* gider; #8'de **Anthony Edwards** (`MIN - G`) seçilir. 2. turda **Jalen Duren** (`#17`) ve 3. turda **Chet Holmgren** (`#32`) ile pota altı (`REB, BLK, FG%`) tahkim edilir.
* **Bizden Önceki İlk 7 Seçim:** `#1 Jokić, #2 Wembanyama, #3 SGA, #4 Luka Dončić, #5 Giannis, #6 Tyrese Maxey, #7 Kevin Durant`

#### 📋 13 Turluk Draft Kadromuz (Slot #8)
* **R1 (#8):** Anthony Edwards (`MIN - G`)
* **R2 (#17):** Jalen Duren (`DET - C`)
* **R3 (#32):** Chet Holmgren (`OKC - C/F`)
* **R4 (#41):** Nickeil Alexander-Walker (`ATL - G`)
* **R5 (#56):** Tyler Herro (`MIL - G`)
* **R6 (#65):** Jaden McDaniels (`MIN - F`)
* **R7 (#80):** Jabari Smith Jr. (`HOU - F`)
* **R8 (#89):** Naz Reid (`CHA - C/F`)
* **R9 (#104):** Brook Lopez (`LAC - C`)
* **R10 (#113):** Andrew Wiggins (`MIA - F`)
* **R11 (#128):** Royce O'Neale (`CHA - F`)
* **R12 (#137):** Bobby Portis Jr. (`MIA - F`)
* **R13 (#152):** Keldon Johnson (`SAS - F/G`)
* **Aktif Punt:** `Punt AST` (`E[Wins]: 4.935 / 9.0`)
* **Sezon Sonu Sıralaması:** **#4 / 12** (`Ort. Sıra: 6.10`, `Medyan: 6`, `%10 Şampiyonluk`, `%27 İlk 3` | `Maç: 11.0G - 11.0M (%50.0)`)
* **Kategori Kazanma Oranları:** `BLK %71.0, FG3M %67.3, TOV %65.8, FT% %52.0, REB %50.1, FG% %49.5, PTS %44.5, STL %43.8, AST %9.3`

---

### 🏅 SENARYO 2: Guard Erimesi & All-Around Kanat (Scottie Barnes Çapası) — **Sezon Sonu: #6 / 12**

* **Senaryo Hikayesi:** İlk 7'de tüm elit guardlar (*SGA, Dončić, Maxey, Cade*) tükenir. #8'de çok yönlü kanat **Scottie Barnes** (`TOR - F/G`) seçilir; 2. turda **Karl-Anthony Towns** (`#17`) ve 3. turda **Desmond Bane** (`#32`) ile **`Punt BLK`** kadrosu kurulur.
* **Bizden Önceki İlk 7 Seçim:** `#1 Jokić, #2 Wembanyama, #3 SGA, #4 Luka Dončić, #5 Giannis, #6 Tyrese Maxey, #7 Cade Cunningham`

#### 📋 13 Turluk Draft Kadromuz (Slot #8)
* **R1 (#8):** Scottie Barnes (`TOR - F/G`)
* **R2 (#17):** Karl-Anthony Towns (`NYK - C/F`)
* **R3 (#32):** Desmond Bane (`ORL - G`)
* **R4 (#41):** Payton Pritchard (`BOS - G`)
* **R5 (#56):** VJ Edgecombe (`PHI - G`)
* **R6 (#65):** Josh Hart (`NYK - G`)
* **R7 (#80):** Nikola Vučević (`ORL - C`)
* **R8 (#89):** Miles Bridges (`PHX - F`)
* **R9 (#104):** Julian Champagnie (`SAS - F`)
* **R10 (#113):** Christian Braun (`DEN - G`)
* **R11 (#128):** Davion Mitchell (`MIA - G`)
* **R12 (#137):** Devin Vassell (`SAS - G/F`)
* **R13 (#152):** Sandro Mamukelashvili (`LAL - F/C`)
* **Aktif Punt:** `Punt BLK` (`E[Wins]: 4.987 / 9.0`)
* **Sezon Sonu Sıralaması:** **#6 / 12 (Playoff)** (`Ort. Sıra: 6.26`, `Medyan: 6`, `%10 Şampiyonluk`, `%23 İlk 3` | `Maç: 11.4G - 10.6M (%51.8)`)
* **Kategori Kazanma Oranları:** `FT% %64.5, TOV %63.6, FG3M %61.6, AST %56.9, REB %51.5, STL %47.1, PTS %42.0, FG% %39.9, BLK %25.5`

---

### 🏅 SENARYO 7: Modern Point-Forward Çapası (Jalen Johnson Çapası) — **Sezon Sonu: #6 / 12** *(Blok Korunursa **#1 / 12**)*

* **Senaryo Hikayesi:** 8. sırada Atlanta'nın point-forward yıldızı **Jalen Johnson** (`ATL - F`) seçilir.
* **Önemli Taktiksel Bulgumuz:** Jalen Johnson seçildiğinde 2. ve 3. turlarda `Punt BLK` yapıp *Bam Adebayo + Desmond Bane* ikilisine gidilirse takım `FG%` ve `BLK` kategorilerinde geriye düşerek sezonu **#6 / 12** sırada bitirmektedir. Ancak Jalen Johnson'ın yanına 2./3. turda **Chet Holmgren** veya **Onyeka Okongwu + Donovan Clingan** gibi blokçu/yüksek FG% uzunlar eklendiğinde (bkz. `Dengeli / Soft Punt FT%` varyasyonu), Jalen Johnson çapası **%57.9 haftalık galibiyet oranıyla sezonu #1 / 12 sırada** tamamlamaktadır!
* **Bizden Önceki İlk 7 Seçim:** `#1 Jokić, #2 Wembanyama, #3 SGA, #4 Luka Dončić, #5 Giannis, #6 Tyrese Maxey, #7 Donovan Mitchell`
* **Kadromuz (`Punt BLK` Varyasyonu):** `R1 (#8) Jalen Johnson, R2 (#17) Bam Adebayo, R3 (#32) Desmond Bane, R4 (#41) Mikal Bridges, R5 (#56) Payton Pritchard, R6 (#65) Kon Knueppel, R7 (#80) Kel'el Ware, R8 (#89) Miles Bridges, R9 (#104) Brandin Podziemski, R10 (#113) Ayo Dosunmu, R11 (#128) Davion Mitchell, R12 (#137) Bobby Portis Jr., R13 (#152) Royce O'Neale`

---

## 4. Gerçek Draft Günü (Slot #8) İçin Nihai Eylem Planı (Cheat Sheet)

1. **1. Tur (#8) Karar Ağacı (Öncelik Sırası):**
   - **Öncelik 1:** Eğer masada **Tyrese Maxey** (`PHI - G`) açıksa tereddütsüz seçin (**Senaryo 1 — %30 Şampiyonluk, #1/12 Sıralama**).
   - **Öncelik 2:** Eğer ilk 7'de bir sürpriz olup **Giannis Antetokounmpo** #8'e kayarsa hemen seçin ve `Punt FT%` moduna geçin (**Senaryo 8 — #3/12 Sıralama**).
   - **Öncelik 3:** Maxey gittiyse **Kevin Durant** (`HOU - F`) veya **Donovan Mitchell** (`CLE - G`) seçerek **`Punt AST`** kurgusunu başlatın (**Senaryo 6 & 4 — #3 ve #4 Sıralama**).
   - **Öncelik 4:** Eğer çok yönlü kanat/oyun kurucu (**Cade Cunningham**, **Jalen Johnson** veya **Scottie Barnes**) seçerseniz, 2. ve 3. turlarda `BLK` ve `FG%` kategorilerini tamamen boş bırakmayın; mutlaka **Chet Holmgren / Evan Mobley / Donovan Clingan** üçlüsünden en az birini kadroya katın.

2. **2. Tur (#17) ve 3. Tur (#32) Omurga Eşleşmeleri:**
   - **En Yüksek Kazanma Oranlı İkili (#8 + #17 + #32):**
     * `Tyrese Maxey (#8)` + `Karl-Anthony Towns (#17)` + `Chet Holmgren (#32)` $\rightarrow$ **%60.8 Maç Galibiyeti (#1/12)**
     * `Kevin Durant (#8)` + `Bam Adebayo (#17)` + `Donovan Clingan (#32)` $\rightarrow$ **%55.4 Maç Galibiyeti (#3/12)**
     * `Donovan Mitchell (#8)` + `Jalen Duren (#17)` + `Desmond Bane (#32)` $\rightarrow$ **%53.0 Maç Galibiyeti (#4/12)**

3. **Orta ve Geç Turların (`R4–R12`) Gizli Cevherleri (Sleeper / Value Picks):**
   - **Tur 4–6 (#41–#65):** `OG Anunoby`, `Mikal Bridges`, `Kon Knueppel`, `Brandon Ingram`, `Payton Pritchard`
   - **Tur 7–9 (#80–#104):** `Jabari Smith Jr.`, `Myles Turner`, `Naz Reid`, `Kel'el Ware`, `Julian Champagnie`
   - **Tur 10–13 (#113–#152):** `Ayo Dosunmu`, `Tobias Harris`, `Royce O'Neale`, `Sandro Mamukelashvili`, `Moussa Diabaté`
