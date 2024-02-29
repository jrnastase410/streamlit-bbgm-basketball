import streamlit as st
import pandas as pd
import numpy as np
import json

# Set page configuration with Bootstrap theme
st.set_page_config(
    page_title='Draft Guide',
    layout='centered'
)

from calcs import *
from data import *

def load_and_process_draft_data(json_file):
    r_json = json.load(json_file)
    league_settings = {
        'season': r_json['gameAttributes']['season'],
        'salary_cap': r_json['gameAttributes']['salaryCap'],
        'max_contract': r_json['gameAttributes']['maxContract'] / r_json['gameAttributes']['salaryCap'],
        'my_team_id': r_json['gameAttributes']['userTid'][-1]['value']
    }
    df = player_json_to_df(r_json, keep=['ratings'])

    def cleanup_df(df):
        df = df[(df.season == league_settings['season']) & (df.current_tid == -2)].drop_duplicates(['pid', 'season'], keep='last').reset_index(
            drop=True)
        df['team'] = 'Draft'
        df['player'] = df['firstName'] + ' ' + df['lastName']
        return df

    return cleanup_df(df), league_settings

if st.button('Clear JSON'):
    st.session_state['df_import'] = None

if st.session_state['df_import'] is None:
    json_file = st.file_uploader('Upload a JSON file', type='json')
    if not json_file:
        st.stop()
    df_import, league_settings = load_and_process_draft_data(json_file)
    st.session_state['df_import'] = df_import
    st.session_state['league_settings'] = league_settings

# Load data from session state
df = st.session_state['df_import'].copy()
league_settings = st.session_state['league_settings']

# Perform calculations
df['vorp'] = df['ovr'].apply(ovr_to_vorp)
df['results'] = df.apply(lambda x: calc_progs(x['ovr'], x['age'], 0.75), axis=1)
df[['rating_prog', 'rating_upper_prog', 'rating_lower_prog', 'cap_value_prog']] = pd.DataFrame(df['results'].tolist(),
                                                                                               index=df.index)
df['pot'] = df['rating_upper_prog'].apply(lambda x: max(x.values())).astype(int)
df['cap_value'] = df['cap_value_prog'].apply(lambda x: sum(x.values()))
df['value'] = df['cap_value'].round(2)
df['rk'] = df['value'].rank(ascending=False, method='dense').astype(int)

df['info'] = df['rk'].astype(str) + ' / ' + df['player'] + ' / ' + df['pos'] + ' / ' + df['age'].astype(str)
df['ratings'] = df['ovr'].astype(str) + ' / ' + df['pot'].astype(str)
df = df[['info', 'ratings', 'value']].sort_values('value', ascending=False)

# Add a checkbox column for drafted players
df.insert(0, "Drafted", False)


# Get dataframe row-selections from user with st.data_editor
edited_df = st.data_editor(
    df.style \
        .background_gradient(cmap='viridis', vmin=0, vmax=df[df.Drafted == False]['value'].max(), subset=['value']) \
        .format(precision=2, subset=['value']),
    hide_index=True,
    column_config={"Drafted": st.column_config.CheckboxColumn(required=True)},
    disabled=['value', 'ovr', 'pot'],
    use_container_width=True
)

# Filter the dataframe based on the checkbox column
drafted_df = edited_df[edited_df.Drafted]

# Display the dataframes
st.header("Drafted Players")
st.dataframe(drafted_df, use_container_width=True)