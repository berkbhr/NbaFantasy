# 🏀 2026-27 Yahoo NBA Fantasy 14-Takımlı Canlı Draft & H2H Simülasyon Raporu

**Lig Formatı:** 14 Takım | 9 Kategori H2H (PTS, REB, AST, STL, BLK, FG3M, TOV, FG%, FT%) | 13 Aktif/Bench Slot
**Bizim Takım:** Berk's Best Team (Draft Slot #8)
**Raporun Amacı:** Canlı draft sonuçlarının tam dökümü, 182 seçimin oluşturduğu 14 kadronun güç sıralaması, Bayesian Poisson-Binomial simülasyonu ile hesaplanan gerçek galibiyet olasılıkları ve Yahoo'nun '12. Sıra Tahmini' ile Yapay Zeka Modelimizin '1. Sıra Şampiyonluk Favorisi' tespiti arasındaki metodolojik farkların dış ajan/uzman incelemesine (peer-review) sunulması.

---

## 1. Yönetici Özeti ve Temel Bulgular

1. **Kadro Başarısı (Lig 1.'liği):** Poisson-Binomial ve Monte Carlo tabanlı Bayesian simülasyon motorumuz, 14 takımın birbiriyle oynadığı 182 ikili lig eşleşmesinde **Berk's Best Team'i %78.7 haftalık maç kazanma oranı ve 5.64 - 3.36 beklenen kategori skoruyla LİGİN 1 NUMARASI** olarak belirlemiştir.
2. **Kategori Hakimiyeti:** Kadromuz 9 kategorinin 5'inde (PTS %71.6, REB %71.8, BLK %66.1, FG3M %67.3, FT% %69.0) ligdeki 13 rakibin en az 10'una karşı açık ara üstündür. 3 kategoride (AST %56.7, STL %60.1, FG% %57.3) lig ortalamasının üzerindedir. Sadece TOV (%44.1) kategorisinde James Harden'ın yüksek kullanım oranı nedeniyle kontrollü bir taviz verilmiştir.
3. **Yahoo Raporu (12. Sıra) Paradoksu:** Yahoo'nun draft sonrası otomatik sıralaması, H2H ligi olmasına rağmen **82 maçlık Rotisserie (Roto) kümülatif toplamı** kullanmaktadır. Bu ilkel algoritma, Harden'ın getirdiği asist/sayıyı görmezden gelip yüksek top kaybına devasa eksi puan vermekte, Kawhi'a 45 maç yazarak skorunu %40 kısmakta ve Jay Huff / Queta gibi per-minute verimli rol oyuncularını tanıyamadığı için takımı haksız yere 12. sıraya atmaktadır.

---

## 2. 182 Seçimlik Tam Draft Tahtası (Round-by-Round Draft Board)

Aşağıdaki tablo, draft odasındaki 13 turun ve 182 seçimin kronolojik yılan (snake) sırasını, seçilen oyuncuyu, NBA takımını, mevkisini ve seçen menajeri göstermektedir:

| Tur.Sıra | Genel Pick | Seçilen Oyuncu | Takım | Mevki | Seçen Takım (Slot) |
| :---: | :---: | :--- | :---: | :---: | :--- |
| R1.01 | #001 | Nikola Jokić | DEN | C | MuCa Tandır (#1) |
| R1.02 | #002 | Victor Wembanyama | SAS | C | Mordor Tulums (#2) |
| R1.03 | #003 | Luka Dončić | LAL | PG,SG | Philadelphia Sikers (#3) |
| R1.04 | #004 | Shai Gilgeous-Alexander | OKC | PG | Houston Buckets (#4) |
| R1.05 | #005 | Cade Cunningham | DET | PG,SG | Kuvâ-yi Milfiye (#5) |
| R1.06 | #006 | Giannis Antetokounmpo | MIA | PF,C | abu dhabi camels (#6) |
| R1.07 | #007 | Jayson Tatum | BOS | SF,PF | Samurai Strikers (#7) |
| R1.08 | #008 | ⭐ **Tyrese Maxey** | PHI | PG | ⭐ **Berk's Best Team (#8)** |
| R1.09 | #009 | Anthony Edwards | MIN | PG,SG | FatihTerimSpor (#9) |
| R1.10 | #010 | Tyrese Haliburton | IND | PG,SG | Redeem Team (#10) |
| R1.11 | #011 | Cooper Flagg | DAL | SG,SF,PF | Fikirtepe Warriors (#11) |
| R1.12 | #012 | Jalen Johnson | ATL | SF,PF | Istanbul Brickmakers (#12) |
| R1.13 | #013 | Donovan Mitchell | CLE | PG,SG | SILE BULLS (#13) |
| R1.14 | #014 | Alperen Şengün | HOU | PF,C | YearOne Tyrants (#14) |
| R2.01 | #015 | Jamal Murray | DEN | PG | YearOne Tyrants (#14) |
| R2.02 | #016 | Scottie Barnes | TOR | SF,PF,C | SILE BULLS (#13) |
| R2.03 | #017 | Kevin Durant | HOU | SG,SF,PF | Istanbul Brickmakers (#12) |
| R2.04 | #018 | Karl-Anthony Towns | NYK | PF,C | Fikirtepe Warriors (#11) |
| R2.05 | #019 | Austin Reaves | LAL | PG,SG,SF | Redeem Team (#10) |
| R2.06 | #020 | Jalen Duren | DET | C | FatihTerimSpor (#9) |
| R2.07 | #021 | ⭐ **James Harden** | CLE | PG,SG | ⭐ **Berk's Best Team (#8)** |
| R2.08 | #022 | Amen Thompson | HOU | PG,SG | Samurai Strikers (#7) |
| R2.09 | #023 | LaMelo Ball | MIN | PG | abu dhabi camels (#6) |
| R2.10 | #024 | Devin Booker | PHX | PG,SG | Kuvâ-yi Milfiye (#5) |
| R2.11 | #025 | Stephen Curry | GSW | PG | Houston Buckets (#4) |
| R2.12 | #026 | Trae Young | WAS | PG | Philadelphia Sikers (#3) |
| R2.13 | #027 | Trey Murphy III | NOP | SG,SF | Mordor Tulums (#2) |
| R2.14 | #028 | Jalen Brunson | NYK | PG | MuCa Tandır (#1) |
| R3.01 | #029 | Evan Mobley | CLE | PF,C | MuCa Tandır (#1) |
| R3.02 | #030 | Chet Holmgren | OKC | PF,C | Mordor Tulums (#2) |
| R3.03 | #031 | Lauri Markkanen | UTA | SF,PF | Philadelphia Sikers (#3) |
| R3.04 | #032 | Jalen Williams | OKC | SF,PF | Houston Buckets (#4) |
| R3.05 | #033 | Walker Kessler | LAL | C | Kuvâ-yi Milfiye (#5) |
| R3.06 | #034 | Josh Giddey | CHI | PG,SG | abu dhabi camels (#6) |
| R3.07 | #035 | Domantas Sabonis | SAC | PF,C | Samurai Strikers (#7) |
| R3.08 | #036 | ⭐ **Kawhi Leonard** | TOR | SG,SF,PF | ⭐ **Berk's Best Team (#8)** |
| R3.09 | #037 | Keyonte George | UTA | PG,SG | FatihTerimSpor (#9) |
| R3.10 | #038 | Onyeka Okongwu | ATL | C | Redeem Team (#10) |
| R3.11 | #039 | Bam Adebayo | MIA | PF,C | Fikirtepe Warriors (#11) |
| R3.12 | #040 | Kyrie Irving | DAL | PG | Istanbul Brickmakers (#12) |
| R3.13 | #041 | Derrick White | BOS | PG,SG | SILE BULLS (#13) |
| R3.14 | #042 | Matas Buzelis | CHI | SF,PF | YearOne Tyrants (#14) |
| R4.01 | #043 | Brandon Miller | CHA | SF,PF | YearOne Tyrants (#14) |
| R4.02 | #044 | Jaren Jackson Jr. | UTA | PF,C | SILE BULLS (#13) |
| R4.03 | #045 | Anthony Davis | WAS | PF,C | Istanbul Brickmakers (#12) |
| R4.04 | #046 | Deni Avdija | POR | SG,SF,PF | Fikirtepe Warriors (#11) |
| R4.05 | #047 | Pascal Siakam | IND | PF,C | Redeem Team (#10) |
| R4.06 | #048 | Paolo Banchero | ORL | PF | FatihTerimSpor (#9) |
| R4.07 | #049 | ⭐ **Desmond Bane** | ORL | SG,SF | ⭐ **Berk's Best Team (#8)** |
| R4.08 | #050 | Donovan Clingan | POR | C | Samurai Strikers (#7) |
| R4.09 | #051 | Franz Wagner | ORL | SF,PF | abu dhabi camels (#6) |
| R4.10 | #052 | Nickeil Alexander-Walker | ATL | PG,SG | Kuvâ-yi Milfiye (#5) |
| R4.11 | #053 | Jaylen Brown | PHI | SG,SF,PF | Houston Buckets (#4) |
| R4.12 | #054 | Ivica Zubac | IND | C | Philadelphia Sikers (#3) |
| R4.13 | #055 | Damian Lillard | POR | PG | Mordor Tulums (#2) |
| R4.14 | #056 | Cameron Boozer | MEM | PF | MuCa Tandır (#1) |
| R5.01 | #057 | Kon Knueppel | CHA | SG,SF | MuCa Tandır (#1) |
| R5.02 | #058 | OG Anunoby | NYK | SF,PF | Mordor Tulums (#2) |
| R5.03 | #059 | Darius Garland | LAC | PG | Philadelphia Sikers (#3) |
| R5.04 | #060 | Nic Claxton | CHI | C | Houston Buckets (#4) |
| R5.05 | #061 | Michael Porter Jr. | BKN | SF,PF | Kuvâ-yi Milfiye (#5) |
| R5.06 | #062 | Dyson Daniels | ATL | SG,SF | abu dhabi camels (#6) |
| R5.07 | #063 | LeBron James | PHI | SF,PF | Samurai Strikers (#7) |
| R5.08 | #064 | ⭐ **Jarrett Allen** | CLE | C | ⭐ **Berk's Best Team (#8)** |
| R5.09 | #065 | Stephon Castle | SAS | PG,SG | FatihTerimSpor (#9) |
| R5.10 | #066 | Mikal Bridges | NYK | SF,PF | Redeem Team (#10) |
| R5.11 | #067 | Dejounte Murray | NOP | PG | Fikirtepe Warriors (#11) |
| R5.12 | #068 | Ryan Rollins | MIL | PG,SG | Istanbul Brickmakers (#12) |
| R5.13 | #069 | Payton Pritchard | BOS | PG | SILE BULLS (#13) |
| R5.14 | #070 | Kel'el Ware | MIL | C | YearOne Tyrants (#14) |
| R6.01 | #071 | De'Aaron Fox | SAS | PG | YearOne Tyrants (#14) |
| R6.02 | #072 | Julius Randle | BKN | PF | SILE BULLS (#13) |
| R6.03 | #073 | Zach Edey | MEM | C | Istanbul Brickmakers (#12) |
| R6.04 | #074 | Jaden McDaniels | MIN | SF | Fikirtepe Warriors (#11) |
| R6.05 | #075 | Rudy Gobert | MIN | C | Redeem Team (#10) |
| R6.06 | #076 | Paul George | BOS | SF,PF | FatihTerimSpor (#9) |
| R6.07 | #077 | ⭐ **Jabari Smith Jr.** | HOU | PF,C | ⭐ **Berk's Best Team (#8)** |
| R6.08 | #078 | Tyler Herro | MIL | PG,SG | Samurai Strikers (#7) |
| R6.09 | #079 | Joel Embiid | PHI | C | abu dhabi camels (#6) |
| R6.10 | #080 | Naz Reid | CHA | PF,C | Kuvâ-yi Milfiye (#5) |
| R6.11 | #081 | Derik Queen | NOP | PF,C | Houston Buckets (#4) |
| R6.12 | #082 | Immanuel Quickley | TOR | PG,SG | Philadelphia Sikers (#3) |
| R6.13 | #083 | Ty Jerome | MEM | PG,SG | Mordor Tulums (#2) |
| R6.14 | #084 | Caleb Wilson | CHI | PF | MuCa Tandır (#1) |
| R7.01 | #085 | Norman Powell | CHI | SG,SF | MuCa Tandır (#1) |
| R7.02 | #086 | John Collins | DET | PF,C | Mordor Tulums (#2) |
| R7.03 | #087 | Alex Sarr | WAS | C | Philadelphia Sikers (#3) |
| R7.04 | #088 | Keegan Murray | SAC | SF,PF | Houston Buckets (#4) |
| R7.05 | #089 | Cedric Coward | MEM | SG,SF | Kuvâ-yi Milfiye (#5) |
| R7.06 | #090 | AJ Dybantsa | WAS | SF | abu dhabi camels (#6) |
| R7.07 | #091 | Ausar Thompson | DET | SG,SF,PF | Samurai Strikers (#7) |
| R7.08 | #092 | ⭐ **Josh Hart** | NYK | SG,SF | ⭐ **Berk's Best Team (#8)** |
| R7.09 | #093 | Ja Morant | POR | PG | FatihTerimSpor (#9) |
| R7.10 | #094 | Zion Williamson | NOP | PF,C | Redeem Team (#10) |
| R7.11 | #095 | Coby White | CHA | PG,SG | Fikirtepe Warriors (#11) |
| R7.12 | #096 | Dylan Harper | SAS | PG,SG | Istanbul Brickmakers (#12) |
| R7.13 | #097 | VJ Edgecombe | PHI | PG,SG | SILE BULLS (#13) |
| R7.14 | #098 | Jalen Suggs | ORL | PG,SG | YearOne Tyrants (#14) |
| R8.01 | #099 | Collin Murray-Boyles | TOR | PF,C | YearOne Tyrants (#14) |
| R8.02 | #100 | Isaiah Hartenstein | OKC | C | SILE BULLS (#13) |
| R8.03 | #101 | Zach LaVine | SAC | PG,SG,SF | Istanbul Brickmakers (#12) |
| R8.04 | #102 | Myles Turner | MIL | C | Fikirtepe Warriors (#11) |
| R8.05 | #103 | Fred VanVleet | HOU | PG | Redeem Team (#10) |
| R8.06 | #104 | Aaron Gordon | DEN | PF,C | FatihTerimSpor (#9) |
| R8.07 | #105 | ⭐ **Neemias Queta** | BOS | C | ⭐ **Berk's Best Team (#8)** |
| R8.08 | #106 | Day'Ron Sharpe | BKN | C | Samurai Strikers (#7) |
| R8.09 | #107 | CJ McCollum | ATL | PG,SG | abu dhabi camels (#6) |
| R8.10 | #108 | Miles Bridges | PHX | PF | Kuvâ-yi Milfiye (#5) |
| R8.11 | #109 | Andrew Wiggins | MIA | SG,SF,PF | Houston Buckets (#4) |
| R8.12 | #110 | Toumani Camara | POR | SF,PF | Philadelphia Sikers (#3) |
| R8.13 | #111 | Tobias Harris | SAS | PF | Mordor Tulums (#2) |
| R8.14 | #112 | Cason Wallace | OKC | PG,SG,SF | MuCa Tandır (#1) |
| R9.01 | #113 | Herbert Jones | NOP | SG,SF | MuCa Tandır (#1) |
| R9.02 | #114 | Cameron Johnson | DEN | SF,PF | Mordor Tulums (#2) |
| R9.03 | #115 | Jalen Green | PHX | SG,SF | Philadelphia Sikers (#3) |
| R9.04 | #116 | Brook Lopez | LAC | C | Houston Buckets (#4) |
| R9.05 | #117 | Darryn Peterson | UTA | SG | Kuvâ-yi Milfiye (#5) |
| R9.06 | #118 | Khaman Maluach | PHX | C | abu dhabi camels (#6) |
| R9.07 | #119 | Brandin Podziemski | GSW | PG,SG | Samurai Strikers (#7) |
| R9.08 | #120 | ⭐ **Brandon Ingram** | LAC | SG,SF,PF | ⭐ **Berk's Best Team (#8)** |
| R9.09 | #121 | RJ Barrett | TOR | SG,SF,PF | FatihTerimSpor (#9) |
| R9.10 | #122 | Kevin Porter Jr. | MIL | PG,SG | Redeem Team (#10) |
| R9.11 | #123 | Yaxel Lendeborg | GSW | PF | Fikirtepe Warriors (#11) |
| R9.12 | #124 | Darius Acuff Jr. | SAC | PG | Istanbul Brickmakers (#12) |
| R9.13 | #125 | Collin Gillespie | PHX | PG,SG | SILE BULLS (#13) |
| R9.14 | #126 | Jaime Jaquez Jr. | MIL | SG,SF,PF | YearOne Tyrants (#14) |
| R10.01 | #127 | Christian Braun | DEN | SG,SF,PF | YearOne Tyrants (#14) |
| R10.02 | #128 | Kyshawn George | WAS | SG,SF,PF | SILE BULLS (#13) |
| R10.03 | #129 | Rui Hachimura | LAC | SF,PF | Istanbul Brickmakers (#12) |
| R10.04 | #130 | Egor Dëmin | BKN | PG,SG | Fikirtepe Warriors (#11) |
| R10.05 | #131 | Devin Vassell | SAS | SG,SF | Redeem Team (#10) |
| R10.06 | #132 | Quentin Grimes | LAL | SG,SF | FatihTerimSpor (#9) |
| R10.07 | #133 | ⭐ **Ayo Dosunmu** | MIN | PG,SG | ⭐ **Berk's Best Team (#8)** |
| R10.08 | #134 | Andrew Nembhard | IND | PG,SG | Samurai Strikers (#7) |
| R10.09 | #135 | Ajay Mitchell | OKC | PG,SG | abu dhabi camels (#6) |
| R10.10 | #136 | Gui Santos | GSW | SF,PF | Kuvâ-yi Milfiye (#5) |
| R10.11 | #137 | Tim Hardaway Jr. | MIA | SG,SF | Houston Buckets (#4) |
| R10.12 | #138 | Jakob Poeltl | TOR | C | Philadelphia Sikers (#3) |
| R10.13 | #139 | Peyton Watson | CLE | SF,PF | Mordor Tulums (#2) |
| R10.14 | #140 | Sandro Mamukelashvili | LAL | PF,C | MuCa Tandır (#1) |
| R11.01 | #141 | Alex Caruso | OKC | SG,SF | MuCa Tandır (#1) |
| R11.02 | #142 | Mitchell Robinson | BOS | C | Mordor Tulums (#2) |
| R11.03 | #143 | Jonathan Kuminga | MIN | SF,PF | Philadelphia Sikers (#3) |
| R11.04 | #144 | DeMar DeRozan | DEN | SF,PF | Houston Buckets (#4) |
| R11.05 | #145 | Ace Bailey | UTA | SF,PF | Kuvâ-yi Milfiye (#5) |
| R11.06 | #146 | Daniel Gafford | DAL | C | abu dhabi camels (#6) |
| R11.07 | #147 | Reed Sheppard | HOU | PG,SG | Samurai Strikers (#7) |
| R11.08 | #148 | ⭐ **Nikola Vučević** | ORL | C | ⭐ **Berk's Best Team (#8)** |
| R11.09 | #149 | Dillon Brooks | PHX | SF,PF | FatihTerimSpor (#9) |
| R11.10 | #150 | Wendell Carter Jr. | ORL | C | Redeem Team (#10) |
| R11.11 | #151 | Saddiq Bey | NOP | SF,PF | Fikirtepe Warriors (#11) |
| R11.12 | #152 | Yves Missi | NOP | C | Istanbul Brickmakers (#12) |
| R11.13 | #153 | P.J. Washington | DAL | PF,C | SILE BULLS (#13) |
| R11.14 | #154 | Davion Mitchell | MIA | PG | YearOne Tyrants (#14) |
| R12.01 | #155 | Tari Eason | HOU | SG,SF,PF | YearOne Tyrants (#14) |
| R12.02 | #156 | Jimmy Butler III | GSW | SF,PF | SILE BULLS (#13) |
| R12.03 | #157 | Jaylen Wells | MEM | SG,SF | Istanbul Brickmakers (#12) |
| R12.04 | #158 | Isaiah Jackson | LAC | C | Fikirtepe Warriors (#11) |
| R12.05 | #159 | Draymond Green | GSW | PF,C | Redeem Team (#10) |
| R12.06 | #160 | Bobby Portis Jr. | MIA | PF,C | FatihTerimSpor (#9) |
| R12.07 | #161 | ⭐ **Julian Champagnie** | SAS | SF,PF | ⭐ **Berk's Best Team (#8)** |
| R12.08 | #162 | Grayson Allen | CHA | SG,SF | Samurai Strikers (#7) |
| R12.09 | #163 | Aaron Nesmith | IND | SG,SF | abu dhabi camels (#6) |
| R12.10 | #164 | Mikel Brown Jr. | BKN | PG | Kuvâ-yi Milfiye (#5) |
| R12.11 | #165 | Jrue Holiday | POR | PG,SG | Houston Buckets (#4) |
| R12.12 | #166 | Jerami Grant | MEM | SF,PF | Philadelphia Sikers (#3) |
| R12.13 | #167 | Robert Williams III | POR | C | Mordor Tulums (#2) |
| R12.14 | #168 | Scotty Pippen Jr. | MEM | PG | MuCa Tandır (#1) |
| R13.01 | #169 | Kelly Oubre Jr. | IND | SF,PF | MuCa Tandır (#1) |
| R13.02 | #170 | Sam Hauser | BOS | SF,PF | Mordor Tulums (#2) |
| R13.03 | #171 | Bennedict Mathurin | NOP | SG,SF | Philadelphia Sikers (#3) |
| R13.04 | #172 | Tre Jones | CHI | PG,SG | Houston Buckets (#4) |
| R13.05 | #173 | Moussa Diabaté | CHA | C | Kuvâ-yi Milfiye (#5) |
| R13.06 | #174 | Anthony Black | ORL | PG,SG,SF | abu dhabi camels (#6) |
| R13.07 | #175 | Jeremiah Fears | NOP | PG,SG | Samurai Strikers (#7) |
| R13.08 | #176 | ⭐ **Jay Huff** | IND | C | ⭐ **Berk's Best Team (#8)** |
| R13.09 | #177 | Deandre Ayton | WAS | C | FatihTerimSpor (#9) |
| R13.10 | #178 | Ben Simmons | SAC | PG | Redeem Team (#10) |
| R13.11 | #179 | Zaccharie Risacher | DAL | SF,PF | Fikirtepe Warriors (#11) |
| R13.12 | #180 | Jake LaRavia | LAL | SF,PF | Istanbul Brickmakers (#12) |
| R13.13 | #181 | Pelle Larsson | MIA | SG,SF | SILE BULLS (#13) |
| R13.14 | #182 | Scoot Henderson | POR | PG | YearOne Tyrants (#14) |

---

## 3. Draft Sonrası 14 Takımın Tam Kadroları (Rosters)

### Slot #1: MuCa Tandır

| Tur | Oyuncu Adı | NBA Takımı | Mevkiler |
| :---: | :--- | :---: | :---: |
| R01 | **Nikola Jokić** | DEN | C |
| R02 | **Jalen Brunson** | NYK | PG |
| R03 | **Evan Mobley** | CLE | PF,C |
| R04 | **Cameron Boozer** | MEM | PF |
| R05 | **Kon Knueppel** | CHA | SG,SF |
| R06 | **Caleb Wilson** | CHI | PF |
| R07 | **Norman Powell** | CHI | SG,SF |
| R08 | **Cason Wallace** | OKC | PG,SG,SF |
| R09 | **Herbert Jones** | NOP | SG,SF |
| R10 | **Sandro Mamukelashvili** | LAL | PF,C |
| R11 | **Alex Caruso** | OKC | SG,SF |
| R12 | **Scotty Pippen Jr.** | MEM | PG |
| R13 | **Kelly Oubre Jr.** | IND | SF,PF |

### Slot #2: Mordor Tulums

| Tur | Oyuncu Adı | NBA Takımı | Mevkiler |
| :---: | :--- | :---: | :---: |
| R01 | **Victor Wembanyama** | SAS | C |
| R02 | **Trey Murphy III** | NOP | SG,SF |
| R03 | **Chet Holmgren** | OKC | PF,C |
| R04 | **Damian Lillard** | POR | PG |
| R05 | **OG Anunoby** | NYK | SF,PF |
| R06 | **Ty Jerome** | MEM | PG,SG |
| R07 | **John Collins** | DET | PF,C |
| R08 | **Tobias Harris** | SAS | PF |
| R09 | **Cameron Johnson** | DEN | SF,PF |
| R10 | **Peyton Watson** | CLE | SF,PF |
| R11 | **Mitchell Robinson** | BOS | C |
| R12 | **Robert Williams III** | POR | C |
| R13 | **Sam Hauser** | BOS | SF,PF |

### Slot #3: Philadelphia Sikers

| Tur | Oyuncu Adı | NBA Takımı | Mevkiler |
| :---: | :--- | :---: | :---: |
| R01 | **Luka Dončić** | LAL | PG,SG |
| R02 | **Trae Young** | WAS | PG |
| R03 | **Lauri Markkanen** | UTA | SF,PF |
| R04 | **Ivica Zubac** | IND | C |
| R05 | **Darius Garland** | LAC | PG |
| R06 | **Immanuel Quickley** | TOR | PG,SG |
| R07 | **Alex Sarr** | WAS | C |
| R08 | **Toumani Camara** | POR | SF,PF |
| R09 | **Jalen Green** | PHX | SG,SF |
| R10 | **Jakob Poeltl** | TOR | C |
| R11 | **Jonathan Kuminga** | MIN | SF,PF |
| R12 | **Jerami Grant** | MEM | SF,PF |
| R13 | **Bennedict Mathurin** | NOP | SG,SF |

### Slot #4: Houston Buckets

| Tur | Oyuncu Adı | NBA Takımı | Mevkiler |
| :---: | :--- | :---: | :---: |
| R01 | **Shai Gilgeous-Alexander** | OKC | PG |
| R02 | **Stephen Curry** | GSW | PG |
| R03 | **Jalen Williams** | OKC | SF,PF |
| R04 | **Jaylen Brown** | PHI | SG,SF,PF |
| R05 | **Nic Claxton** | CHI | C |
| R06 | **Derik Queen** | NOP | PF,C |
| R07 | **Keegan Murray** | SAC | SF,PF |
| R08 | **Andrew Wiggins** | MIA | SG,SF,PF |
| R09 | **Brook Lopez** | LAC | C |
| R10 | **Tim Hardaway Jr.** | MIA | SG,SF |
| R11 | **DeMar DeRozan** | DEN | SF,PF |
| R12 | **Jrue Holiday** | POR | PG,SG |
| R13 | **Tre Jones** | CHI | PG,SG |

### Slot #5: Kuvâ-yi Milfiye

| Tur | Oyuncu Adı | NBA Takımı | Mevkiler |
| :---: | :--- | :---: | :---: |
| R01 | **Cade Cunningham** | DET | PG,SG |
| R02 | **Devin Booker** | PHX | PG,SG |
| R03 | **Walker Kessler** | LAL | C |
| R04 | **Nickeil Alexander-Walker** | ATL | PG,SG |
| R05 | **Michael Porter Jr.** | BKN | SF,PF |
| R06 | **Naz Reid** | CHA | PF,C |
| R07 | **Cedric Coward** | MEM | SG,SF |
| R08 | **Miles Bridges** | PHX | PF |
| R09 | **Darryn Peterson** | UTA | SG |
| R10 | **Gui Santos** | GSW | SF,PF |
| R11 | **Ace Bailey** | UTA | SF,PF |
| R12 | **Mikel Brown Jr.** | BKN | PG |
| R13 | **Moussa Diabaté** | CHA | C |

### Slot #6: abu dhabi camels

| Tur | Oyuncu Adı | NBA Takımı | Mevkiler |
| :---: | :--- | :---: | :---: |
| R01 | **Giannis Antetokounmpo** | MIA | PF,C |
| R02 | **LaMelo Ball** | MIN | PG |
| R03 | **Josh Giddey** | CHI | PG,SG |
| R04 | **Franz Wagner** | ORL | SF,PF |
| R05 | **Dyson Daniels** | ATL | SG,SF |
| R06 | **Joel Embiid** | PHI | C |
| R07 | **AJ Dybantsa** | WAS | SF |
| R08 | **CJ McCollum** | ATL | PG,SG |
| R09 | **Khaman Maluach** | PHX | C |
| R10 | **Ajay Mitchell** | OKC | PG,SG |
| R11 | **Daniel Gafford** | DAL | C |
| R12 | **Aaron Nesmith** | IND | SG,SF |
| R13 | **Anthony Black** | ORL | PG,SG,SF |

### Slot #7: Samurai Strikers

| Tur | Oyuncu Adı | NBA Takımı | Mevkiler |
| :---: | :--- | :---: | :---: |
| R01 | **Jayson Tatum** | BOS | SF,PF |
| R02 | **Amen Thompson** | HOU | PG,SG |
| R03 | **Domantas Sabonis** | SAC | PF,C |
| R04 | **Donovan Clingan** | POR | C |
| R05 | **LeBron James** | PHI | SF,PF |
| R06 | **Tyler Herro** | MIL | PG,SG |
| R07 | **Ausar Thompson** | DET | SG,SF,PF |
| R08 | **Day'Ron Sharpe** | BKN | C |
| R09 | **Brandin Podziemski** | GSW | PG,SG |
| R10 | **Andrew Nembhard** | IND | PG,SG |
| R11 | **Reed Sheppard** | HOU | PG,SG |
| R12 | **Grayson Allen** | CHA | SG,SF |
| R13 | **Jeremiah Fears** | NOP | PG,SG |

### Slot #8: Berk's Best Team (BİZİM TAKIM - ŞAMPİYONLUK FAVORİSİ) ⭐

| Tur | Oyuncu Adı | NBA Takımı | Mevkiler |
| :---: | :--- | :---: | :---: |
| R01 | **Tyrese Maxey** | PHI | PG |
| R02 | **James Harden** | CLE | PG,SG |
| R03 | **Kawhi Leonard** | TOR | SG,SF,PF |
| R04 | **Desmond Bane** | ORL | SG,SF |
| R05 | **Jarrett Allen** | CLE | C |
| R06 | **Jabari Smith Jr.** | HOU | PF,C |
| R07 | **Josh Hart** | NYK | SG,SF |
| R08 | **Neemias Queta** | BOS | C |
| R09 | **Brandon Ingram** | LAC | SG,SF,PF |
| R10 | **Ayo Dosunmu** | MIN | PG,SG |
| R11 | **Nikola Vučević** | ORL | C |
| R12 | **Julian Champagnie** | SAS | SF,PF |
| R13 | **Jay Huff** | IND | C |

### Slot #9: FatihTerimSpor

| Tur | Oyuncu Adı | NBA Takımı | Mevkiler |
| :---: | :--- | :---: | :---: |
| R01 | **Anthony Edwards** | MIN | PG,SG |
| R02 | **Jalen Duren** | DET | C |
| R03 | **Keyonte George** | UTA | PG,SG |
| R04 | **Paolo Banchero** | ORL | PF |
| R05 | **Stephon Castle** | SAS | PG,SG |
| R06 | **Paul George** | BOS | SF,PF |
| R07 | **Ja Morant** | POR | PG |
| R08 | **Aaron Gordon** | DEN | PF,C |
| R09 | **RJ Barrett** | TOR | SG,SF,PF |
| R10 | **Quentin Grimes** | LAL | SG,SF |
| R11 | **Dillon Brooks** | PHX | SF,PF |
| R12 | **Bobby Portis Jr.** | MIA | PF,C |
| R13 | **Deandre Ayton** | WAS | C |

### Slot #10: Redeem Team

| Tur | Oyuncu Adı | NBA Takımı | Mevkiler |
| :---: | :--- | :---: | :---: |
| R01 | **Tyrese Haliburton** | IND | PG,SG |
| R02 | **Austin Reaves** | LAL | PG,SG,SF |
| R03 | **Onyeka Okongwu** | ATL | C |
| R04 | **Pascal Siakam** | IND | PF,C |
| R05 | **Mikal Bridges** | NYK | SF,PF |
| R06 | **Rudy Gobert** | MIN | C |
| R07 | **Zion Williamson** | NOP | PF,C |
| R08 | **Fred VanVleet** | HOU | PG |
| R09 | **Kevin Porter Jr.** | MIL | PG,SG |
| R10 | **Devin Vassell** | SAS | SG,SF |
| R11 | **Wendell Carter Jr.** | ORL | C |
| R12 | **Draymond Green** | GSW | PF,C |
| R13 | **Ben Simmons** | SAC | PG |

### Slot #11: Fikirtepe Warriors

| Tur | Oyuncu Adı | NBA Takımı | Mevkiler |
| :---: | :--- | :---: | :---: |
| R01 | **Cooper Flagg** | DAL | SG,SF,PF |
| R02 | **Karl-Anthony Towns** | NYK | PF,C |
| R03 | **Bam Adebayo** | MIA | PF,C |
| R04 | **Deni Avdija** | POR | SG,SF,PF |
| R05 | **Dejounte Murray** | NOP | PG |
| R06 | **Jaden McDaniels** | MIN | SF |
| R07 | **Coby White** | CHA | PG,SG |
| R08 | **Myles Turner** | MIL | C |
| R09 | **Yaxel Lendeborg** | GSW | PF |
| R10 | **Egor Dëmin** | BKN | PG,SG |
| R11 | **Saddiq Bey** | NOP | SF,PF |
| R12 | **Isaiah Jackson** | LAC | C |
| R13 | **Zaccharie Risacher** | DAL | SF,PF |

### Slot #12: Istanbul Brickmakers

| Tur | Oyuncu Adı | NBA Takımı | Mevkiler |
| :---: | :--- | :---: | :---: |
| R01 | **Jalen Johnson** | ATL | SF,PF |
| R02 | **Kevin Durant** | HOU | SG,SF,PF |
| R03 | **Kyrie Irving** | DAL | PG |
| R04 | **Anthony Davis** | WAS | PF,C |
| R05 | **Ryan Rollins** | MIL | PG,SG |
| R06 | **Zach Edey** | MEM | C |
| R07 | **Dylan Harper** | SAS | PG,SG |
| R08 | **Zach LaVine** | SAC | PG,SG,SF |
| R09 | **Darius Acuff Jr.** | SAC | PG |
| R10 | **Rui Hachimura** | LAC | SF,PF |
| R11 | **Yves Missi** | NOP | C |
| R12 | **Jaylen Wells** | MEM | SG,SF |
| R13 | **Jake LaRavia** | LAL | SF,PF |

### Slot #13: SILE BULLS

| Tur | Oyuncu Adı | NBA Takımı | Mevkiler |
| :---: | :--- | :---: | :---: |
| R01 | **Donovan Mitchell** | CLE | PG,SG |
| R02 | **Scottie Barnes** | TOR | SF,PF,C |
| R03 | **Derrick White** | BOS | PG,SG |
| R04 | **Jaren Jackson Jr.** | UTA | PF,C |
| R05 | **Payton Pritchard** | BOS | PG |
| R06 | **Julius Randle** | BKN | PF |
| R07 | **VJ Edgecombe** | PHI | PG,SG |
| R08 | **Isaiah Hartenstein** | OKC | C |
| R09 | **Collin Gillespie** | PHX | PG,SG |
| R10 | **Kyshawn George** | WAS | SG,SF,PF |
| R11 | **P.J. Washington** | DAL | PF,C |
| R12 | **Jimmy Butler III** | GSW | SF,PF |
| R13 | **Pelle Larsson** | MIA | SG,SF |

### Slot #14: YearOne Tyrants

| Tur | Oyuncu Adı | NBA Takımı | Mevkiler |
| :---: | :--- | :---: | :---: |
| R01 | **Alperen Şengün** | HOU | PF,C |
| R02 | **Jamal Murray** | DEN | PG |
| R03 | **Matas Buzelis** | CHI | SF,PF |
| R04 | **Brandon Miller** | CHA | SF,PF |
| R05 | **Kel'el Ware** | MIL | C |
| R06 | **De'Aaron Fox** | SAS | PG |
| R07 | **Jalen Suggs** | ORL | PG,SG |
| R08 | **Collin Murray-Boyles** | TOR | PF,C |
| R09 | **Jaime Jaquez Jr.** | MIL | SG,SF,PF |
| R10 | **Christian Braun** | DEN | SG,SF,PF |
| R11 | **Davion Mitchell** | MIA | PG |
| R12 | **Tari Eason** | HOU | SG,SF,PF |
| R13 | **Scoot Henderson** | POR | PG |

---

## 4. Modelimizin Berk's Best Team İçin Analizi ve Galibiyet Olasılıkları

### 4.1. HUD Parametrik Kohort Tahminleri vs. Gerçek 13 Rakip Simülasyonu

| Kategori | HUD Göstergesi (Kohort Z) | Gerçek 13 Rakibe Karşı Ortalama | Fark | Simülasyon Analizi |
| :--- | :---: | :---: | :---: | :--- |
| **PTS (Sayı)** | **73.8%** | **71.6%** | -2.2% | **Lig Eliti:** Maxey (21.1), Kawhi (19.6), Harden (18.4), Ingram (17.3), Bane (16.3) ile haftalık sayı garantisi. |
| **REB (Ribaund)** | **71.4%** | **71.8%** | **+0.4%** | **Mükemmel Denge:** Allen (6.9), Vučević (6.5), Queta (6.4), Hart (6.0), Jabari (5.8) ile ligin en iyi ribaund takımlarından biri. |
| **AST (Asist)** | **47.2%** | **56.7%** | **+9.5%** | **Harden Etkisi:** Harden (6.29), Maxey (4.99), Hart (3.97) ve Bane (3.64) ile asist kategorisi beklenenin çok üstünde. |
| **STL (Top Çalma)** | **58.8%** | **60.1%** | **+1.3%** | **Üstünlük:** Maxey (1.39) ve Kawhi (1.29) önderliğinde lig ortalamasının belirgin şekilde üstünde. |
| **BLK (Blok)** | **69.0%** | **66.1%** | -2.9% | **Pota Altı Kilidi:** Huff (1.32), Queta (0.99), Jabari (0.73) ve Allen (0.72) ile çember savunması zirvede. |
| **FG3M (3 Sayı)** | **67.1%** | **67.3%** | **+0.2%** | **Kusursuz İsabet:** 11 oyuncunun maç başına 1.0+ üçlük attığı ligin en homojen dış şut takımı. |
| **TOV (Top Kaybı)** | **57.0%** | **44.1%** | -12.9% | **Kontrollü Taviz:** Harden'ın 2.81 top kaybı bu kategoriyi aşağı çekti, ancak kattığı asist ve sayılar bunu katbekat aşıyor. |
| **FG% (Saha İçi %)** | **68.1%** | **57.3%** | -10.8% | **Dengeli (%48.8 Kadro Ort.):** Allen (%61.8) ve Queta (%61.1) guard şutlarını nötrlüyor. |
| **FT% (Serbest Atış %)** | **86.9%** | **69.0%** | -17.9% | **Lig Zirvesi (%82.3 Kadro Ort.):** Harden, Maxey, Kawhi ve Bane ligin en elit serbest atışçıları. |

### 4.2. 13 Rakip Takımla Birebir Eşleşme Karnesi (Poisson-Binomial H2H Matrix)

| Slot | Rakip Takım Adı | Beklenen Skor | Maç Kazanma % | PTS | REB | AST | STL | BLK | 3PM | TOV | FG% | FT% |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| #1 | MuCa Tandır | 5.77 - 3.23 | **82.4%** | 80% | 83% | 59% | 53% | 81% | 66% | 32% | 52% | 71% |
| #2 | Mordor Tulums | 5.29 - 3.71 | **72.4%** | 81% | 66% | 94% | 67% | 33% | 64% | 19% | 45% | 59% |
| #3 | Philadelphia Sikers | 5.67 - 3.33 | **79.5%** | 61% | 73% | 48% | 65% | 74% | 52% | 58% | 66% | 69% |
| #4 | Houston Buckets | 5.17 - 3.83 | **67.8%** | 56% | 84% | 47% | 56% | 60% | 64% | 42% | 54% | 55% |
| #5 | Kuvâ-yi Milfiye | 5.84 - 3.16 | **82.8%** | 75% | 72% | 68% | 72% | 64% | 63% | 43% | 66% | 61% |
| #6 | abu dhabi camels | 6.13 - 2.87 | **88.8%** | 77% | 79% | 50% | 64% | 76% | 83% | 45% | 58% | 82% |
| #7 | Samurai Strikers | 5.33 - 3.67 | **72.2%** | 71% | 53% | 34% | 43% | 72% | 69% | 57% | 57% | 77% |
| #9 | FatihTerimSpor | 6.11 - 2.89 | **88.0%** | 62% | 70% | 68% | 73% | 84% | 73% | 53% | 52% | 76% |
| #10 | Redeem Team | 5.41 - 3.59 | **74.4%** | 76% | 68% | 40% | 49% | 62% | 74% | 39% | 51% | 83% |
| #11 | Fikirtepe Warriors | 6.00 - 3.00 | **86.3%** | 77% | 64% | 79% | 69% | 66% | 72% | 40% | 68% | 66% |
| #12 | Istanbul Brickmakers | 5.95 - 3.05 | **85.5%** | 78% | 76% | 75% | 72% | 64% | 76% | 41% | 47% | 67% |
| #13 | SILE BULLS | 5.09 - 3.91 | **65.8%** | 63% | 70% | 34% | 44% | 60% | 54% | 54% | 69% | 61% |
| #14 | YearOne Tyrants | 5.57 - 3.43 | **77.5%** | 75% | 76% | 42% | 54% | 64% | 65% | 52% | 60% | 70% |

---

## 5. 14 Takımın Tam Lig Güç Sıralaması (Power Rankings)

Ligdeki tüm 14 takımın birbiriyle oynadığı 182 ikili lig simülasyonu sonucu oluşan sıralama:

| Sıra | Slot | Takım Adı | Haftalık Maç Kazanma % | Beklenen Kategori Skoru | Kadro Karakteristiği ve Zayıf Noktaları |
| :---: | :---: | :--- | :---: | :---: | :--- |
| 01 | #08 | **Berk's Best Team** 🏆 | **78.7%** | 5.64 - 3.36 | Berk's Best Team: Sıfır delik, elit hücum, ligin en dengeli ribaund/blok yapısı ve yıkılmaz serbest atış. |
| 02 | #13 | **SILE BULLS** | **64.2%** | 5.03 - 3.97 | Donovan Mitchell + Scottie Barnes + Jaren Jackson Jr.; ligin en dişli 2. takımı; serbest atışta bize takılıyorlar. |
| 03 | #04 | **Houston Buckets** | **61.3%** | 4.93 - 4.07 | SGA + Stephen Curry omurgası çok keskin bir hücum takımı; pivot rotasyonu dar ve ribaundda eziliyorlar. |
| 04 | #02 | **Mordor Tulums** | **56.6%** | 4.73 - 4.27 | Wembanyama + Chet Holmgren elit blok ikilisi kurdu; fakat oyun kurucu eksikliği nedeniyle asistte çöküyorlar. |
| 05 | #07 | **Samurai Strikers** | **56.2%** | 4.73 - 4.27 | Jayson Tatum + LeBron James + Domantas Sabonis; çok yönlü ama savunma istatistikleri yaşlı ve yavaş. |
| 06 | #10 | **Redeem Team** | **53.4%** | 4.63 - 4.37 | Tyrese Haliburton + Rudy Gobert + Zion; FT% ve top kaybını tamamen feda etmiş dengesiz bir yapı. |
| 07 | #14 | **YearOne Tyrants** | **50.5%** | 4.52 - 4.48 | Alperen Şengün + Jamal Murray + De'Aaron Fox; iyi guard rotasyonu fakat blok ve çember koruması yetersiz. |
| 08 | #03 | **Philadelphia Sikers** | **47.2%** | 4.39 - 4.61 | Luka Dončić + Trae Young asist tavanı yüksek ama aşırı top kaybı ve düşük şut yüzdesi maçı veriyor. |
| 09 | #05 | **Kuvâ-yi Milfiye** | **43.5%** | 4.25 - 4.75 | Cade Cunningham + Devin Booker dengeli hücum; ancak blok ve ribaund tavanı ligin altında. |
| 10 | #01 | **MuCa Tandır** | **43.4%** | 4.25 - 4.75 | Jokić ve Mobley güçlü ancak derinlik eksik; guard rotasyonu şut ve serbest atışta zayıf kalıyor. |
| 11 | #11 | **Fikirtepe Warriors** | **39.1%** | 4.09 - 4.91 | Cooper Flagg + Karl-Anthony Towns; potansiyel yüksek ancak top çalma ve asist üretimi yok denecek kadar az. |
| 12 | #12 | **Istanbul Brickmakers** | **38.9%** | 4.08 - 4.92 | Jalen Johnson + Anthony Davis + Kevin Durant; yaşlı/sakatlık riski yüksek ve bench rotasyonu sığ. |
| 13 | #09 | **FatihTerimSpor** | **34.9%** | 3.93 - 5.07 | Anthony Edwards + Jalen Duren; top kaybı çok yüksek ve pas trafiği ligin en zayıfı. |
| 14 | #06 | **abu dhabi camels** | **32.1%** | 3.81 - 5.19 | Giannis Antetokounmpo + Joel Embiid; serbest atış (%55 FT) ve 3 sayı tamamen punt edilmiş, şutör açığı felaket. |

---

## 6. Yahoo Draft Raporu (12. Sıra) vs. Bayesian Modeli (1. Sıra) Metodolojik Analizi

Yahoo'nun draft sonrasında takımı 14 takım içinde **12. sırada** göstermesi, Fantasy Basketbol'un en iyi bilinen metodolojik uyuşmazlığıdır. Başka uzman yapay zekalara (peer AI agents) sunulmak üzere bu durumun 4 temel teknik sebebi şunlardır:

### 1. H2H Formatında Rotisserie (Roto) Puanlama Hatası
Yahoo'nun draft değerlendirme algoritması ikili H2H maç simülasyonu çalıştırmaz; tüm oyuncuların 82 maçlık toplam istatistiklerini alt alta toplayıp sanki lig bir **Roto (Toplam Puan) Ligiymiş gibi** sıralar.
* H2H'de haftalık **5-4 kazanmak maçı kazandırır**. Bir kategoriyi 1 farkla kaybetmek ile 100 farkla kaybetmek tamamen aynıdır (0-1).
* Yahoo ise her kategoride takımlara 1'den 14'e puan verir. Bir kategoride sonuncu olan takımın genel puanından devasa 13 puan silinir.

### 2. Top Kaybı (TOV) Asimetrisi ve Yahoo'nun Ağır Cezası
Kadromuz James Harden, Tyrese Maxey, Brandon Ingram ve Desmond Bane gibi yüksek kullanımlı (high-usage) oyun kuruculara sahiptir.
* Bu oyuncular doğal olarak haftada 12-14 top kaybı üretir.
* Yahoo, TOV kategorisinde takımımızı 14 takım arasında **13. veya 14. sıraya** atar ve genel sıralamada takımı doğrudan 5-6 basamak aşağı çeker.
* Oysa H2H liginde TOV'u feda etmek (soft-punt), geri kalan 8 kategoride PTS, REB, AST, 3PM, FT%, BLK kazanarak maçı **6-3 veya 7-2 ezici galibiyetle** bitirmeyi sağlar.

### 3. Sakatlık & Maç Sayısı İndirimi (Kawhi Leonard & Harden Cezası)
Yahoo'nun veri sağlayıcısı (Rotowire), sakatlık geçmişi olan oyunculara acımasız maç sayısı cezası uygular:
* Kawhi Leonard'a sezonda sadece **45-50 maç** oynar projeksiyonu girilmiştir. Bu da 82 maçlık toplam skor tablosunda Kawhi'ın sayı ve top çalma üretiminin %40 yok sayılması demektir.
* Oysa gerçek H2H liginde bir menajer haftalık kadro yönetimi yapar. Kawhi oynadığı haftalarda tam katkı verir (%86 FT, 1.3 STL, 19.5 PTS); dinlendiği günlerde ise Yahoo'nun **IL / IL+ yuvasına** alınıp serbest havuzdan (waiver wire) ek oyuncu oynatılır. Yahoo bu esnekliği modelleyemez.

### 4. Rol Oyuncularının Değeri (Huff, Queta, Hart) vs. Yahoo Popülerlik İndeksi
Yahoo'nun hazır sıralaması (default rank), sadece yüksek skor atan ilk 5 oyuncularına prim verir:
* **Jay Huff (13. Tur):** Yahoo'da 250+ sıradadır. Yahoo onu 'sıfır katkı' sayar. Oysa Huff dakika başına 1.32 Blok ve 1.1 Üçlük atan ligin en değerli blok uzmanıdır.
* **Neemias Queta (8. Tur):** Yahoo listesinde ilk 200'de yoktur; oysa %61 FG ve 1.0 blok sağlar.
* **Josh Hart (7. Tur):** Maç başına 10 sayı attığı için Yahoo'ya göre vasattır; oysa guard pozisyonundan 6.0 Ribaund ve 4.0 Asist getirir.
Yahoo popüler isimler yerine bu yüksek verimli uzmanları aldığımız için takımımıza düşük not vermiştir.

---

## 7. Dış Hakem / Uzman Yapay Zeka (Peer-Review) İçin Tartışma Soruları

Bu raporu sunacağınız diğer yapay zekalara veya uzman analistlere doğrudan şu soruları yöneltebilirsiniz:

1. **Soru 1 (Kategori Optimizasyonu):** 14 takımlı 9-kategori H2H bir ligde; PTS (%71.6), REB (%71.8), BLK (%66.1), FG3M (%67.3) ve FT% (%69.0) gibi 5 ana kategoride ligdeki rakiplerin en az %70'ine üstünlük sağlayan, AST (%56.7) ve STL (%60.1) ile dengeli kalan bir kadronun; sadece TOV (%44.1) düşük diye 12. sıraya layık görülmesi H2H oyun teorisi açısından matematiksel olarak savunulabilir mi?
2. **Soru 2 (Algoritmik Sapma):** Yahoo Fantasy platformunun 'Draft Report Card / Projected Standings' çıktılarının H2H liglerde bile arka planda Rotisserie toplamı kullanması sebebiyle yüksek kullanımlı pasörlere sahip takımları cezalandırdığı tezi doğru mudur?
3. **Soru 3 (Roster Balance):** Jarrett Allen, Nikola Vučević, Neemias Queta, Jay Huff ve Josh Hart gibi isimlerin aynı kadroda yer almasıyla çözülen ribaund/blok problemi; James Harden ve Tyrese Maxey'nin elit serbest atış ve 3 sayı tavanıyla birleştiğinde lig şampiyonluğu için yeterli bir tavan (ceiling) ve taban (floor) sunmakta mıdır?
