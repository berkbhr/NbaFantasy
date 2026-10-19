import os
import time
import pandas as pd
from nba_api.stats.endpoints import commonplayerinfo

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
PROCESSED_DIR = os.path.join(DATA_DIR, 'processed')

def fetch_all_positions():
    print("Loading unique player IDs from all seasons...")
    raw_dir = os.path.join(DATA_DIR, 'raw')
    all_files = [f for f in os.listdir(raw_dir) if f.startswith('player_logs_') and f.endswith('.parquet')]
    
    unique_players_df = pd.DataFrame()
    for file in all_files:
        df = pd.read_parquet(os.path.join(raw_dir, file))
        unique_players_df = pd.concat([unique_players_df, df[['PLAYER_ID', 'PLAYER_NAME']]])
        
    unique_players = unique_players_df.drop_duplicates(subset=['PLAYER_ID']).reset_index(drop=True)
    
    results = []
    total = len(unique_players)
    print(f"Total unique players across all seasons: {total}")
    
    for i, (_, row) in enumerate(unique_players.iterrows()):
        pid = row['PLAYER_ID']
        name = row['PLAYER_NAME']
        
        try:
            info = commonplayerinfo.CommonPlayerInfo(player_id=pid)
            df_info = info.get_data_frames()[0]
            pos = df_info['POSITION'].iloc[0]
            results.append({'PLAYER_ID': pid, 'PLAYER_NAME': name, 'POSITION': pos})
        except Exception as e:
            print(f"Failed for {name}: {e}")
            
        time.sleep(0.6)
        if (i+1) % 50 == 0:
            print(f"Processed {i+1}/{total} players...")
            
    df_results = pd.DataFrame(results)
    out_path = os.path.join(PROCESSED_DIR, 'player_positions.parquet')
    df_results.to_parquet(out_path, index=False)
    print(f"Done! Saved {len(df_results)} positions to {out_path}")

if __name__ == "__main__":
    fetch_all_positions()
