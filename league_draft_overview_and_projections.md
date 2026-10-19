# 14 Takımlı Yahoo NBA Fantasy Ligi: Draft Özeti, Kadrolar ve Model Projeksiyonları

> **Doküman Niteliği:** Bu belge, 18 Ekim 2026 tarihinde gerçekleştirilen 14 takımlı canlı Yahoo Fantasy draftının seçim sıralamasını, oluşan kadroları, Poisson-Binomial simülasyon modelinin çıktılarını ve Yahoo resmi sıralama verisini **tamamen tarafsız, nesnel ve yorumsuz** olarak sunmak amacıyla hazırlanmıştır.

---

## 1. Temel Lig Bilgileri ve Format

- **Format:** 9-Kategori Head-to-Head (H2H)
- **Kategoriler:** Points (PTS), Rebounds (REB), Assists (AST), Steals (STL), Blocks (BLK), 3-Pointers Made (FG3M), Turnovers (TOV), Field Goal Percentage (FG%), Free Throw Percentage (FT%)
- **Takım Sayısı:** 14
- **Kadro Boyutu:** 13 Oyuncu (10 Aktif Kadro Yuvası + 3 Yedek Yuvası)
- **Draft Türü:** Yılan Tipi (Snake Draft) — 13 Tur, Toplam 182 Seçim
- **İncelenen Takım:** Berk's Best Team (Slot #8)
- **Draft Tarihi:** 18 Ekim 2026

---

## 2. 14 Takımın Draft Sırası (Slot) ve Tam Kadroları

### Slot #1: MuCa Tandır
| Tur | Genel Sıra | Oyuncu | NBA Takımı | Pozisyon |
| :---: | :---: | :--- | :---: | :---: |
| 1 | #1 | Nikola Jokić | DEN | C |
| 2 | #28 | Jalen Brunson | NYK | PG |
| 3 | #29 | Evan Mobley | CLE | PF,C |
| 4 | #56 | Cameron Boozer | MEM | PF |
| 5 | #57 | Kon Knueppel | CHA | SG,SF |
| 6 | #84 | Caleb Wilson | CHI | PF |
| 7 | #85 | Norman Powell | CHI | SG,SF |
| 8 | #112 | Cason Wallace | OKC | PG,SG,SF |
| 9 | #113 | Herbert Jones | NOP | SG,SF |
| 10 | #140 | Sandro Mamukelashvili | LAL | PF,C |
| 11 | #141 | Alex Caruso | OKC | SG,SF |
| 12 | #168 | Scotty Pippen Jr. | MEM | PG |
| 13 | #169 | Kelly Oubre Jr. | IND | SF,PF |

### Slot #2: Mordor Tulums
| Tur | Genel Sıra | Oyuncu | NBA Takımı | Pozisyon |
| :---: | :---: | :--- | :---: | :---: |
| 1 | #2 | Victor Wembanyama | SAS | C |
| 2 | #27 | Trey Murphy III | NOP | SG,SF |
| 3 | #30 | Chet Holmgren | OKC | PF,C |
| 4 | #55 | Damian Lillard | POR | PG |
| 5 | #58 | OG Anunoby | NYK | SF,PF |
| 6 | #83 | Ty Jerome | MEM | PG,SG |
| 7 | #86 | John Collins | DET | PF,C |
| 8 | #111 | Tobias Harris | SAS | PF |
| 9 | #114 | Cameron Johnson | DEN | SF,PF |
| 10 | #139 | Peyton Watson | CLE | SF,PF |
| 11 | #142 | Mitchell Robinson | BOS | C |
| 12 | #167 | Robert Williams III | POR | C |
| 13 | #170 | Sam Hauser | BOS | SF,PF |

### Slot #3: Philadelphia Sikers
| Tur | Genel Sıra | Oyuncu | NBA Takımı | Pozisyon |
| :---: | :---: | :--- | :---: | :---: |
| 1 | #3 | Luka Dončić | LAL | PG,SG |
| 2 | #26 | Trae Young | WAS | PG |
| 3 | #31 | Lauri Markkanen | UTA | SF,PF |
| 4 | #54 | Ivica Zubac | IND | C |
| 5 | #59 | Darius Garland | LAC | PG |
| 6 | #82 | Immanuel Quickley | TOR | PG,SG |
| 7 | #87 | Alex Sarr | WAS | C |
| 8 | #110 | Toumani Camara | POR | SF,PF |
| 9 | #115 | Jalen Green | PHX | SG,SF |
| 10 | #138 | Jakob Poeltl | TOR | C |
| 11 | #143 | Jonathan Kuminga | MIN | SF,PF |
| 12 | #166 | Jerami Grant | MEM | SF,PF |
| 13 | #171 | Bennedict Mathurin | NOP | SG,SF |

### Slot #4: Houston Buckets
| Tur | Genel Sıra | Oyuncu | NBA Takımı | Pozisyon |
| :---: | :---: | :--- | :---: | :---: |
| 1 | #4 | Shai Gilgeous-Alexander | OKC | PG |
| 2 | #25 | Stephen Curry | GSW | PG |
| 3 | #32 | Jalen Williams | OKC | SF,PF |
| 4 | #53 | Jaylen Brown | PHI | SG,SF,PF |
| 5 | #60 | Nic Claxton | CHI | C |
| 6 | #81 | Derik Queen | NOP | PF,C |
| 7 | #88 | Keegan Murray | SAC | SF,PF |
| 8 | #109 | Andrew Wiggins | MIA | SG,SF,PF |
| 9 | #116 | Brook Lopez | LAC | C |
| 10 | #137 | Tim Hardaway Jr. | MIA | SG,SF |
| 11 | #144 | DeMar DeRozan | DEN | SF,PF |
| 12 | #165 | Jrue Holiday | POR | PG,SG |
| 13 | #172 | Tre Jones | CHI | PG,SG |

