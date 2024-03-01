import logging
from data import *
from calcs import *
import streamlit as st

logging.basicConfig(level=logging.INFO, format='%(message)s')


def write_to_console(text):
    logging.info(text)

@st.cache_data
def load_and_process_data(r_json, keep=['ratings', 'salaries'], ci_q=0.75, inflation_factor=1.0275,
                          scale_factor=0.9, filter_column=None, filter_values=None):
    league_settings = get_league_settings(r_json)
    df = player_json_to_df(r_json, keep=keep)
    df = cleanup_df(df, league_settings, r_json)
    df = filter_df(df, filter_column, filter_values)
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