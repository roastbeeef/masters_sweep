import streamlit as st
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
from itertools import product
import time

# Constants
URL = 'https://www.espn.co.uk/golf/leaderboard'
REFRESH_INTERVAL = 300  # seconds

# Scoring rules
points = [30, 25, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 0]
position_points = {k + 1: v for k, v in enumerate(points)}

# Player groups
players_by_group = {
    "Jon Rahm": 1, "Collin Morikawa": 1, "Xander Schauffele": 1, "Ludvig Åberg": 1,
    "Bryson DeChambeau": 1, "Rory McIlroy": 1, "Scottie Scheffler": 1,
    "Joaquín Niemann": 2, "Brooks Koepka": 2, "Viktor Hovland": 2, "Patrick Cantlay": 2,
    "Hideki Matsuyama": 2, "Justin Thomas": 2, "Jordan Spieth": 2,
    "Shane Lowry": 3, "Tommy Fleetwood": 3, "Will Zalatoris": 3, "Robert MacIntyre": 3,
    "Cameron Smith": 3, "Tyrrell Hatton": 3, "Russell Henley": 3,
    "Akshay Bhatia": 4, "Min Woo Lee": 4, "Corey Conners": 4, "Jason Day": 4,
    "Tony Finau": 4, "Sepp Straka": 4, "Wyndham Clark": 4,
    "Cameron Young": 5, "Sungjae Im": 5, "Patrick Reed": 5, "Tom Kim": 5,
    "Sahith Theegala": 5, "Maverick McNealy": 5, "Sam Burns": 5,
    "Adam Scott": 6, "Keegan Bradley": 6, "Dustin Johnson": 6, "Matt Fitzpatrick": 6,
    "Justin Rose": 6, "Phil Mickelson": 6, "Max Homa": 6
}

@st.cache_data(ttl=REFRESH_INTERVAL)
def fetch_leaderboard():
    # Get the page
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(URL, headers=headers)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table')

    # Extract headers and rows
    headers = [th.get_text(strip=True) for th in table.find_all('th')]
    rows = [
        [td.get_text(strip=True) for td in tr.find_all('td')]
        for tr in table.find_all('tr')[1:]
        if tr.find_all('td')
    ]

    leaderboard = pd.DataFrame(rows, columns=headers)
    leaderboard = leaderboard[['POS', 'PLAYER', 'SCORE']]
    leaderboard['POS'] = leaderboard['POS'].str.extract('(\d+)', expand=False)
    leaderboard['POS'] = leaderboard['POS'].fillna(0).astype(int)

    return leaderboard

def build_player_dataframe():
    df = pd.DataFrame.from_dict(players_by_group, orient='index', columns=['group']).reset_index()
    df.columns = ['name', 'group']
    return df

def merge_data():
    leaderboard = fetch_leaderboard()
    players_df = build_player_dataframe()

    merged = players_df.merge(leaderboard, how='inner', left_on='name', right_on='PLAYER')
    points_df = pd.DataFrame(position_points.items(), columns=['POS', 'PTS'])

    merged = merged.merge(points_df, how='left', on='POS')
    merged['PTS_ADJ'] = np.where(merged['SCORE'] == 'CUT', -5, merged['PTS'])
    merged['PTS_ADJ'] = merged['PTS_ADJ'].fillna(0).astype(int)

    return merged

def generate_top_combos(df):
    grouped = {group: group_df for group, group_df in df.groupby('group')}
    assert len(grouped) == 6, "Must have exactly 6 groups."

    all_combos = list(product(*(grouped[g].to_dict('records') for g in sorted(grouped))))
    combo_rows = []

    for combo in all_combos:
        row = {f'GROUP_{i+1}_PICK': player['PLAYER'] for i, player in enumerate(combo)}
        row['TOTAL_PTS_ADJ'] = sum(player['PTS_ADJ'] for player in combo)
        combo_rows.append(row)

    combo_df = pd.DataFrame(combo_rows)
    top_10 = combo_df.sort_values(by='TOTAL_PTS_ADJ', ascending=False).head(10).reset_index(drop=True)
    return top_10

# Streamlit UI
st.set_page_config(layout="wide")
st.title("🏌️‍♂️ Masters Fantasy Top 10 Combos")
st.caption("Auto-refreshes every 5 minutes.")

with st.spinner("Fetching latest leaderboard..."):
    leaderboard_df = merge_data()
    top_10_df = generate_top_combos(leaderboard_df)

st.subheader("🔝 Top 10 Combos (1 player per group)")
st.dataframe(top_10_df, use_container_width=True)

# Optional: Show last updated time
st.markdown(f"⏱️ Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}")