### Slot #5: Kuvâ-yi Milfiye
| Tur | Genel Sıra | Oyuncu | NBA Takımı | Pozisyon |
| :---: | :---: | :--- | :---: | :---: |
| 1 | #5 | Cade Cunningham | DET | PG,SG |
| 2 | #24 | Devin Booker | PHX | PG,SG |
| 3 | #33 | Walker Kessler | LAL | C |
| 4 | #52 | Nickeil Alexander-Walker | ATL | PG,SG |
| 5 | #61 | Michael Porter Jr. | BKN | SF,PF |
| 6 | #80 | Naz Reid | CHA | PF,C |
| 7 | #89 | Cedric Coward | MEM | SG,SF |
| 8 | #108 | Miles Bridges | PHX | PF |
| 9 | #117 | Darryn Peterson | UTA | SG |
| 10 | #136 | Gui Santos | GSW | SF,PF |
| 11 | #145 | Ace Bailey | UTA | SF,PF |
| 12 | #164 | Mikel Brown Jr. | BKN | PG |
| 13 | #173 | Moussa Diabaté | CHA | C |

### Slot #6: abu dhabi camels
| Tur | Genel Sıra | Oyuncu | NBA Takımı | Pozisyon |
| :---: | :---: | :--- | :---: | :---: |
| 1 | #6 | Giannis Antetokounmpo | MIA | PF,C |
| 2 | #23 | LaMelo Ball | MIN | PG |
| 3 | #34 | Josh Giddey | CHI | PG,SG |
| 4 | #51 | Franz Wagner | ORL | SF,PF |
| 5 | #62 | Dyson Daniels | ATL | SG,SF |
| 6 | #79 | Joel Embiid | PHI | C |
| 7 | #90 | AJ Dybantsa | WAS | SF |
| 8 | #107 | CJ McCollum | ATL | PG,SG |
| 9 | #118 | Khaman Maluach | PHX | C |
| 10 | #135 | Ajay Mitchell | OKC | PG,SG |
| 11 | #146 | Daniel Gafford | DAL | C |
| 12 | #163 | Aaron Nesmith | IND | SG,SF |
| 13 | #174 | Anthony Black | ORL | PG,SG,SF |

### Slot #7: Samurai Strikers
| Tur | Genel Sıra | Oyuncu | NBA Takımı | Pozisyon |
| :---: | :---: | :--- | :---: | :---: |
| 1 | #7 | Jayson Tatum | BOS | SF,PF |
| 2 | #22 | Amen Thompson | HOU | PG,SG |
| 3 | #35 | Domantas Sabonis | SAC | PF,C |
| 4 | #50 | Donovan Clingan | POR | C |
| 5 | #63 | LeBron James | PHI | SF,PF |
| 6 | #78 | Tyler Herro | MIL | PG,SG |
| 7 | #91 | Ausar Thompson | DET | SG,SF,PF |
| 8 | #106 | Day'Ron Sharpe | BKN | C |
| 9 | #119 | Brandin Podziemski | GSW | PG,SG |
| 10 | #134 | Andrew Nembhard | IND | PG,SG |
| 11 | #147 | Reed Sheppard | HOU | PG,SG |
| 12 | #162 | Grayson Allen | CHA | SG,SF |
| 13 | #175 | Jeremiah Fears | NOP | PG,SG |

### Slot #8: Berk's Best Team
| Tur | Genel Sıra | Oyuncu | NBA Takımı | Pozisyon |
| :---: | :---: | :--- | :---: | :---: |
| 1 | #8 | Tyrese Maxey | PHI | PG |
| 2 | #21 | James Harden | CLE | PG,SG |
| 3 | #36 | Kawhi Leonard | TOR | SG,SF,PF |
| 4 | #49 | Desmond Bane | ORL | SG,SF |
| 5 | #64 | Jarrett Allen | CLE | C |
| 6 | #77 | Jabari Smith Jr. | HOU | PF,C |
| 7 | #92 | Josh Hart | NYK | SG,SF |
| 8 | #105 | Neemias Queta | BOS | C |
| 9 | #120 | Brandon Ingram | LAC | SG,SF,PF |
| 10 | #133 | Ayo Dosunmu | MIN | PG,SG |
| 11 | #148 | Nikola Vučević | ORL | C |
| 12 | #161 | Julian Champagnie | SAS | SF,PF |
| 13 | #176 | Jay Huff | IND | C |

### Slot #9: FatihTerimSpor
| Tur | Genel Sıra | Oyuncu | NBA Takımı | Pozisyon |
| :---: | :---: | :--- | :---: | :---: |
| 1 | #9 | Anthony Edwards | MIN | PG,SG |
| 2 | #20 | Jalen Duren | DET | C |
| 3 | #37 | Keyonte George | UTA | PG,SG |
| 4 | #48 | Paolo Banchero | ORL | PF |
| 5 | #65 | Stephon Castle | SAS | PG,SG |
| 6 | #76 | Paul George | BOS | SF,PF |
| 7 | #93 | Ja Morant | POR | PG |
| 8 | #104 | Aaron Gordon | DEN | PF,C |
| 9 | #121 | RJ Barrett | TOR | SG,SF,PF |
| 10 | #132 | Quentin Grimes | LAL | SG,SF |
| 11 | #149 | Dillon Brooks | PHX | SF,PF |
| 12 | #160 | Bobby Portis Jr. | MIA | PF,C |
| 13 | #177 | Deandre Ayton | WAS | C |

### Slot #10: Redeem Team
| Tur | Genel Sıra | Oyuncu | NBA Takımı | Pozisyon |
| :---: | :---: | :--- | :---: | :---: |
| 1 | #10 | Tyrese Haliburton | IND | PG,SG |
| 2 | #19 | Austin Reaves | LAL | PG,SG,SF |
| 3 | #38 | Onyeka Okongwu | ATL | C |
| 4 | #47 | Pascal Siakam | IND | PF,C |
| 5 | #66 | Mikal Bridges | NYK | SF,PF |
| 6 | #75 | Rudy Gobert | MIN | C |
| 7 | #94 | Zion Williamson | NOP | PF,C |
| 8 | #103 | Fred VanVleet | HOU | PG |
| 9 | #122 | Kevin Porter Jr. | MIL | PG,SG |
| 10 | #131 | Devin Vassell | SAS | SG,SF |
| 11 | #150 | Wendell Carter Jr. | ORL | C |
| 12 | #159 | Draymond Green | GSW | PF,C |
| 13 | #178 | Ben Simmons | SAC | PG |

