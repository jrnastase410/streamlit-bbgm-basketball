import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(
    page_title='Mobile View',
    layout='wide'
)

df_import = st.session_state['df_import']

teams_to_choose_from = ['*All*'] + list(np.sort([x for x in df_import.team.unique() if x not in ['FA','Draft']])) + ['FA', 'Draft']

# Select two teams for the trade
team1, team2 = st.selectbox('Select Team 1', teams_to_choose_from), st.selectbox('Select Team 2', teams_to_choose_from)

# Filter the dataframe for each team and select only the required columns
df_team1 = df_import[df_import['team'] == team1][['player', 'value']].sort_values('value', ascending=False)
df_team2 = df_import[df_import['team'] == team2][['player', 'value']].sort_values('value', ascending=False)

# Create a column for selection in each dataframe
df_team1['Select'] = False
df_team2['Select'] = False

# Display the dataframes side by side and allow user to select members for trade
col1, col2 = st.columns(2)
with col1:
    edited_df_team1 = st.data_editor(df_team1.round({'value': 2}), hide_index=True, key='df_team1')
with col2:
    edited_df_team2 = st.data_editor(df_team2.round({'value': 2}), hide_index=True, key='df_team2')

# Get the selected members for trade
selected_team1 = edited_df_team1[edited_df_team1['Select']]
selected_team2 = edited_df_team2[edited_df_team2['Select']]

# Calculate and display the sum of the 'value' column for the selected members of each team
st.write(f"Total value for selected members of {team1}: {selected_team1['value'].sum().round(2)}")
st.write(f"Total value for selected members of {team2}: {selected_team2['value'].sum().round(2)}")