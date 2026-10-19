import os
import sys
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'src'))

from live_draft_assistant import LiveDraftAssistant


def verify_player_name_resolution():
    print("=" * 65)
    print("  YAHOO OYUNCU İSİMLERİ & EXACT-SYNC DOĞRULAMA TESTİ")
    print("=" * 65)

    assistant = LiveDraftAssistant(prior_season="2025_26")
    df_base = assistant.df_base

    # Test common tricky Yahoo/NBA name variations
    test_cases = [
        ("Nikola Jokić", "Nikola Jokic"),
        ("Victor Wembanyama", "Victor Wembanyama"),
        ("Luka Dončić", "Luka Doncic"),
        ("Shai Gilgeous-Alexander", "Shai Gilgeous Alexander"),
        ("Karl-Anthony Towns", "Karl Anthony Towns"),
        ("P.J. Washington", "PJ Washington"),
        ("OG Anunoby", "O.G. Anunoby"),
        ("Trey Murphy III", "Trey Murphy"),
        ("Jabari Smith Jr.", "Jabari Smith"),
        ("Robert Williams III", "Robert Williams"),
        ("Wendell Carter Jr.", "Wendell Carter"),
        ("Kelly Oubre Jr.", "Kelly Oubre"),
        ("Gary Trent Jr.", "Gary Trent"),
        ("Derrick Jones Jr.", "Derrick Jones"),
        ("Kenyon Martin Jr.", "KJ Martin"),
        ("Alperen Şengün", "Alperen Sengun"),
        ("Jonas Valančiūnas", "Jonas Valanciunas"),
        ("Bogdan Bogdanović", "Bogdan Bogdanovic"),
        ("Bojan Bogdanović", "Bojan Bogdanovic"),
        ("Dennis Schröder", "Dennis Schroder"),
        ("Nikola Vučević", "Nikola Vucevic"),
        ("Jusuf Nurkić", "Jusuf Nurkic"),
        ("Chet Holmgren", "Chet Holmgren"),
        ("VJ Edgecombe", "V.J. Edgecombe"),
    ]

    print(f"\n1. Kritik Oyuncu İsim Varyasyonları Testi ({len(test_cases)} Test Vakası):")
    passed = 0
    for official_name, yahoo_variant in test_cases:
        pid_sync = assistant._resolve_exact_for_sync(yahoo_variant)
        pid_fuzzy = assistant.resolve_player_id(yahoo_variant, only_available=False)
        matched_id = pid_sync or pid_fuzzy
        matched_name = assistant.players[matched_id].name if matched_id in assistant.players else "BULUNAMADI"

        status = "✅" if matched_id is not None else "❌"
        if matched_id is not None:
            passed += 1
        print(f"  {status} Yahoo: '{yahoo_variant:26s}' -> Eşleşen: {matched_name} (ID: {matched_id})")

    print(f"\nÖzet: {passed}/{len(test_cases)} isim başarıyla çözüldü.")

    # 2. Check for ambiguous names (duplicate cleaned names in the base pool)
    if hasattr(assistant, '_exact_name_index'):
        ambig = {k: v for k, v in assistant._exact_name_index.items() if len(v) > 1}
        print(f"\n2. Havuzdaki Çift/Belirsiz İsimler ({len(ambig)} Adet):")
        for k, pids in ambig.items():
            names = [f"{assistant.players[p].name} ({assistant.team_abbr_dict.get(p, 'NBA')})" for p in pids if p in assistant.players]
            print(f"  ⚠️ '{k}': {', '.join(names)}")


if __name__ == "__main__":
    verify_player_name_resolution()
