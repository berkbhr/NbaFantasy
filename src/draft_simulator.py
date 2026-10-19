import pandas as pd
from src.season_data_manager import fetch_season_baseline
import numpy as np

def calculate_z_scores(df):
    """
    Calculates basic Z-scores for a baseline dataframe to rank players for the draft.
    """
    df = df[(df['GP'] >= 30) & (df['MIN'] >= 15.0)].copy()
    
    # Categories
    cats = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'FG3M', 'TOV']
    
    # FG and FT impact
    league_fg = df['FGM'].sum() / df['FGA'].sum()
    league_ft = df['FTM'].sum() / df['FTA'].sum()
    
    df['FG_Impact'] = df['FGA'] * (df['FG_PCT'] - league_fg)
    df['FT_Impact'] = df['FTA'] * (df['FT_PCT'] - league_ft)
    
    all_cats = cats + ['FG_Impact', 'FT_Impact']
    
    for cat in all_cats:
        mean = df[cat].mean()
        std = df[cat].std()
        df[f'Z_{cat}'] = (df[cat] - mean) / std if std > 0 else 0
        
        # Invert TOV
        if cat == 'TOV':
            df[f'Z_{cat}'] = -df[f'Z_{cat}']
            
    df['Total_Z'] = df[[f'Z_{cat}' for cat in all_cats]].sum(axis=1)
    return df.sort_values('Total_Z', ascending=False)

def simulate_draft(team_count=2, roster_size=13, baseline_season="2021-22"):
    """
    Simulates a snake draft based on the previous season's data.
    """
    print(f"Fetching {baseline_season} data for Draft ADP rankings...")
    df_prev = fetch_season_baseline(baseline_season)
    df_ranked = calculate_z_scores(df_prev)
    
    # Top players available
    available_players = df_ranked[['PLAYER_ID', 'PLAYER_NAME', 'Total_Z']].to_dict('records')
    
    teams = {i: [] for i in range(team_count)}
    
    # Snake draft
    direction = 1
    current_team = 0
    
    for round_num in range(roster_size):
        for _ in range(team_count):
            # Draft the best available player
            if available_players:
                player = available_players.pop(0)
                teams[current_team].append(player)
            
            # Move to next team
            current_team += direction
            
        # Reverse direction for snake draft
        direction *= -1
        current_team += direction
        
    return teams, available_players

if __name__ == "__main__":
    teams, undrafted = simulate_draft(2, 13)
    print("\n--- Team 0 (Model) ---")
    for p in teams[0]:
        print(f"{p['PLAYER_NAME']} (Z: {p['Total_Z']:.2f})")
        
    print("\n--- Team 1 (Naive Opponent) ---")
    for p in teams[1]:
        print(f"{p['PLAYER_NAME']} (Z: {p['Total_Z']:.2f})")
        
    print(f"\nUndrafted players (Waivers): {len(undrafted)}")
