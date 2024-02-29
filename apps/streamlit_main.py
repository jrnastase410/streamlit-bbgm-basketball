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
from st_aggrid import *
import logging

# Set up logging to write to the console
logging.basicConfig(level=logging.INFO, format='%(message)s')

# Example function that writes to the console
def write_to_console(text):
    logging.info(text)


@st.cache_data(ttl=60 * 60 * 24 * 3, max_entries=3, show_spinner=True)
def load_and_process_data(json_file, ci_q=0.75):
    write_to_console('Loading JSON file')

    r_json = json.load(json_file)

    league_settings = {
        'season': r_json['gameAttributes']['season'],
        'salary_cap': r_json['gameAttributes']['salaryCap'],
        'max_contract': r_json['gameAttributes']['maxContract'] / r_json['gameAttributes']['salaryCap'],
        'my_team_id': r_json['gameAttributes']['userTid'][-1]['value']
    }

    write_to_console('Converting json to df')

    df = player_json_to_df(r_json, keep=['ratings', 'salaries'])
    df = df[df.season == league_settings['season']].drop_duplicates(['pid', 'season'], keep='last').reset_index(
        drop=True)

    df['tid'] = df['current_tid'].copy()
    df = df.drop(columns=['current_tid'], axis=1)
    team_dict = dict([(teams['tid'], teams['abbrev']) for teams in r_json['teams']])
    team_dict[-2] = 'Draft'
    team_dict[-1] = 'FA'
    df['team'] = df['tid'].map(team_dict)

    # Calculate Progs
    write_to_console('Calculating Progs')
    df['results'] = df.apply(lambda x: calc_progs(x['ovr'], x['age'], ci_q), axis=1)
    write_to_console('Assigning Progs to Columns')
    df[['rating_prog', 'rating_upper_prog', 'rating_lower_prog', 'cap_value_prog']] = pd.DataFrame(
        df['results'].tolist(), index=df.index)

    write_to_console('Calculating Potential / Surplus Value')
    # Calculate New Potential
    df['rating_upper'] = df['rating_upper_prog'].apply(lambda x: max(x.values())).round(0).astype('int64[pyarrow]')

    # Calculate Salary Projections / Fills
    write_to_console('Calculating Salary Caps')
    df['salary_caps'] = df.apply(lambda x: {i: league_settings['salary_cap'] * (1.0275 ** i) for i in range(10)},
                                 axis=1)
    write_to_console('Calculating Cap Hits')
    df['cap_hits'] = df.apply(lambda x: {
        i: (x['salaries'][i] / x['salary_caps'][i]) if isinstance(x['salaries'], dict) and isinstance(x['salary_caps'],
                                                                                                      dict) and i in x[
                                                           'salaries'] else None for i in range(10)}, axis=1)
    write_to_console('Predicting Cap Hits')
    df['cap_hits_prog'] = df.apply(predict_cap_hit, axis=1)
    write_to_console('Filling Cap Hits')
    df['cap_hits_filled'] = df.apply(lambda row: fill_cap_hits(row['cap_hits'], row['cap_hits_prog'], 1.0275), axis=1)

    # Calculate Surplus
    write_to_console('Calculating surplus progs')
    df['surplus_1_progs'] = df[['age','rating_prog','rating_upper']].apply(lambda x: {
        i: (x['cap_value_prog'][i] - x['cap_hits'][i]) if isinstance(x['cap_value_prog'], dict) and isinstance(
            x['cap_hits'], dict) and i in x['cap_value_prog'] and x['cap_hits'][i] is not None else 0 for i in
        range(10)}, axis=1)
    df['surplus_2_progs'] = df.apply(lambda x: {
        i: (x['cap_value_prog'][i] - x['cap_hits_filled'][i]) if isinstance(x['cap_value_prog'], dict) and isinstance(
            x['cap_hits_filled'], dict) and i in x['cap_value_prog'] and x['cap_hits_filled'][i] is not None else 0 for
        i in range(10)}, axis=1)

    # Sum up Values
    write_to_console('Summing up values')
    df['v1'] = df['surplus_1_progs'].apply(lambda x: sum(x.values()))
    df['v2'] = (df['surplus_2_progs'].apply(lambda x: sum(x.values())) - df['v1']).clip(0, )
    df['value'] = df[['v1', 'v2']].sum(axis=1)

    # Clean up at the end
    df['player'] = df['firstName'] + ' ' + df['lastName']
    df['cap_hit'] = df['salary'].fillna(0) / league_settings['salary_cap']
    df['years'] = df['salaries'].apply(lambda x: len(x) if isinstance(x, dict) else 0)

    write_to_console('Finished processing data -> Returning')

    columns_to_keep = ['pid', 'player', 'season', 'ovr', 'pot', 'age', 'pos', 'salary', 'salaries', 'tid', 'team',
                       'rating_prog',
                       'rating_upper_prog', 'rating_lower_prog', 'cap_value_prog',
                       'rating_upper', 'salary_caps', 'cap_hits', 'cap_hits_prog',
                       'cap_hits_filled', 'surplus_1_progs', 'surplus_2_progs', 'v1', 'v2',
                       'value', 'cap_hit', 'years']

    ## Use logger to print memory util of returned dataframe
    return_df = df[~df.team.isna()][columns_to_keep].reset_index()
    write_to_console(f'Memory Utilization: {return_df.memory_usage(deep=True).sum() / 1024 ** 2:.2f} MB')
    return return_df, league_settings


def select_teams(df):
    teams_to_choose_from = ['*All*'] + list(np.sort([x for x in df.team.unique() if len(x) == 3])) + ['FA', 'Draft']
    num_columns = 7
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
        return df[df.team.isin(selected_teams)]
    else:
        return df


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
        use_container_width=False
    )

    # Filter the dataframe using the temporary column, then drop the column
    selected_pids = list(set(edited_df[edited_df.Select]['pid'].to_list() + st.session_state.selected_pids))
    return selected_pids


json_file = st.file_uploader('Upload a JSON file', type='json')
if not json_file:
    st.stop()

df_import, league_settings = load_and_process_data(json_file)

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