### Slot #11: Fikirtepe Warriors
| Tur | Genel Sıra | Oyuncu | NBA Takımı | Pozisyon |
| :---: | :---: | :--- | :---: | :---: |
| 1 | #11 | Cooper Flagg | DAL | SG,SF,PF |
| 2 | #18 | Karl-Anthony Towns | NYK | PF,C |
| 3 | #39 | Bam Adebayo | MIA | PF,C |
| 4 | #46 | Deni Avdija | POR | SG,SF,PF |
| 5 | #67 | Dejounte Murray | NOP | PG |
| 6 | #74 | Jaden McDaniels | MIN | SF |
| 7 | #95 | Coby White | CHA | PG,SG |
| 8 | #102 | Myles Turner | MIL | C |
| 9 | #123 | Yaxel Lendeborg | GSW | PF |
| 10 | #130 | Egor Dëmin | BKN | PG,SG |
| 11 | #151 | Saddiq Bey | NOP | SF,PF |
| 12 | #158 | Isaiah Jackson | LAC | C |
| 13 | #179 | Zaccharie Risacher | DAL | SF,PF |

### Slot #12: Istanbul Brickmakers
| Tur | Genel Sıra | Oyuncu | NBA Takımı | Pozisyon |
| :---: | :---: | :--- | :---: | :---: |
| 1 | #12 | Jalen Johnson | ATL | SF,PF |
| 2 | #17 | Kevin Durant | HOU | SG,SF,PF |
| 3 | #40 | Kyrie Irving | DAL | PG |
| 4 | #45 | Anthony Davis | WAS | PF,C |
| 5 | #68 | Ryan Rollins | MIL | PG,SG |
| 6 | #73 | Zach Edey | MEM | C |
| 7 | #96 | Dylan Harper | SAS | PG,SG |
| 8 | #101 | Zach LaVine | SAC | PG,SG,SF |
| 9 | #124 | Darius Acuff Jr. | SAC | PG |
| 10 | #129 | Rui Hachimura | LAC | SF,PF |
| 11 | #152 | Yves Missi | NOP | C |
| 12 | #157 | Jaylen Wells | MEM | SG,SF |
| 13 | #180 | Jake LaRavia | LAL | SF,PF |

### Slot #13: SILE BULLS
| Tur | Genel Sıra | Oyuncu | NBA Takımı | Pozisyon |
| :---: | :---: | :--- | :---: | :---: |
| 1 | #13 | Donovan Mitchell | CLE | PG,SG |
| 2 | #16 | Scottie Barnes | TOR | SF,PF,C |
| 3 | #41 | Derrick White | BOS | PG,SG |
| 4 | #44 | Jaren Jackson Jr. | UTA | PF,C |
| 5 | #69 | Payton Pritchard | BOS | PG |
| 6 | #72 | Julius Randle | BKN | PF |
| 7 | #97 | VJ Edgecombe | PHI | PG,SG |
| 8 | #100 | Isaiah Hartenstein | OKC | C |
| 9 | #125 | Collin Gillespie | PHX | PG,SG |
| 10 | #128 | Kyshawn George | WAS | SG,SF,PF |
| 11 | #153 | P.J. Washington | DAL | PF,C |
| 12 | #156 | Jimmy Butler III | GSW | SF,PF |
| 13 | #181 | Pelle Larsson | MIA | SG,SF |

### Slot #14: YearOne Tyrants
| Tur | Genel Sıra | Oyuncu | NBA Takımı | Pozisyon |
| :---: | :---: | :--- | :---: | :---: |
| 1 | #14 | Alperen Şengün | HOU | PF,C |
| 2 | #15 | Jamal Murray | DEN | PG |
| 3 | #42 | Matas Buzelis | CHI | SF,PF |
| 4 | #43 | Brandon Miller | CHA | SF,PF |
| 5 | #70 | Kel'el Ware | MIL | C |
| 6 | #71 | De'Aaron Fox | SAS | PG |
| 7 | #98 | Jalen Suggs | ORL | PG,SG |
| 8 | #99 | Collin Murray-Boyles | TOR | PF,C |
| 9 | #126 | Jaime Jaquez Jr. | MIL | SG,SF,PF |
| 10 | #127 | Christian Braun | DEN | SG,SF,PF |
| 11 | #154 | Davion Mitchell | MIA | PG |
| 12 | #155 | Tari Eason | HOU | SG,SF,PF |
| 13 | #182 | Scoot Henderson | POR | PG |

---

## 3. Tur Tur Draft Seçim Sıralaması (Tüm 182 Seçim)

