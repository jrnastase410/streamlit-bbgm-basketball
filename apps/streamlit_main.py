print('Importing libraries...')

import os
print(os.getcwd())

from calcs import *
from data import player_json_to_df
import plotly.graph_objects as go
import streamlit as st
import json

st.set_page_config(
    page_title='Home',
    layout='wide'
)



@st.cache_data
def load_and_process_data(json_file):
    r_json = json.load(json_file)
    df = player_json_to_df(r_json)
    df = df[df.season == df[~df.salary.isna()].season.max()].drop_duplicates(['pid', 'season']).reset_index(drop=True)
    df['results'] = df.apply(lambda x: calc_progs(x['ovr'], x['age'], 0.75), axis=1)
    df['rating_prog'] = df['results'].apply(lambda x: x['rating'])
    df['rating_upper_prog'] = df['results'].apply(lambda x: x['rating_upper'])
    df['rating_lower_prog'] = df['results'].apply(lambda x: x['rating_lower'])
    df['vorp_added_prog'] = df['results'].apply(lambda x: x['vorp_added'])
    df['cap_value_prog'] = df['results'].apply(lambda x: x['cap_value'])
    df['team'] = df['tid'].map(dict([(teams['tid'], teams['abbrev']) for teams in r_json['teams']]))
    return df


def player_plot(pid, df):
    # Filter the dataframe for the specific pid
    df_filtered = df[df.pid == pid]

    # Retrieve the player's first name and last name
    first_name = df_filtered['firstName'].values[0]
    last_name = df_filtered['lastName'].values[0]

    # Create the title
    title = f'{first_name} {last_name}'

    # Extract the rating, value, and bounds data
    rating_data = df_filtered['rating_prog'].values[0]
    rating_upper_data = df_filtered['rating_upper_prog'].values[0]
    rating_lower_data = df_filtered['rating_lower_prog'].values[0]
    value_data = df_filtered['vorp_added_prog'].values[0]
    cap_value_data = df_filtered['cap_value_prog'].values[0]

    # Create the plot for ratings
    fig = go.Figure()

    # Add the plot for upper and lower bounds as lines with the area between them filled
    fig.add_trace(
        go.Scatter(
            x=list(rating_upper_data.keys()),
            y=list(rating_upper_data.values()),
            name='Upper Bound',
            mode='lines',
            line=dict(width=0),
            hoverinfo='skip',
            showlegend=False,
        )
    )

    fig.add_trace(
        go.Scatter(
            x=list(rating_lower_data.keys()),
            y=list(rating_lower_data.values()),
            name='Lower Bound',
            mode='none',
            fill='tonexty',
            hoverinfo='skip',
            fillcolor='rgba(255, 90, 95, 0.2)',
            showlegend=False,
        )
    )

    # Add the plot for ratings as a line
    fig.add_trace(
        go.Scatter(
            x=list(rating_data.keys()),
            y=list(rating_data.values()),
            name='Rating',
            line=dict(
                color='rgb(255, 90, 95)'
            ),
            customdata=np.stack((list(rating_lower_data.values()), list(rating_upper_data.values())), axis=-1),
            hovertemplate=
            '<b>Year</b>: %{x}<br>' +
            '<b>Rating</b>: %{y:.1f}<br>' +  # Round to 1 decimal place
            '<b>Lower Bound</b>: %{customdata[0]:.1f}<br>' +  # Round to 1 decimal place
            '<b>Upper Bound</b>: %{customdata[1]:.1f}<br>',  # Round to 1 decimal place
        )
    )

    # Add the plot for values as bars
    fig.add_trace(
        go.Bar(
            x=[x - 0.2 for x in list(value_data.keys())],
            y=list(value_data.values()),
            name='Value',
            yaxis='y2',
            width=0.35,
            marker=dict(
                color='rgb(252,100,45)'
            ),
            text=[f'{val:.1f}' for val in list(value_data.values())],
            textposition='outside',
            textfont=dict(
                color='rgb(252,100,45)',
                size=25,
            ),
        )
    )

    # Add the plot for cap values as bars
    fig.add_trace(
        go.Bar(
            x=[x + 0.2 for x in list(cap_value_data.keys())],
            y=list(cap_value_data.values()),
            name='Cap Value',
            yaxis='y3',
            width=0.35,
            marker=dict(
                color='rgb(0, 166, 153)'
            ),
            text=[f'{val * 100:.1f}%' for val in list(cap_value_data.values())],
            textposition='outside',
            textfont=dict(
                color='rgb(0, 166, 153)',
                size=40,
            ),
        )
    )

    # Update the plot title
    fig.update_layout(
        template='simple_white',
        title=title,
        barmode='group',
        yaxis=dict(
            range=[10, 90],
            showgrid=False,
            showticklabels=True,
        ),
        yaxis2=dict(
            range=[0, 20],
            overlaying='y',
            side='right',
            showgrid=False,
            showticklabels=False,
        ),
        yaxis3=dict(
            range=[0, 1],
            overlaying='y',
            side='left',
            showgrid=False,
            showticklabels=False,
        )
    )

    return fig


def display_team(team, df):
    team_df = df[df['team'] == team]
    team_df = team_df[['player', 'pid', 'season', 'age', 'ovr', 'pot']]
    return team_df


# Upload json file
json_file = st.file_uploader('Upload a JSON file', type='json')
if not json_file:
    st.stop()

df = load_and_process_data(json_file)
df['player'] = df['firstName'] + ' ' + df['lastName']
team_names = np.sort(df['team'].astype(str).unique())
my_team = st.selectbox('Select your team:', team_names)
if my_team:
    team_df = display_team(my_team, df)
    st.dataframe(team_df, use_container_width=True)
player_name = st.text_input('Enter player name:')
team_name = st.text_input('Enter team name:')
matching_players = df[(df['player'].str.contains(player_name, na=False, case=False)) & (
    df['team'].str.contains(team_name, na=False, case=False))]
if not matching_players.empty:
    selected_index = st.selectbox('Select a player:', matching_players.player)
    selected_player = matching_players[matching_players.player == selected_index].iloc[0]
    pid = selected_player['pid']
    player_fig = player_plot(pid, df)
    st.plotly_chart(player_fig, use_container_width=True)
else:
    st.write('No matching players found.')
