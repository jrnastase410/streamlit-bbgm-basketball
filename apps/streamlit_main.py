import streamlit as st

st.set_page_config(
    page_title='Home',
    layout='wide'
)

import os

print(os.getcwd())

from calcs import *
from data import *
from plots import *
import logging
import json

# Set up logging to write to the console
logging.basicConfig(level=logging.INFO, format='%(message)s')

# Example function that writes to the console
def write_to_console(text):
    logging.info(text)


@st.cache_data(ttl=60 * 60 * 24 * 3, max_entries=3, show_spinner=True)
def load_and_process_data(json_file, keep=['ratings', 'salaries'], ci_q=0.75, inflation_factor=1.0275,
                          scale_factor=0.9):
    r_json = load_json(json_file)
    league_settings = get_league_settings(r_json)
    df = player_json_to_df(r_json, keep=keep)
    df = cleanup_df(df, league_settings, r_json)
    df = calculate_progs(df, ci_q)
    df = calculate_potential(df)
    df = calculate_salary_projections(df, league_settings, inflation_factor)
    df = calculate_cap_hits(df)
    df = predict_cap_hits(df)
    df['cap_hits_filled'] = df.apply(lambda row: fill_cap_hits(row['cap_hits'], row['cap_hits_prog'], inflation_factor),
                                     axis=1)
    df = calculate_surplus(df)
    df = scale_surplus(df, scale_factor)
    df = sum_values(df)

    columns_to_keep = ['pid', 'player', 'season', 'ovr', 'pot', 'age', 'pos', 'salary', 'salaries', 'tid', 'team',
                       'rating_prog',
                       'rating_upper_prog', 'rating_lower_prog', 'cap_value_prog',
                       'rating_upper', 'salary_caps', 'cap_hits', 'cap_hits_prog',
                       'cap_hits_filled', 'surplus_1_progs', 'surplus_2_progs', 'v1', 'v2',
                       'value', 'cap_hit', 'years']

    return_df = df[~df.team.isna()][columns_to_keep].reset_index()
    return return_df, league_settings


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
            .background_gradient(cmap='RdBu_r', vmin=-df_import.value.max(), vmax=df_import.value.max(), subset=['v1']) \
            .background_gradient(cmap='RdBu_r', vmin=-df_import.value.max(), vmax=df_import.value.max(), subset=['v2']) \
            .background_gradient(cmap='RdBu_r', vmin=-df_import.value.max(), vmax=df_import.value.max(),
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

if st.button('Clear JSON'):
    try:
        del st.session_state['json_file']
    except:
        pass

if 'json_file' in st.session_state:
    json_file = st.session_state['json_file']
else:
    json_file = st.file_uploader('Upload a JSON file', type='json')

if not json_file:
    st.stop()

df_all, league_settings = load_and_process_data(json_file)

st.write(df_all.head())

st.session_state['json_file'] = json_file

st.write(st.session_state['json_file'] if 'json_file' in st.session_state else 'No file uploaded')

st.write('--------------------------------')
st.write('--------------------------------')
st.write('--------------------------------')
st.write('--------------------------------')


"""df_import = st.session_state['df_import']
league_settings = st.session_state['league_settings']

## Markdown that shows my season and team
st.markdown(f"Season: {league_settings['season']}, My Team: {df_import[df_import.tid == league_settings['my_team_id']]['team'].values[0]}")

print('Data loaded and processed')

df_import['pot'] = df_import['rating_upper']

selected_teams = select_teams(df_import)
df_filtered = filter_teams(df_import, selected_teams)

# Create a button to clear the selected pids
if st.button('Clear selected players'):
    st.session_state['selected_pids'] = []

df_display = df_filtered[
    ['player', 'pid', 'team', 'pos', 'age', 'ovr', 'pot', 'years', 'cap_hit', 'value', 'v1', 'v2']].sort_values('value',
                                                                                                                ascending=False)

st.session_state['selected_pids'] = display_and_select_pids(df_display)

if len(st.session_state['selected_pids']) > 0:
    trade_df = df_import[df_import.pid.isin(st.session_state['selected_pids'])]
    pivot_table = trade_df.pivot_table(index='player', columns='team', values='value', aggfunc='sum', fill_value=0)
    # Sort rows to keep teams together
    pivot_table = pivot_table.sort_values(by=pivot_table.columns.tolist(), ascending=True)
    # Add a column to show the total value for each team
    pivot_table.loc['Total'] = pivot_table.sum()
    st.dataframe(pivot_table)

[st.plotly_chart(player_plot(pid, df_import), use_container_width=True) for pid in st.session_state['selected_pids']]
"""