| Genel # | Tur | Tur İçi # | Oyuncu | NBA Takımı | Pozisyon | Seçen Takım | Slot |
| :---: | :---: | :---: | :--- | :---: | :---: | :--- | :---: |
| #1 | R1 | 1 | Nikola Jokić | DEN | C | MuCa Tandır | #1 |
| #2 | R1 | 2 | Victor Wembanyama | SAS | C | Mordor Tulums | #2 |
| #3 | R1 | 3 | Luka Dončić | LAL | PG,SG | Philadelphia Sikers | #3 |
| #4 | R1 | 4 | Shai Gilgeous-Alexander | OKC | PG | Houston Buckets | #4 |
| #5 | R1 | 5 | Cade Cunningham | DET | PG,SG | Kuvâ-yi Milfiye | #5 |
| #6 | R1 | 6 | Giannis Antetokounmpo | MIA | PF,C | abu dhabi camels | #6 |
| #7 | R1 | 7 | Jayson Tatum | BOS | SF,PF | Samurai Strikers | #7 |
| #8 | R1 | 8 | Tyrese Maxey | PHI | PG | Berk's Best Team | #8 |
| #9 | R1 | 9 | Anthony Edwards | MIN | PG,SG | FatihTerimSpor | #9 |
| #10 | R1 | 10 | Tyrese Haliburton | IND | PG,SG | Redeem Team | #10 |
| #11 | R1 | 11 | Cooper Flagg | DAL | SG,SF,PF | Fikirtepe Warriors | #11 |
| #12 | R1 | 12 | Jalen Johnson | ATL | SF,PF | Istanbul Brickmakers | #12 |
| #13 | R1 | 13 | Donovan Mitchell | CLE | PG,SG | SILE BULLS | #13 |
| #14 | R1 | 14 | Alperen Şengün | HOU | PF,C | YearOne Tyrants | #14 |
| #15 | R2 | 1 | Jamal Murray | DEN | PG | YearOne Tyrants | #14 |
| #16 | R2 | 2 | Scottie Barnes | TOR | SF,PF,C | SILE BULLS | #13 |
| #17 | R2 | 3 | Kevin Durant | HOU | SG,SF,PF | Istanbul Brickmakers | #12 |
| #18 | R2 | 4 | Karl-Anthony Towns | NYK | PF,C | Fikirtepe Warriors | #11 |
| #19 | R2 | 5 | Austin Reaves | LAL | PG,SG,SF | Redeem Team | #10 |
| #20 | R2 | 6 | Jalen Duren | DET | C | FatihTerimSpor | #9 |
| #21 | R2 | 7 | James Harden | CLE | PG,SG | Berk's Best Team | #8 |
| #22 | R2 | 8 | Amen Thompson | HOU | PG,SG | Samurai Strikers | #7 |
| #23 | R2 | 9 | LaMelo Ball | MIN | PG | abu dhabi camels | #6 |
| #24 | R2 | 10 | Devin Booker | PHX | PG,SG | Kuvâ-yi Milfiye | #5 |
| #25 | R2 | 11 | Stephen Curry | GSW | PG | Houston Buckets | #4 |
| #26 | R2 | 12 | Trae Young | WAS | PG | Philadelphia Sikers | #3 |
| #27 | R2 | 13 | Trey Murphy III | NOP | SG,SF | Mordor Tulums | #2 |
| #28 | R2 | 14 | Jalen Brunson | NYK | PG | MuCa Tandır | #1 |
| #29 | R3 | 1 | Evan Mobley | CLE | PF,C | MuCa Tandır | #1 |
| #30 | R3 | 2 | Chet Holmgren | OKC | PF,C | Mordor Tulums | #2 |
| #31 | R3 | 3 | Lauri Markkanen | UTA | SF,PF | Philadelphia Sikers | #3 |
| #32 | R3 | 4 | Jalen Williams | OKC | SF,PF | Houston Buckets | #4 |
| #33 | R3 | 5 | Walker Kessler | LAL | C | Kuvâ-yi Milfiye | #5 |
| #34 | R3 | 6 | Josh Giddey | CHI | PG,SG | abu dhabi camels | #6 |
| #35 | R3 | 7 | Domantas Sabonis | SAC | PF,C | Samurai Strikers | #7 |
| #36 | R3 | 8 | Kawhi Leonard | TOR | SG,SF,PF | Berk's Best Team | #8 |
| #37 | R3 | 9 | Keyonte George | UTA | PG,SG | FatihTerimSpor | #9 |
| #38 | R3 | 10 | Onyeka Okongwu | ATL | C | Redeem Team | #10 |
| #39 | R3 | 11 | Bam Adebayo | MIA | PF,C | Fikirtepe Warriors | #11 |
| #40 | R3 | 12 | Kyrie Irving | DAL | PG | Istanbul Brickmakers | #12 |
| #41 | R3 | 13 | Derrick White | BOS | PG,SG | SILE BULLS | #13 |
| #42 | R3 | 14 | Matas Buzelis | CHI | SF,PF | YearOne Tyrants | #14 |
| #43 | R4 | 1 | Brandon Miller | CHA | SF,PF | YearOne Tyrants | #14 |
| #44 | R4 | 2 | Jaren Jackson Jr. | UTA | PF,C | SILE BULLS | #13 |
| #45 | R4 | 3 | Anthony Davis | WAS | PF,C | Istanbul Brickmakers | #12 |
| #46 | R4 | 4 | Deni Avdija | POR | SG,SF,PF | Fikirtepe Warriors | #11 |
| #47 | R4 | 5 | Pascal Siakam | IND | PF,C | Redeem Team | #10 |
| #48 | R4 | 6 | Paolo Banchero | ORL | PF | FatihTerimSpor | #9 |
| #49 | R4 | 7 | Desmond Bane | ORL | SG,SF | Berk's Best Team | #8 |
| #50 | R4 | 8 | Donovan Clingan | POR | C | Samurai Strikers | #7 |
| #51 | R4 | 9 | Franz Wagner | ORL | SF,PF | abu dhabi camels | #6 |
| #52 | R4 | 10 | Nickeil Alexander-Walker | ATL | PG,SG | Kuvâ-yi Milfiye | #5 |
| #53 | R4 | 11 | Jaylen Brown | PHI | SG,SF,PF | Houston Buckets | #4 |
| #54 | R4 | 12 | Ivica Zubac | IND | C | Philadelphia Sikers | #3 |
| #55 | R4 | 13 | Damian Lillard | POR | PG | Mordor Tulums | #2 |
| #56 | R4 | 14 | Cameron Boozer | MEM | PF | MuCa Tandır | #1 |
| #57 | R5 | 1 | Kon Knueppel | CHA | SG,SF | MuCa Tandır | #1 |
| #58 | R5 | 2 | OG Anunoby | NYK | SF,PF | Mordor Tulums | #2 |
| #59 | R5 | 3 | Darius Garland | LAC | PG | Philadelphia Sikers | #3 |
| #60 | R5 | 4 | Nic Claxton | CHI | C | Houston Buckets | #4 |
| #61 | R5 | 5 | Michael Porter Jr. | BKN | SF,PF | Kuvâ-yi Milfiye | #5 |
| #62 | R5 | 6 | Dyson Daniels | ATL | SG,SF | abu dhabi camels | #6 |
| #63 | R5 | 7 | LeBron James | PHI | SF,PF | Samurai Strikers | #7 |
| #64 | R5 | 8 | Jarrett Allen | CLE | C | Berk's Best Team | #8 |
| #65 | R5 | 9 | Stephon Castle | SAS | PG,SG | FatihTerimSpor | #9 |
| #66 | R5 | 10 | Mikal Bridges | NYK | SF,PF | Redeem Team | #10 |
| #67 | R5 | 11 | Dejounte Murray | NOP | PG | Fikirtepe Warriors | #11 |
| #68 | R5 | 12 | Ryan Rollins | MIL | PG,SG | Istanbul Brickmakers | #12 |
| #69 | R5 | 13 | Payton Pritchard | BOS | PG | SILE BULLS | #13 |
| #70 | R5 | 14 | Kel'el Ware | MIL | C | YearOne Tyrants | #14 |
| #71 | R6 | 1 | De'Aaron Fox | SAS | PG | YearOne Tyrants | #14 |
| #72 | R6 | 2 | Julius Randle | BKN | PF | SILE BULLS | #13 |
| #73 | R6 | 3 | Zach Edey | MEM | C | Istanbul Brickmakers | #12 |
| #74 | R6 | 4 | Jaden McDaniels | MIN | SF | Fikirtepe Warriors | #11 |
| #75 | R6 | 5 | Rudy Gobert | MIN | C | Redeem Team | #10 |
| #76 | R6 | 6 | Paul George | BOS | SF,PF | FatihTerimSpor | #9 |
| #77 | R6 | 7 | Jabari Smith Jr. | HOU | PF,C | Berk's Best Team | #8 |
| #78 | R6 | 8 | Tyler Herro | MIL | PG,SG | Samurai Strikers | #7 |
| #79 | R6 | 9 | Joel Embiid | PHI | C | abu dhabi camels | #6 |
| #80 | R6 | 10 | Naz Reid | CHA | PF,C | Kuvâ-yi Milfiye | #5 |
| #81 | R6 | 11 | Derik Queen | NOP | PF,C | Houston Buckets | #4 |
| #82 | R6 | 12 | Immanuel Quickley | TOR | PG,SG | Philadelphia Sikers | #3 |
| #83 | R6 | 13 | Ty Jerome | MEM | PG,SG | Mordor Tulums | #2 |
| #84 | R6 | 14 | Caleb Wilson | CHI | PF | MuCa Tandır | #1 |
| #85 | R7 | 1 | Norman Powell | CHI | SG,SF | MuCa Tandır | #1 |
| #86 | R7 | 2 | John Collins | DET | PF,C | Mordor Tulums | #2 |
| #87 | R7 | 3 | Alex Sarr | WAS | C | Philadelphia Sikers | #3 |
| #88 | R7 | 4 | Keegan Murray | SAC | SF,PF | Houston Buckets | #4 |
| #89 | R7 | 5 | Cedric Coward | MEM | SG,SF | Kuvâ-yi Milfiye | #5 |
| #90 | R7 | 6 | AJ Dybantsa | WAS | SF | abu dhabi camels | #6 |
| #91 | R7 | 7 | Ausar Thompson | DET | SG,SF,PF | Samurai Strikers | #7 |
| #92 | R7 | 8 | Josh Hart | NYK | SG,SF | Berk's Best Team | #8 |
| #93 | R7 | 9 | Ja Morant | POR | PG | FatihTerimSpor | #9 |
| #94 | R7 | 10 | Zion Williamson | NOP | PF,C | Redeem Team | #10 |
| #95 | R7 | 11 | Coby White | CHA | PG,SG | Fikirtepe Warriors | #11 |
| #96 | R7 | 12 | Dylan Harper | SAS | PG,SG | Istanbul Brickmakers | #12 |
| #97 | R7 | 13 | VJ Edgecombe | PHI | PG,SG | SILE BULLS | #13 |
| #98 | R7 | 14 | Jalen Suggs | ORL | PG,SG | YearOne Tyrants | #14 |
| #99 | R8 | 1 | Collin Murray-Boyles | TOR | PF,C | YearOne Tyrants | #14 |
| #100 | R8 | 2 | Isaiah Hartenstein | OKC | C | SILE BULLS | #13 |
| #101 | R8 | 3 | Zach LaVine | SAC | PG,SG,SF | Istanbul Brickmakers | #12 |
| #102 | R8 | 4 | Myles Turner | MIL | C | Fikirtepe Warriors | #11 |
| #103 | R8 | 5 | Fred VanVleet | HOU | PG | Redeem Team | #10 |
| #104 | R8 | 6 | Aaron Gordon | DEN | PF,C | FatihTerimSpor | #9 |
| #105 | R8 | 7 | Neemias Queta | BOS | C | Berk's Best Team | #8 |
| #106 | R8 | 8 | Day'Ron Sharpe | BKN | C | Samurai Strikers | #7 |
| #107 | R8 | 9 | CJ McCollum | ATL | PG,SG | abu dhabi camels | #6 |
| #108 | R8 | 10 | Miles Bridges | PHX | PF | Kuvâ-yi Milfiye | #5 |
| #109 | R8 | 11 | Andrew Wiggins | MIA | SG,SF,PF | Houston Buckets | #4 |
| #110 | R8 | 12 | Toumani Camara | POR | SF,PF | Philadelphia Sikers | #3 |
| #111 | R8 | 13 | Tobias Harris | SAS | PF | Mordor Tulums | #2 |
| #112 | R8 | 14 | Cason Wallace | OKC | PG,SG,SF | MuCa Tandır | #1 |
| #113 | R9 | 1 | Herbert Jones | NOP | SG,SF | MuCa Tandır | #1 |
| #114 | R9 | 2 | Cameron Johnson | DEN | SF,PF | Mordor Tulums | #2 |
| #115 | R9 | 3 | Jalen Green | PHX | SG,SF | Philadelphia Sikers | #3 |
| #116 | R9 | 4 | Brook Lopez | LAC | C | Houston Buckets | #4 |
| #117 | R9 | 5 | Darryn Peterson | UTA | SG | Kuvâ-yi Milfiye | #5 |
| #118 | R9 | 6 | Khaman Maluach | PHX | C | abu dhabi camels | #6 |
| #119 | R9 | 7 | Brandin Podziemski | GSW | PG,SG | Samurai Strikers | #7 |
| #120 | R9 | 8 | Brandon Ingram | LAC | SG,SF,PF | Berk's Best Team | #8 |
| #121 | R9 | 9 | RJ Barrett | TOR | SG,SF,PF | FatihTerimSpor | #9 |
| #122 | R9 | 10 | Kevin Porter Jr. | MIL | PG,SG | Redeem Team | #10 |
| #123 | R9 | 11 | Yaxel Lendeborg | GSW | PF | Fikirtepe Warriors | #11 |
| #124 | R9 | 12 | Darius Acuff Jr. | SAC | PG | Istanbul Brickmakers | #12 |
| #125 | R9 | 13 | Collin Gillespie | PHX | PG,SG | SILE BULLS | #13 |
| #126 | R9 | 14 | Jaime Jaquez Jr. | MIL | SG,SF,PF | YearOne Tyrants | #14 |
| #127 | R10 | 1 | Christian Braun | DEN | SG,SF,PF | YearOne Tyrants | #14 |
| #128 | R10 | 2 | Kyshawn George | WAS | SG,SF,PF | SILE BULLS | #13 |
| #129 | R10 | 3 | Rui Hachimura | LAC | SF,PF | Istanbul Brickmakers | #12 |
| #130 | R10 | 4 | Egor Dëmin | BKN | PG,SG | Fikirtepe Warriors | #11 |
| #131 | R10 | 5 | Devin Vassell | SAS | SG,SF | Redeem Team | #10 |
| #132 | R10 | 6 | Quentin Grimes | LAL | SG,SF | FatihTerimSpor | #9 |
| #133 | R10 | 7 | Ayo Dosunmu | MIN | PG,SG | Berk's Best Team | #8 |
| #134 | R10 | 8 | Andrew Nembhard | IND | PG,SG | Samurai Strikers | #7 |
| #135 | R10 | 9 | Ajay Mitchell | OKC | PG,SG | abu dhabi camels | #6 |
| #136 | R10 | 10 | Gui Santos | GSW | SF,PF | Kuvâ-yi Milfiye | #5 |
| #137 | R10 | 11 | Tim Hardaway Jr. | MIA | SG,SF | Houston Buckets | #4 |
| #138 | R10 | 12 | Jakob Poeltl | TOR | C | Philadelphia Sikers | #3 |
| #139 | R10 | 13 | Peyton Watson | CLE | SF,PF | Mordor Tulums | #2 |
| #140 | R10 | 14 | Sandro Mamukelashvili | LAL | PF,C | MuCa Tandır | #1 |
| #141 | R11 | 1 | Alex Caruso | OKC | SG,SF | MuCa Tandır | #1 |
| #142 | R11 | 2 | Mitchell Robinson | BOS | C | Mordor Tulums | #2 |
| #143 | R11 | 3 | Jonathan Kuminga | MIN | SF,PF | Philadelphia Sikers | #3 |
| #144 | R11 | 4 | DeMar DeRozan | DEN | SF,PF | Houston Buckets | #4 |
| #145 | R11 | 5 | Ace Bailey | UTA | SF,PF | Kuvâ-yi Milfiye | #5 |
| #146 | R11 | 6 | Daniel Gafford | DAL | C | abu dhabi camels | #6 |
| #147 | R11 | 7 | Reed Sheppard | HOU | PG,SG | Samurai Strikers | #7 |
| #148 | R11 | 8 | Nikola Vučević | ORL | C | Berk's Best Team | #8 |
| #149 | R11 | 9 | Dillon Brooks | PHX | SF,PF | FatihTerimSpor | #9 |
| #150 | R11 | 10 | Wendell Carter Jr. | ORL | C | Redeem Team | #10 |
| #151 | R11 | 11 | Saddiq Bey | NOP | SF,PF | Fikirtepe Warriors | #11 |
| #152 | R11 | 12 | Yves Missi | NOP | C | Istanbul Brickmakers | #12 |
| #153 | R11 | 13 | P.J. Washington | DAL | PF,C | SILE BULLS | #13 |
| #154 | R11 | 14 | Davion Mitchell | MIA | PG | YearOne Tyrants | #14 |
| #155 | R12 | 1 | Tari Eason | HOU | SG,SF,PF | YearOne Tyrants | #14 |
| #156 | R12 | 2 | Jimmy Butler III | GSW | SF,PF | SILE BULLS | #13 |
| #157 | R12 | 3 | Jaylen Wells | MEM | SG,SF | Istanbul Brickmakers | #12 |
| #158 | R12 | 4 | Isaiah Jackson | LAC | C | Fikirtepe Warriors | #11 |
| #159 | R12 | 5 | Draymond Green | GSW | PF,C | Redeem Team | #10 |
| #160 | R12 | 6 | Bobby Portis Jr. | MIA | PF,C | FatihTerimSpor | #9 |
| #161 | R12 | 7 | Julian Champagnie | SAS | SF,PF | Berk's Best Team | #8 |
| #162 | R12 | 8 | Grayson Allen | CHA | SG,SF | Samurai Strikers | #7 |
| #163 | R12 | 9 | Aaron Nesmith | IND | SG,SF | abu dhabi camels | #6 |
| #164 | R12 | 10 | Mikel Brown Jr. | BKN | PG | Kuvâ-yi Milfiye | #5 |
| #165 | R12 | 11 | Jrue Holiday | POR | PG,SG | Houston Buckets | #4 |
| #166 | R12 | 12 | Jerami Grant | MEM | SF,PF | Philadelphia Sikers | #3 |
| #167 | R12 | 13 | Robert Williams III | POR | C | Mordor Tulums | #2 |
| #168 | R12 | 14 | Scotty Pippen Jr. | MEM | PG | MuCa Tandır | #1 |
| #169 | R13 | 1 | Kelly Oubre Jr. | IND | SF,PF | MuCa Tandır | #1 |
| #170 | R13 | 2 | Sam Hauser | BOS | SF,PF | Mordor Tulums | #2 |
| #171 | R13 | 3 | Bennedict Mathurin | NOP | SG,SF | Philadelphia Sikers | #3 |
| #172 | R13 | 4 | Tre Jones | CHI | PG,SG | Houston Buckets | #4 |
| #173 | R13 | 5 | Moussa Diabaté | CHA | C | Kuvâ-yi Milfiye | #5 |
| #174 | R13 | 6 | Anthony Black | ORL | PG,SG,SF | abu dhabi camels | #6 |
| #175 | R13 | 7 | Jeremiah Fears | NOP | PG,SG | Samurai Strikers | #7 |
| #176 | R13 | 8 | Jay Huff | IND | C | Berk's Best Team | #8 |
| #177 | R13 | 9 | Deandre Ayton | WAS | C | FatihTerimSpor | #9 |
| #178 | R13 | 10 | Ben Simmons | SAC | PG | Redeem Team | #10 |
| #179 | R13 | 11 | Zaccharie Risacher | DAL | SF,PF | Fikirtepe Warriors | #11 |
| #180 | R13 | 12 | Jake LaRavia | LAL | SF,PF | Istanbul Brickmakers | #12 |
| #181 | R13 | 13 | Pelle Larsson | MIA | SG,SF | SILE BULLS | #13 |
| #182 | R13 | 14 | Scoot Henderson | POR | PG | YearOne Tyrants | #14 |

