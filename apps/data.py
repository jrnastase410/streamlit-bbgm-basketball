import pandas as pd
import json
import streamlit as st


def load_json(json_file):
    r_json = json.load(json_file)
    return r_json


@st.cache_data(show_spinner=False)
def get_league_settings(r_json):
    league_settings = {
        'season': r_json['gameAttributes']['season'],
        'salary_cap': r_json['gameAttributes']['salaryCap'],
        'max_contract': r_json['gameAttributes']['maxContract'] / r_json['gameAttributes']['salaryCap'],
        'my_team_id': r_json['gameAttributes']['userTid'][-1]['value']
    }
    return league_settings


def create_df_from_player_data(players, key, additional_fields=None):
    data = []
    for player in players:
        for item in player[key]:
            row = {'pid': player['pid']}
            if key == 'ratings':
                row['current_tid'] = player['tid']
            if additional_fields:
                row.update({field: player[field] for field in additional_fields})
            row.update(item)
            data.append(row)
    return pd.DataFrame(data).convert_dtypes(dtype_backend='pyarrow')


def player_json_to_df(r_json, keep=['ratings', 'salaries', 'stats']):
    players = r_json['players']

    if 'ratings' in keep:
        ratings_df = create_df_from_player_data(players, 'ratings', ['firstName', 'lastName', 'born'])
        ratings_df['age'] = ratings_df['season'] - ratings_df['born'].apply(lambda x: x['year'])
        ratings_df = ratings_df.drop('born', axis=1).reset_index(drop=True)

    if 'stats' in keep:
        stats_df = create_df_from_player_data(players, 'stats')
        stats_df = stats_df[(stats_df.playoffs == False)].reset_index(drop=True)

    if 'salaries' in keep:
        salaries_df = create_df_from_player_data(players, 'salaries')
        salaries_df = salaries_df.reset_index(drop=True).rename(columns={'amount': 'salary'})

        def calculate_future_salaries(row):
            pid = row['pid']
            season = row['season']
            future_years = {}
            future_rows = salaries_df[(salaries_df['pid'] == pid) & (salaries_df['season'] >= season)]
            for i, (_, future_row) in enumerate(future_rows.iterrows()):
                future_years[i] = future_row['salary']
            return future_years

        # Vectorized apply using list comprehension for better performance
        salaries_df['salaries'] = [
            calculate_future_salaries(row)
            for _, row in salaries_df.iterrows()
        ]

    if 'stats' in keep and 'salaries' in keep:
        df = ratings_df.merge(
            stats_df[
                ['pid', 'season', 'tid', 'gp', 'gs', 'min', 'usgp', 'ortg', 'drtg', 'obpm', 'dbpm', 'ows', 'dws',
                 'vorp',
                 'ewa']],
            on=['pid', 'season'], how='left').merge(
            salaries_df[['pid', 'season', 'salary', 'salaries']], on=['pid', 'season'], how='left')

        return df

    if 'stats' in keep:
        return ratings_df.merge(
            stats_df[
                ['pid', 'season', 'tid', 'gp', 'gs', 'min', 'usgp', 'ortg', 'drtg', 'obpm', 'dbpm', 'ows', 'dws',
                 'vorp',
                 'ewa']],
            on=['pid', 'season'], how='left')

    if 'salaries' in keep:
        return ratings_df.merge(
            salaries_df[['pid', 'season', 'salary', 'salaries']], on=['pid', 'season'], how='left')

    return ratings_df

def cleanup_df(df, league_settings, r_json):
    df = df[df.season == league_settings['season']].drop_duplicates(['pid', 'season'], keep='last').reset_index(
        drop=True)
    df['tid'] = df['current_tid'].copy()
    df = df.drop(columns=['current_tid'], axis=1)
    team_dict = dict([(teams['tid'], teams['abbrev']) for teams in r_json['teams']])
    team_dict[-2] = 'Draft'
    team_dict[-1] = 'FA'
    df['team'] = df['tid'].map(team_dict)
    # Convert to categorical for better performance
    df['team'] = df['team'].astype('category')
    df['pos'] = df['pos'].astype('category')

    df['player'] = df['firstName'] + ' ' + df['lastName']
    df['cap_hit'] = df['salary'].fillna(0) / league_settings['salary_cap']
    df['years'] = df['salaries'].apply(lambda x: len(x) if isinstance(x, dict) else 0)

    return df

def filter_df(df, filter_column, filter_values):
    if filter_values:
        return df[df[filter_column].isin(filter_values)]
    else:
        return df