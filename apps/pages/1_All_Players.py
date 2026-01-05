import streamlit as st

# Set page configuration with Bootstrap theme
st.set_page_config(
    page_title='Show All',
    layout='centered'
)

from calcs import *
from data import *
from utils import *
from plots import *

import numpy as np

# Use centralized data from session state
if 'full_df' not in st.session_state:
    st.error('Please upload a JSON file first')
    st.stop()

df = st.session_state['full_df']
league_settings = st.session_state['league_settings']


def select_teams(df):
    teams_to_choose_from = ['*All*'] + list(np.sort([x for x in df.team.unique() if x not in ['FA','Draft']])) + ['FA', 'Draft']
    num_columns = 4
    num_per_column = len(teams_to_choose_from) // num_columns + 1
    columns = st.columns(num_columns)
    selected_teams = []
    for i in range(num_columns):
        for team in teams_to_choose_from[i * num_per_column: (i + 1) * num_per_column]:
            if team == '*All*':
                selected = columns[i].checkbox(team, value=True)
            else:
                selected = columns[i].checkbox(team)
            if selected:
                selected_teams.append(team)
    return selected_teams


def filter_teams(df, selected_teams):
    if selected_teams != ['*All*']:
        return df[(df.team.isin(selected_teams))]
    else:
        return df[~df.team.isin(['Draft'])]


def display_and_select_pids(df):
    if 'selected_pids' not in st.session_state:
        st.session_state.selected_pids = []

    df_with_selections = df.copy()
    df_with_selections.insert(0, "Select", False)

    # Get dataframe row-selections from user with st.data_editor
    edited_df = st.data_editor(
        df_with_selections.style \
            .format(precision=0, subset=['pid', 'age', 'ovr', 'pot', 'years']) \
            .format(precision=2, subset=['v1', 'v2', 'value']) \
            .format("{:.1%}", subset=['cap_hit']) \
            .background_gradient(cmap='RdBu_r', vmin=26, vmax=80, subset=['ovr', 'pot']) \
            .background_gradient(cmap='RdBu_r', vmin=-df.value.max(), vmax=df.value.max(), subset=['v1']) \
            .background_gradient(cmap='RdBu_r', vmin=-df.value.max(), vmax=df.value.max(), subset=['v2']) \
            .background_gradient(cmap='RdBu_r', vmin=-df.value.max(), vmax=df.value.max(),
                                 subset=['value']) \
            .background_gradient(cmap='RdBu_r', vmin=-0.35, vmax=0.35, subset=['cap_hit']) \
            .background_gradient(cmap='RdBu', vmin=0, vmax=10, subset=['years']) \
        ,
        hide_index=True,
        column_config={"Select": st.column_config.CheckboxColumn(required=True)},
        disabled=df.columns,
        use_container_width=True
    )

    # Filter the dataframe using the temporary column, then drop the column
    selected_pids = list(set(edited_df[edited_df.Select]['pid'].to_list() + st.session_state.selected_pids))
    return selected_pids


## Markdown that shows my season and team
st.markdown(f"Season: {league_settings['season']}, My Team: {df[df.tid == league_settings['my_team_id']]['team'].values[0]}")

st.write('Data loaded and processed')

selected_teams = select_teams(df)
df_filtered = filter_teams(df, selected_teams)

# Create a button to clear the selected pids
if st.button('Clear selected players'):
    st.session_state['selected_pids'] = []

df_display = df_filtered[
    ['player', 'pid', 'team', 'pos', 'age', 'ovr', 'pot', 'years', 'cap_hit', 'value', 'v1', 'v2']].sort_values('value',
                                                                                                                ascending=False)

st.session_state['selected_pids'] = display_and_select_pids(df_display)

if len(st.session_state['selected_pids']) > 0:
    trade_df = df[df.pid.isin(st.session_state['selected_pids'])]
    pivot_table = trade_df.pivot_table(index='player', columns='team', values='value', aggfunc='sum', fill_value=0)
    # Sort rows to keep teams together
    pivot_table = pivot_table.sort_values(by=pivot_table.columns.tolist(), ascending=True)
    # Add a column to show the total value for each team
    pivot_table.loc['Total'] = pivot_table.sum()
    st.dataframe(pivot_table)

[st.plotly_chart(player_plot(pid, df), use_container_width=True) for pid in st.session_state['selected_pids']]