---

## 4. 'Berk's Best Team' (Slot #8) Kadrosu ve İstatistiksel Projeksiyonları

### A. Oyuncu Bazlı Maç Başına Ham Projeksiyon Verileri (Bayesian Model)

| Oyuncu | Mevki | PTS | REB | AST | STL | BLK | 3PM | TOV | FG% | FT% |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Tyrese Maxey | G | 21.1 | 3.3 | 5.0 | 1.39 | 0.54 | 2.4 | 1.9 | 45.7% | 87.5% |
| James Harden | G | 18.4 | 4.1 | 6.3 | 1.00 | 0.38 | 2.4 | 2.8 | 43.2% | 87.1% |
| Kawhi Leonard | F | 19.6 | 4.9 | 2.7 | 1.29 | 0.37 | 1.9 | 1.5 | 50.0% | 86.3% |
| Desmond Bane | G | 16.3 | 3.7 | 3.6 | 0.92 | 0.37 | 1.8 | 1.7 | 47.8% | 88.4% |
| Jarrett Allen | C | 11.5 | 6.9 | 1.5 | 0.74 | 0.72 | 0.1 | 1.1 | 61.8% | 71.7% |
| Jabari Smith Jr. | F | 12.9 | 5.8 | 1.6 | 0.64 | 0.73 | 1.8 | 1.2 | 45.4% | 77.9% |
| Josh Hart | G | 10.3 | 6.0 | 4.0 | 0.98 | 0.24 | 1.2 | 1.6 | 49.5% | 76.9% |
| Neemias Queta | C | 8.3 | 6.4 | 1.4 | 0.60 | 0.99 | 0.1 | 0.9 | 61.1% | 71.7% |
| Brandon Ingram | F | 17.3 | 4.7 | 3.1 | 0.68 | 0.59 | 1.5 | 2.0 | 47.6% | 81.1% |
| Ayo Dosunmu | G | 11.9 | 2.9 | 3.1 | 0.75 | 0.24 | 1.4 | 1.2 | 49.8% | 84.5% |
| Nikola Vučević | C | 11.5 | 6.5 | 2.4 | 0.52 | 0.57 | 1.1 | 1.1 | 50.9% | 77.7% |
| Julian Champagnie | F | 9.6 | 4.6 | 1.4 | 0.68 | 0.42 | 1.9 | 0.8 | 44.5% | 81.8% |
| Jay Huff | C | 8.1 | 3.5 | 1.2 | 0.43 | 1.32 | 1.1 | 0.8 | 49.6% | 77.7% |
| **Kadro Ort.** | - | **13.6** | **4.9** | **2.9** | **0.82** | **0.57** | **1.4** | **1.4** | **48.8%** | **82.3%** |

