import pandas as pd
import numpy as np

def calculate_season_z_scores(df_logs):
    """
    Calculates season averages and Z-scores from game logs.
    """
    if df_logs.empty:
        return pd.DataFrame()
        
    # Aggregate to per-game
    agg_funcs = {
        'PTS': 'mean', 'REB': 'mean', 'AST': 'mean', 
        'STL': 'mean', 'BLK': 'mean', 'FG3M': 'mean', 'TOV': 'mean',
        'FGM': 'sum', 'FGA': 'sum', 'FTM': 'sum', 'FTA': 'sum',
        'MIN': 'sum'
    }
    
    # Calculate GP (Games Played)
    gp = df_logs.groupby('PLAYER_ID').size().rename('GP')
    df_avg = df_logs.groupby('PLAYER_ID').agg(agg_funcs)
    df_avg = df_avg.join(gp)
    
    # Needs at least 3 games to be considered for waivers
    df_avg = df_avg[df_avg['GP'] >= 3].copy()
    
    # Calculate Impact stats
    league_fg = df_avg['FGM'].sum() / df_avg['FGA'].sum() if df_avg['FGA'].sum() > 0 else 0
    league_ft = df_avg['FTM'].sum() / df_avg['FTA'].sum() if df_avg['FTA'].sum() > 0 else 0
    
    df_avg['FG_PCT'] = df_avg['FGM'] / df_avg['FGA']
    df_avg['FT_PCT'] = df_avg['FTM'] / df_avg['FTA']
    
    # FGA/GP is needed for Impact per game
    df_avg['FGA_PG'] = df_avg['FGA'] / df_avg['GP']
    df_avg['FTA_PG'] = df_avg['FTA'] / df_avg['GP']
    
    df_avg['FG_Impact'] = df_avg['FGA_PG'] * (df_avg['FG_PCT'] - league_fg)
    df_avg['FT_Impact'] = df_avg['FTA_PG'] * (df_avg['FT_PCT'] - league_ft)
    
    # Z-Scores
    cats = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'FG3M', 'TOV', 'FG_Impact', 'FT_Impact']
    for cat in cats:
        mean = df_avg[cat].mean()
        std = df_avg[cat].std()
        df_avg[f'Z_{cat}'] = (df_avg[cat] - mean) / std if std > 0 else 0
        if cat == 'TOV':
            df_avg[f'Z_{cat}'] = -df_avg[f'Z_{cat}']
            
    df_avg['Total_Z'] = df_avg[[f'Z_{cat}' for cat in cats]].sum(axis=1)
    return df_avg

def get_naive_waiver_moves(team_roster_ids, waiver_pool_ids, df_logs, max_moves=3):
    """
    Naive AI: Drops worst player for best available based purely on Total_Z.
    Returns: list of (drop_id, add_id, drop_z, add_z) tuples.
    """
    df_z = calculate_season_z_scores(df_logs)
    if df_z.empty:
        return []
        
    # Get stats for current team and waivers
    team_stats = df_z[df_z.index.isin(team_roster_ids)].copy()
    waiver_stats = df_z[df_z.index.isin(waiver_pool_ids)].copy()
    
    # If a player has no stats yet, assign -99
    for pid in team_roster_ids:
        if pid not in team_stats.index:
            team_stats.loc[pid, 'Total_Z'] = -99
            
    team_stats = team_stats.sort_values('Total_Z', ascending=True)
    waiver_stats = waiver_stats.sort_values('Total_Z', ascending=False)
    
    moves = []
    
    for i in range(min(max_moves, len(team_stats), len(waiver_stats))):
        worst_team_player_id = team_stats.index[i]
        worst_z = team_stats.iloc[i]['Total_Z']
        
        best_waiver_player_id = waiver_stats.index[i]
        best_z = waiver_stats.iloc[i]['Total_Z']
        
        # Only make the move if the waiver player is significantly better
        if best_z > worst_z + 0.5:
            moves.append((worst_team_player_id, best_waiver_player_id, worst_z, best_z))
            
    return moves
