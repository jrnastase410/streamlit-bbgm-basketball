import streamlit as st
from data import load_json

# Set page configuration with Bootstrap theme
st.set_page_config(
    page_title='Home / Upload',
    layout='centered',
    ## good upload icon
    page_icon=':open_file_folder:'
)

if st.button('Clear JSON'):
    for key_to_drop in ['r_json', 'draft_df', 'my_team_df', 'resign_df', 'all_df']:
        try:
            del st.session_state[key_to_drop]
        except:
            pass

if 'r_json' in st.session_state:
    r_json = st.session_state['r_json']
else:
    json_upload = st.file_uploader('Upload a JSON file', type='json')
    if not json_upload:
        st.stop()
    r_json = load_json(json_upload)

st.session_state['r_json'] = r_json

st.write(st.session_state['r_json'].keys() if 'r_json' in st.session_state else 'No file uploaded')