### B. Model Kategori Kazanma Olasılıkları Çıktısı

| Kategori | Canlı Draft HUD Tahmini (Tur Kohortu) | 13 Gerçek Rakibe Karşı Simülasyon Ort. | Fark |
| :--- | :---: | :---: | :---: |
| **PTS** | 73.8% | 71.6% | -2.2% |
| **REB** | 71.4% | 71.8% | +0.4% |
| **AST** | 47.2% | 56.7% | +9.5% |
| **STL** | 58.8% | 60.1% | +1.3% |
| **BLK** | 69.0% | 66.1% | -2.9% |
| **FG3M** | 67.1% | 67.3% | +0.2% |
| **TOV** | 57.0% | 44.1% | -12.9% |
| **FG** | 68.1% | 57.3% | -10.8% |
| **FT** | 86.9% | 69.0% | -17.9% |

- **Ortalama Haftalık Beklenen Kategori Skoru:** 5.64 - 3.36
- **Haftalık Maç Kazanma Olasılığı P(Galibiyet >= 5):** %78.7

---

## 5. Modelin Lig Genel Sıralaması (Poisson-Binomial Round-Robin Power Rankings)

14 takımın her birinin ligdeki diğer 13 takımla yaptığı ikili Poisson-Binomial maç simülasyonları sonucunda elde edilen genel sıralama:

