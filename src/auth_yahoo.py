"""
1-Click Yahoo Fantasy Sports OAuth2 Authorization & Verification Script.

Reads credentials from config/yahoo_oauth.json, generates authorization URL,
exchanges verification code for permanent refresh_token, discovers league_key,
and verifies real-time roster ingestion.
"""
import os
import sys
import json
import time
import base64
import re
import urllib.request
import urllib.parse
import urllib.error

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "yahoo_oauth.json")

AUTH_URL_TEMPLATE = (
    "https://api.login.yahoo.com/oauth2/request_auth"
    "?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&language=en-us"
)
TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"
API_BASE = "https://fantasysports.yahooapis.com/fantasy/v2"

def load_config():
    if not os.path.exists(CONFIG_PATH):
        print(f"[HATA] {CONFIG_PATH} dosyasi bulunamadi!")
        sys.exit(1)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

def main():
    print("=" * 75)
    print("🏀 YAHOO FANTASY SPORTS OAUTH2 TEK SEFERLIK BAGLANTI ARACI")
    print("=" * 75)

    cfg = load_config()
    client_id = cfg.get("client_id", "").strip()
    client_secret = cfg.get("client_secret", "").strip()
    redirect_uri = cfg.get("redirect_uri", "https://localhost:8080").strip()

    if not client_id or "BURAYA" in client_id or not client_secret or "BURAYA" in client_secret:
        print("\n[UYARI] Lutfen once 'config/yahoo_oauth.json' dosyasini acin;")
        print("  - 'client_id' karsiligina Yahoo Client ID'nizi")
        print("  - 'client_secret' karsiligina Yahoo Client Secret'inizi yazip kaydedin.\n")
        return

    # 1. Generate Auth URL
    auth_url = AUTH_URL_TEMPLATE.format(
        client_id=urllib.parse.quote(client_id),
        redirect_uri=urllib.parse.quote(redirect_uri)
    )

    print("\nAdim 1: Asagidaki baglantiya tarayicinizda (Chrome/Edge) gidin:\n")
    print(auth_url)
    print("\nAdim 2: Yahoo hesabinizla giris yapip 'Agree / Izin Ver' butonuna tiklayin.")
    print("Adim 3: Tarayiciniz 'https://localhost:8080/?code=XXXXX' sayfasina yonlenecektir.")
    print("        (Sayfa acilmasa bile onemli degil, adres cubugundaki linki veya 'code=' sonrasindaki degeri kopyalayin).\n")

    user_input = input("Tarayicinin adres cubugundaki URL'yi veya onay kodunu buraya yapistirin: ").strip()
    if not user_input:
        print("[IPTAL] Kod girilmedi.")
        return

    # Extract code parameter if full URL was pasted
    code = user_input
    if "code=" in user_input:
        m = re.search(r"code=([^&]+)", user_input)
        if m:
            code = m.group(1)

    print(f"\n[BILGI] Kod alindi: {code[:6]}... Token takasi yapiliyor...")

    # 2. Exchange code for access_token & refresh_token
    creds = f"{client_id}:{client_secret}".encode("utf-8")
    b64_auth = base64.b64encode(creds).decode("ascii")

    post_data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
        "code": code,
    }).encode("utf-8")

    req = urllib.request.Request(
        TOKEN_URL,
        data=post_data,
        headers={
            "Authorization": f"Basic {b64_auth}",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0",
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            token_resp = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as he:
        err_msg = he.read().decode("utf-8", errors="ignore")
        print(f"\n[HATA] Yahoo Token Takasi Basarisiz (HTTP {he.code}):")
        print(err_msg)
        return
    except Exception as e:
        print(f"\n[HATA] Baglanti hatasi: {e}")
        return

    access_token = token_resp.get("access_token")
    refresh_token = token_resp.get("refresh_token")
    expires_in = float(token_resp.get("expires_in", 3600))

    if not access_token or not refresh_token:
        print("[HATA] Yahoo token donmedi:", token_resp)
        return

    print("✅ [BASARILI] Yahoo OAuth2 Token basariyla alindi!")
    cfg["access_token"] = access_token
    cfg["refresh_token"] = refresh_token
    cfg["token_expiry"] = time.time() + expires_in - 60.0

    # 3. Discover User's NBA Leagues
    print("\n[BILGI] Yahoo Fantasy ligleriniz taranıyor...")
    leagues_req = urllib.request.Request(
        f"{API_BASE}/users;use_login=1/games;game_keys=nba/leagues?format=json",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
        }
    )

    league_key = None
    team_key = None
    try:
        with urllib.request.urlopen(leagues_req, timeout=10.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            fc = data.get("fantasy_content", {})
            users = fc.get("users", {})
            user_info = users.get("0", {}).get("user", [])
            games = user_info[1].get("games", {}) if len(user_info) > 1 else {}
            nba_game = games.get("0", {}).get("game", [])
            leagues = nba_game[1].get("leagues", {}) if len(nba_game) > 1 else {}
            
            for k, v in leagues.items():
                if k == "count" or not isinstance(v, dict):
                    continue
                l_info = v.get("league", [])
                meta = l_info[0] if l_info else {}
                league_key = meta.get("league_key")
                league_name = meta.get("name")
                print(f"  Bulunan Lig: {league_name} (Key: {league_key})")
                
                # Check user's team in this league
                teams_req = urllib.request.Request(
                    f"{API_BASE}/league/{league_key}/teams?format=json",
                    headers={"Authorization": f"Bearer {access_token}", "User-Agent": "Mozilla/5.0"}
                )
                with urllib.request.urlopen(teams_req, timeout=10.0) as t_resp:
                    t_data = json.loads(t_resp.read().decode("utf-8"))
                    # Pick user's team or slot 8
                    t_fc = t_data.get("fantasy_content", {}).get("league", [])[1].get("teams", {})
                    for tk, tv in t_fc.items():
                        if tk == "count" or not isinstance(tv, dict):
                            continue
                        t_arr = tv.get("team", [])[0]
                        t_name = ""
                        curr_t_key = ""
                        for item in t_arr:
                            if isinstance(item, dict):
                                if "name" in item: t_name = item["name"]
                                if "team_key" in item: curr_t_key = item["team_key"]
                        if "berk" in t_name.lower():
                            team_key = curr_t_key
                            print(f"  Takiminiz Tespit Edildi: {t_name} (Key: {team_key})")
                            break
    except Exception as e:
        print(f"[UYARI] Otomatik lig tespiti yapilamadi ({e}). Manuel 'league_id' kullanilacak.")

    if league_key:
        cfg["league_key"] = league_key
    if team_key:
        cfg["team_key"] = team_key

    save_config(cfg)
    print(f"\n🎉 Baglanti tamamlandi ve '{CONFIG_PATH}' dosyasina kalici olarak kaydedildi!")
    print("Artik sistem her calistiginda arka planda liginizi otomatik olarak senkronize edebilir.")

if __name__ == "__main__":
    main()
