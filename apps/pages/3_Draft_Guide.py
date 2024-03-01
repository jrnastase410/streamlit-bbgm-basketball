import streamlit as st

# Set page configuration with Bootstrap theme
st.set_page_config(
    page_title='Draft Guide',
    layout='centered'
)

from calcs import *
from data import *
from utils import *
from plots import *

if 'draft_df' not in st.session_state:
    st.session_state['draft_df'] = \
    load_and_process_data(st.session_state['r_json'], filter_column='team', filter_values=['Draft'])[0]

df = st.session_state['draft_df'].copy()

# Perform calculations
df['cap_value'] = df['cap_value_prog'].apply(lambda x: sum(x.values()))
df['value'] = df['cap_value'].round(2)
df['rk'] = df['value'].rank(ascending=False, method='dense').astype(int)
df['info'] = df['rk'].astype(str) + ' / ' + df['player'] + ' / ' + df['pos'] + ' / ' + df['age'].astype(str)
df['ratings'] = df['ovr'].astype(str) + ' / ' + df['pot'].astype(str)

# Add a checkbox column for drafted players
df.insert(0, "Drafted", False)

# Get dataframe row-selections from user with st.data_editor
st.markdown("""# Draft Guide""", unsafe_allow_html=True)
st.markdown("""------------------------------""")
st.markdown("""### Available Players""", unsafe_allow_html=True)
edited_df = st.data_editor(
    df[['Drafted', 'info', 'ratings', 'value']].sort_values('value', ascending=False).style \
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
st.markdown("""### Drafted Players""", unsafe_allow_html=True)
st.dataframe(drafted_df, use_container_width=True)