| Sıra | Slot # | Takım Adı | Haftalık Maç Kazanma Olasılığı | Beklenen Kategori Galibiyeti (9 Üzerinden) |
| :---: | :---: | :--- | :---: | :---: |
| 1 | #8 | Berk's Best Team | %78.7 | 5.64 |
| 2 | #13 | SILE BULLS | %64.2 | 5.03 |
| 3 | #4 | Houston Buckets | %61.3 | 4.93 |
| 4 | #2 | Mordor Tulums | %56.6 | 4.73 |
| 5 | #7 | Samurai Strikers | %56.2 | 4.73 |
| 6 | #10 | Redeem Team | %53.4 | 4.63 |
| 7 | #14 | YearOne Tyrants | %50.5 | 4.52 |
| 8 | #3 | Philadelphia Sikers | %47.2 | 4.39 |
| 9 | #5 | Kuvâ-yi Milfiye | %43.5 | 4.25 |
| 10 | #1 | MuCa Tandır | %43.4 | 4.25 |
| 11 | #11 | Fikirtepe Warriors | %39.1 | 4.09 |
| 12 | #12 | Istanbul Brickmakers | %38.9 | 4.08 |
| 13 | #9 | FatihTerimSpor | %34.9 | 3.93 |
| 14 | #6 | abu dhabi camels | %32.1 | 3.81 |

