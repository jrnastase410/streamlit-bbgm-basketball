import streamlit as st

# Set page configuration with Bootstrap theme
st.set_page_config(
    page_title='My Team',
    layout='centered'
)

from calcs import *
from data import *
from utils import *
from plots import *

# Use centralized data from session state
if 'full_df' not in st.session_state:
    st.error('Please upload a JSON file first')
    st.stop()

my_team_id = st.session_state['league_settings']['my_team_id']
df = st.session_state['full_df'][st.session_state['full_df']['tid'] == my_team_id]

# Perform calculations
df['cap_value'] = df['cap_value_prog'].apply(lambda x: sum(x.values()))
df['value'] = df['value'].round(2)
df['rk'] = df['value'].rank(ascending=False, method='dense').astype(int)
df['info'] = df['pos'].astype(str) + ' / ' + df['player']
df['ratings'] = df['age'].astype(str) + ' / ' + df['ovr'].astype(str) + ' / ' + df['pot'].astype(str)

# Add a checkbox column for drafted players
df.insert(0, "Drafted", False)

# Get dataframe row-selections from user with st.data_editor
st.markdown("""# My Team""", unsafe_allow_html=True)
st.markdown("""------------------------------""")
st.markdown("""### Roster""", unsafe_allow_html=True)
edited_df = st.data_editor(
    df[['Drafted', 'info', 'ratings', 'value', 'pid']].sort_values('value', ascending=False).style \
        .background_gradient(cmap='RdBu_r', vmin=-5, vmax=5, subset=['value']) \
        .format(precision=2, subset=['value']),
    hide_index=True,
    column_config={"Drafted": st.column_config.CheckboxColumn(required=True)},
    disabled=['value', 'ovr', 'pot'],
    use_container_width=True
)

# Filter the dataframe based on the checkbox column
selected_players = edited_df[edited_df.Drafted].pid.to_list()

[st.plotly_chart(player_plot(pid, df), use_container_width=True) for pid in selected_players]
