import os
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DIR = os.path.join(PROJECT_ROOT, 'data', 'processed')

def merge_positions_to_excel():
    pos_file = os.path.join(PROCESSED_DIR, 'player_positions.parquet')
    if not os.path.exists(pos_file):
        print("Positions file not found!")
        return

    df_pos = pd.read_parquet(pos_file)
    
    # Seasons we currently have
    seasons = ["2022_23", "2023_24", "2024_25", "2025_26"]
    
    for season in seasons:
        excel_path = os.path.join(PROCESSED_DIR, f'Master_Database_{season}.xlsx')
        if not os.path.exists(excel_path):
            continue
            
        print(f"Updating {excel_path}...")
        
        # We need to read all sheets
        try:
            xls = pd.ExcelFile(excel_path)
            sheets = {sheet_name: xls.parse(sheet_name) for sheet_name in xls.sheet_names}
        except Exception as e:
            print(f"Failed to read {excel_path}: {e}")
            continue
            
        # Update Player_Stats sheet
        if 'Player_Stats' in sheets:
            df_players = sheets['Player_Stats']
            if 'POSITION' in df_players.columns:
                df_players.drop(columns=['POSITION'], inplace=True)
                
            # Merge
            df_players = pd.merge(df_players, df_pos[['PLAYER_ID', 'POSITION']], on='PLAYER_ID', how='left')
            
            # Reorder to put POSITION near the name
            cols = list(df_players.columns)
            cols.insert(cols.index('PLAYER_NAME') + 1, cols.pop(cols.index('POSITION')))
            sheets['Player_Stats'] = df_players[cols]
            
        # Write back to excel
        with pd.ExcelWriter(excel_path, engine='xlsxwriter') as writer:
            for sheet_name, df in sheets.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                worksheet = writer.sheets[sheet_name]
                worksheet.add_table(0, 0, len(df), len(df.columns)-1, 
                                    {'columns': [{'header': str(c)} for c in df.columns]})
                
        print(f"Successfully updated {season} Excel file.")

if __name__ == "__main__":
    merge_positions_to_excel()