---

## 6. 13 Rakip Takımla Birebir Eşleşme Matrisi (Berk's Best Team vs. Rakipler)

| Slot | Rakip Takım | Beklenen Kategori Skoru | Maç Kazanma Olasılığı | PTS | REB | AST | STL | BLK | 3PM | TOV | FG% | FT% |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| #1 | MuCa Tandır | 5.77 - 3.23 | %82.4 | %80 | %83 | %59 | %53 | %81 | %66 | %32 | %52 | %71 |
| #2 | Mordor Tulums | 5.29 - 3.71 | %72.4 | %81 | %66 | %94 | %67 | %33 | %64 | %19 | %45 | %59 |
| #3 | Philadelphia Sikers | 5.67 - 3.33 | %79.5 | %61 | %73 | %48 | %65 | %74 | %52 | %58 | %66 | %69 |
| #4 | Houston Buckets | 5.17 - 3.83 | %67.8 | %56 | %84 | %47 | %56 | %60 | %64 | %42 | %54 | %55 |
| #5 | Kuvâ-yi Milfiye | 5.84 - 3.16 | %82.8 | %75 | %72 | %68 | %72 | %64 | %63 | %43 | %66 | %61 |
| #6 | abu dhabi camels | 6.13 - 2.87 | %88.8 | %77 | %79 | %50 | %64 | %76 | %83 | %45 | %58 | %82 |
| #7 | Samurai Strikers | 5.33 - 3.67 | %72.2 | %71 | %53 | %34 | %43 | %72 | %69 | %57 | %57 | %77 |
| #9 | FatihTerimSpor | 6.11 - 2.89 | %88.0 | %62 | %70 | %68 | %73 | %84 | %73 | %53 | %52 | %76 |
| #10 | Redeem Team | 5.41 - 3.59 | %74.4 | %76 | %68 | %40 | %49 | %62 | %74 | %39 | %51 | %83 |
| #11 | Fikirtepe Warriors | 6.00 - 3.00 | %86.3 | %77 | %64 | %79 | %69 | %66 | %72 | %40 | %68 | %66 |
| #12 | Istanbul Brickmakers | 5.95 - 3.05 | %85.5 | %78 | %76 | %75 | %72 | %64 | %76 | %41 | %47 | %67 |
| #13 | SILE BULLS | 5.09 - 3.91 | %65.8 | %63 | %70 | %34 | %44 | %60 | %54 | %54 | %69 | %61 |
| #14 | YearOne Tyrants | 5.57 - 3.43 | %77.5 | %75 | %76 | %42 | %54 | %64 | %65 | %52 | %60 | %70 |

---

## 7. Yahoo Fantasy Resmi Projeksiyon Verisi ve Karşılaştırma

| Projeksiyon Kaynağı | Berk's Best Team Sıralaması | Beklenen Maç Kazanma Olasılığı / Karakteri |
| :--- | :---: | :--- |
| **Yahoo Fantasy Resmi Draft Raporu (Predicted Order of Finish)** | **12. Sıra (14 Takım Arasında)** | Yahoo'nun resmi draft değerlendirmesinde ligin alt basamaklarında öngörülmüştür. |
| **Poisson-Binomial H2H Eşleşme Simülasyon Modeli** | **1. Sıra (14 Takım Arasında)** | Haftalık %78.7 kazanma olasılığı ve 5.64 beklenen kategori galibiyeti öngörülmüştür. |

### Diğer Ajanlar ve Bağımsız Denetçiler İçin Açık Sorular:
1. Aynı 182 seçim ve aynı 14 kadro verisi üzerinden; Yahoo Fantasy resmi projeksiyonunun takımı **12. sırada** göstermesi ile Poisson-Binomial eşleşme simülasyonunun takımı **1. sırada** göstermesi arasındaki temel metodolojik ve matematiksel zıtlıklar nelerdir?
2. 9 kategorili Head-to-Head (H2H) lig yapısında kadro inşası değerlendirilirken; sezonluk kümülatif toplam istatistik yaklaşımı ile haftalık ikili kategori kazanma olasılığı yaklaşımı arasında hangi farklar bulunmaktadır?
3. Bu kadro yapısının güçlü ve riskli yönleri bağımsız bir gözle incelendiğinde nasıl değerlendirilmelidir?
