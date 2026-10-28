"""
1-Click Yahoo Fantasy Sports OAuth2 Authorization & Verification Script.

Reads credentials from config/yahoo_oauth.json, generates authorization URL,
exchanges verification code for permanent refresh_token, discovers league_key,
and verifies real-time roster ingestion.
"""

import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

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

    # If refresh_token already exists in config, try refreshing & discovering league automatically first
    if cfg.get("refresh_token"):
        sys.path.insert(0, PROJECT_ROOT)
        from src.yahoo_draft_sync import YahooFantasyOAuthClient

        client = YahooFantasyOAuthClient(config_path=CONFIG_PATH)
        if client.refresh_access_token():
            if client.discover_league_and_team(target_league_id="64691"):
                print("\n✅ Mevcut refresh_token ile baglanti dogrulandi!")
                print(f"  League Key: {client.league_key}")
                print(f"  Team Key:   {client.team_key}")
                print(f"🎉 '{CONFIG_PATH}' guncellendi!")
                return
            else:
                print(f"\n[DETAY] Mevcut token gecerli ancak lig kesfi hatasi: {client.last_error}")
                custom_lid = input(
                    "\nYahoo lig sayfanizin URL'sini veya Lig ID numaranizi girin (Yeni token almak icin 'yeni' yazin, cikmak icin Enter): "
                ).strip()
                if not custom_lid:
                    return
                if custom_lid.lower() != "yeni":
                    m_lid = re.search(r"(\d{3,8})", custom_lid)
                    if m_lid and client.discover_league_and_team(target_league_id=m_lid.group(1)):
                        print("\n✅ Lig basariyla bulundu!")
                        print(f"  League Key: {client.league_key}")
                        print(f"  Team Key:   {client.team_key}")
                        print(f"🎉 '{CONFIG_PATH}' guncellendi!")
                        return
                    print(f"[UYARI] Lig ({custom_lid}) yine erisilemedi: {client.last_error}")
                    return

    # 1. Generate Auth URL
    auth_url = AUTH_URL_TEMPLATE.format(
        client_id=urllib.parse.quote(client_id), redirect_uri=urllib.parse.quote(redirect_uri)
    )

    print("\nAdim 1: Asagidaki baglantiya tarayicinizda (Chrome/Edge) gidin:\n")
    print(auth_url)
    print("\nAdim 2: Yahoo hesabinizla giris yapip 'Agree / Izin Ver' butonuna tiklayin.")
    print("Adim 3: Tarayiciniz 'https://localhost:8080/?code=XXXXX' sayfasina yonlenecektir.")
    print(
        "        (Sayfa acilmasa bile onemli degil, adres cubugundaki linki veya 'code=' sonrasindaki degeri kopyalayin).\n"
    )

    user_input = input(
        "Tarayicinin adres cubugundaki URL'yi veya onay kodunu buraya yapistirin: "
    ).strip()
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

    post_data = urllib.parse.urlencode(
        {
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code": code,
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        TOKEN_URL,
        data=post_data,
        headers={
            "Authorization": f"Basic {b64_auth}",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0",
        },
        method="POST",
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
    save_config(cfg)

    # 3. Discover User's NBA Leagues via hardened YahooFantasyOAuthClient
    print("\n[BILGI] Yahoo Fantasy ligleriniz taranıyor...")
    sys.path.insert(0, PROJECT_ROOT)
    from src.yahoo_draft_sync import YahooFantasyOAuthClient

    client = YahooFantasyOAuthClient(config_path=CONFIG_PATH)
    if client.discover_league_and_team(target_league_id="64691"):
        print(f"  Bulunan Lig Key: {client.league_key}")
        print(f"  Takiminiz Key:   {client.team_key}")
    else:
        print(f"[UYARI] Otomatik lig tespiti yapilamadi ({client.last_error}).")

    print(f"\n🎉 Baglanti tamamlandi ve '{CONFIG_PATH}' dosyasina kalici olarak kaydedildi!")
    print("Artik sistem her calistiginda arka planda liginizi otomatik olarak senkronize edebilir.")


if __name__ == "__main__":
    main()
