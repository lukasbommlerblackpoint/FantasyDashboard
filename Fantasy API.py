import requests
import pandas as pd
import matplotlib.pyplot as plt

headers = {
	"x-rapidapi-key": "b5f9043febmsh34ee669c0ca74e3p143c33jsne48ea19c3a67",
	"x-rapidapi-host": "tank01-nfl-live-in-game-real-time-statistics-nfl.p.rapidapi.com"
}


# projections
url = "https://tank01-nfl-live-in-game-real-time-statistics-nfl.p.rapidapi.com/getNFLProjections"
all_weeks = []  # list to store weekly DataFrames

for week in range(1, 9):
    querystring = {
        "week": str(week),
        "archiveSeason": "2025",
        "itemFormat": "list"
    }

    response = requests.get(url, headers=headers, params=querystring)
    data = response.json()

    # Defensive check to avoid breaking on missing data
    if 'body' not in data or 'playerProjections' not in data['body']:
        print(f"⚠️ No data for week {week}")
        continue

    # Create DataFrame for this week
    df_projected = pd.DataFrame(data['body']['playerProjections'])
    df_projected = df_projected[['playerID', 'longName', 'pos', 'team', 'fantasyPointsDefault']].copy()

    # Extract PPR projected points
    df_projected['projected_points'] = df_projected['fantasyPointsDefault'].apply(lambda x: x.get('PPR', 0))
    df_projected.drop(columns=['fantasyPointsDefault'], inplace=True)
    df_projected['week'] = week  # use loop variable for clarity

    all_weeks.append(df_projected)

# Combine all weeks into one DataFrame
df_player = pd.concat(all_weeks, ignore_index=True)
df_player.rename(columns={'longName': 'Name','pos': 'Position','team': 'Team'}, inplace=True)

# make sure there is an entry for each week
weeks = pd.DataFrame({'week': range(1, 9)})
unique_players = df_player[['playerID', 'Name', 'Position', 'Team']].drop_duplicates()
full_df = unique_players.merge(weeks, how='cross')
df_full = full_df.merge(df_player[['playerID', 'week', 'projected_points']], on=['playerID', 'week'], how='left')
df_full['projected_points'] = df_full['projected_points'].fillna(0)
df_full = df_full.sort_values(['playerID', 'week']).reset_index(drop=True)

# points by player
season_start = pd.Timestamp('2025-09-03')
all_players = []
player_ids = df_full.playerID.unique()
url = "https://tank01-nfl-live-in-game-real-time-statistics-nfl.p.rapidapi.com/getNFLGamesForPlayer"
for pid in player_ids:
    querystring = {
        "playerID": str(pid),
        "itemFormat": "list",
        "fantasyPoints": "true"
    }
    response = requests.get(url, headers=headers, params=querystring)
    data = response.json()

    # Defensive check in case data is missing or malformed
    if 'body' not in data or not data['body']:
        print(f"⚠️ No data for playerID {pid}")
        continue

    # Build player DataFrame
    df = pd.DataFrame(data['body'])[['playerID', 'gameID', 'fantasyPointsDefault']].copy()
    df['scored_points'] = df['fantasyPointsDefault'].apply(lambda x: x.get('PPR', 0) if isinstance(x, dict) else 0)
    df.drop(columns=['fantasyPointsDefault'], inplace=True)

    # Extract and convert dates
    df['date_str'] = df['gameID'].str[:8]
    df['game_date'] = pd.to_datetime(df['date_str'], format='%Y%m%d', errors='coerce')

    # Filter and assign week
    df = df[df['game_date'] > season_start].copy()
    df['week'] = ((df['game_date'] - season_start).dt.days // 7) + 1

    # Clean up
    df.drop(columns=['date_str', 'gameID', 'game_date'], inplace=True)

    all_players.append(df)

# Combine all players into one DataFrame
df_all_scored = pd.concat(all_players, ignore_index=True)

# ADP
url = "https://tank01-nfl-live-in-game-real-time-statistics-nfl.p.rapidapi.com/getNFLADP"
querystring = {"adpType":"PPR"}
response = requests.get(url, headers=headers, params=querystring)
data = response.json()
df_adp = pd.DataFrame(data['body']['adpList'])
df_adp = df_adp[['playerID', 'overallADP']]

# add ADP to dataframe
df_final = pd.merge(df_full, df_adp, how='left', on='playerID')
df_final = pd.merge(df_final, df_all_scored, how='left', on=['playerID', 'week'], ).fillna(0)

numeric_cols = ['projected_points', 'scored_points', 'overallADP']
df_final[numeric_cols] = df_final[numeric_cols].apply(pd.to_numeric, errors='coerce')
df_final.to_excel('df_players.xlsx')


# get teams
url = "https://tank01-nfl-live-in-game-real-time-statistics-nfl.p.rapidapi.com/getNFLTeams"
querystring = {"sortBy":"standings","rosters":"false","schedules":"false","topPerformers":"false","teamStats":"true","teamStatsSeason":"2025"}
response = requests.get(url, headers=headers, params=querystring)
data = response.json()['body']
rows = []
for team in data:
    team_stats = team.get('teamStats', {})
    rushing = team_stats.get('Rushing', {})
    receiving = team_stats.get('Receiving', {})
    row = {
        'teamID': team.get('teamID'),
        'teamAbv': team.get('teamAbv'),
        'wins': team.get('wins'),
        'rushYds': rushing.get('rushYds'),
        'rushTD': rushing.get('rushTD'),
        'carries': rushing.get('carries'),
        'receptions': receiving.get('receptions'),
        'recTD': receiving.get('recTD'),
        'targets': receiving.get('targets'),
        'recYds': receiving.get('recYds')
    }
    rows.append(row)
df_teams = pd.DataFrame(rows)
numeric_cols = ['wins', 'rushYds', 'rushTD', 'carries', 'receptions', 'recTD', 'targets', 'recYds']
df_teams[numeric_cols] = df_teams[numeric_cols].apply(pd.to_numeric, errors='coerce')
df_teams.to_excel('df_teams.xlsx')
