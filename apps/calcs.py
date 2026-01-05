import numpy as np
import pandas as pd
import pickle

import streamlit as st


@st.cache_resource
def load_poly_models():
    poly_under = np.load('./models/poly_under.npy')
    poly_over = np.load('./models/poly_over.npy')
    return poly_under, poly_over


@st.cache_resource
def load_cap_hit_model():
    return pickle.load(open('models/cap_hit_model.pkl', 'rb'))


@st.cache_data
def load_progs():
    progs = pd.read_parquet('./constants/progression.parquet')
    for i in range(1, 10):
        progs[f'y_{i}'] = progs[f'y_{i}'] / (np.sum(progs[f'y_{i}']) / progs.age.nunique())
    return progs


poly_under, poly_over = load_poly_models()
cap_hit_model = load_cap_hit_model()
progs = load_progs()

UNDER_OVER = 56.064


def ovr_to_vorp_norm(ovr):
    if ovr <= UNDER_OVER:
        return np.polyval(poly_under, ovr)
    else:
        return np.polyval(poly_over, ovr)


def predict_minutes(ovr):
    # =6.6208*LN(A2) - 26.515
    ovr_capped = max(ovr, 1)

    pred_ini = 6.6208 * np.log(ovr_capped) - 26.515
    pred_inverse = 1 / (1 + np.exp(-pred_ini))
    pred_final = 3000 * pred_inverse
    return pred_final


def ovr_to_vorp(ovr):
    return ovr_to_vorp_norm(ovr) * predict_minutes(ovr) / (82 * 32)


def compute_kde_percentile_fast(x_values, y_values, percentile):
    # Calculate the cumulative sum of the y_values
    cumulative_sum = np.cumsum(y_values)

    # Find the index where the cumulative sum is just greater than or equal to the desired percentile
    index = np.searchsorted(cumulative_sum, percentile)

    # Return the corresponding x_value at this index
    return x_values[index]


@st.cache_data(show_spinner=False)
def calc_progs(ovr, age, q=0.9):
    sum_rvorp = 309.00924055899424
    sum_wvorp = 41 * 30 / 2.8

    sum_vorp = (sum_rvorp + sum_rvorp) / 2

    num_teams = 30

    x_prog = progs[progs.age == age]['x'].values
    x_rating = x_prog + ovr
    x_pred = np.array([ovr_to_vorp(x) for x in x_rating])
    x_value = np.clip(x_pred, 0, None)
    x_cap_hit = num_teams * x_value / sum_vorp

    rating_dict = {}
    rating_upper_dict = {}
    rating_lower_dict = {}
    vorp_added_dict = {}
    cap_value_dict = {}

    rating_dict[0] = ovr
    rating_upper_dict[0] = ovr
    rating_lower_dict[0] = ovr
    vorp_added_dict[0] = ovr_to_vorp(ovr)
    cap_value_dict[0] = num_teams * np.maximum(0, vorp_added_dict[0]) / sum_vorp

    progs_age = progs[progs.age == age]
    y_values = progs_age[[f'y_{i}' for i in range(1, 10)]].values

    for i in range(1, 10):
        y = y_values[:, i - 1]
        rating_dict[i] = np.dot(x_rating, y) / np.sum(y)
        rating_upper_dict[i] = compute_kde_percentile_fast(x_rating, y, q)
        rating_lower_dict[i] = compute_kde_percentile_fast(x_rating, y, 1 - q)
        vorp_added_dict[i] = np.dot(x_value, y) / np.sum(y)
        cap_value_dict[i] = np.dot(x_cap_hit, y) / np.sum(y)

    return {
        'rating': rating_dict,
        'rating_upper': rating_upper_dict,
        'rating_lower': rating_lower_dict,
        'cap_value': cap_value_dict
    }


def predict_cap_hit_array(ages, ovrs, pots):
    # Convert inputs to numpy arrays
    ages = np.array(ages)
    ovrs = np.array(ovrs)
    pots = np.array(pots)

    # Reshape inputs to 2D arrays
    ages = ages.reshape(-1, 1)
    ovrs = ovrs.reshape(-1, 1)
    pots = pots.reshape(-1, 1)

    # Concatenate inputs
    inputs = np.concatenate([ages, ovrs, pots], axis=1)

    # Predict cap hit for all inputs at once
    predictions = cap_hit_model.predict(inputs)

    return predictions


@st.cache_data
def predict_cap_hit(row):
    age = row['age']
    rating_prog = row['rating_prog']
    pot = row['rating_upper']

    # Prepare inputs for vectorized prediction
    ages = [age + year for year in rating_prog.keys()]
    ovrs = list(rating_prog.values())
    pots = [pot] * len(rating_prog)

    # Call the vectorized prediction function
    predictions = predict_cap_hit_array(ages, ovrs, pots)

    # Create a dictionary mapping years to predictions
    cap_hit_proj = dict(zip(rating_prog.keys(), predictions))

    return cap_hit_proj


def fill_cap_hits(cap_hits, cap_hits_proj, inflation_factor):
    filled_cap_hits = {}
    null_count = 0
    last_non_null_year = None

    for i in range(10):
        if cap_hits[i] is not None:
            last_non_null_year = i

    for i in range(10):
        if cap_hits[i] is None:
            if last_non_null_year is not None:
                filled_cap_hits[i] = cap_hits_proj.get(last_non_null_year, 0) / (inflation_factor ** null_count)
            else:
                filled_cap_hits[i] = 0  # or some default value if no non-null year found
            null_count += 1
        else:
            filled_cap_hits[i] = cap_hits[i]
            null_count = 0  # Reset null count if non-None value is encountered

    return filled_cap_hits


def calculate_progs(df, ci_q):
    # Vectorized calculation of progressions
    results = [calc_progs(ovr, age, ci_q) for ovr, age in zip(df['ovr'], df['age'])]
    df[['rating_prog', 'rating_upper_prog', 'rating_lower_prog', 'cap_value_prog']] = pd.DataFrame(
        results, index=df.index)
    return df


def calculate_potential(df):
    df['rating_upper'] = df['rating_upper_prog'].apply(lambda x: max(x.values())).round(0).astype('int64[pyarrow]')
    df['pot'] = df['rating_upper'].values
    return df


def calculate_salary_projections(df, league_settings, inflation_factor, salary_cap_scale=1.0):
    # Vectorized calculation of salary caps
    salary_cap_base = salary_cap_scale * league_settings['salary_cap']
    df['salary_caps'] = [
        {i: salary_cap_base * (inflation_factor ** i) for i in range(10)}
        for _ in range(len(df))
    ]
    return df


def calculate_cap_hits(df):
    # Vectorized calculation of cap hits
    cap_hits_list = []
    for salaries, salary_caps in zip(df['salaries'], df['salary_caps']):
        cap_hit = {
            i: (salaries[i] / salary_caps[i]) if isinstance(salaries, dict) and isinstance(salary_caps, dict) and i in salaries else None 
            for i in range(10)
        }
        cap_hits_list.append(cap_hit)
    df['cap_hits'] = cap_hits_list
    return df


def predict_cap_hits(df):
    # Vectorized prediction of cap hits
    cap_hits_prog_list = []
    for _, row in df[['age', 'rating_prog', 'rating_upper']].iterrows():
        cap_hits_prog_list.append(predict_cap_hit(row))
    df['cap_hits_prog'] = cap_hits_prog_list
    return df


def calculate_surplus(df):
    # Vectorized calculation of surplus
    surplus_1_list = []
    surplus_2_list = []
    
    for cap_value_prog, cap_hits, cap_hits_filled in zip(df['cap_value_prog'], df['cap_hits'], df['cap_hits_filled']):
        surplus_1 = {
            i: (cap_value_prog[i] - cap_hits[i]) if isinstance(cap_value_prog, dict) and isinstance(cap_hits, dict) 
                and i in cap_value_prog and cap_hits[i] is not None else 0 
            for i in range(10)
        }
        surplus_2 = {
            i: (cap_value_prog[i] - cap_hits_filled[i]) if isinstance(cap_value_prog, dict) and isinstance(cap_hits_filled, dict) 
                and i in cap_value_prog and cap_hits_filled[i] is not None else 0 
            for i in range(10)
        }
        surplus_1_list.append(surplus_1)
        surplus_2_list.append(surplus_2)
    
    df['surplus_1_progs'] = surplus_1_list
    df['surplus_2_progs'] = surplus_2_list
    return df


def scale_surplus(df, scale_factor):
    # Vectorized scaling of surplus
    df['surplus_1_progs'] = [{i: x[i] * (scale_factor ** i) for i in x} for x in df['surplus_1_progs']]
    df['surplus_2_progs'] = [{i: x[i] * (scale_factor ** i) for i in x} for x in df['surplus_2_progs']]
    return df


def sum_values(df):
    df['v1'] = df['surplus_1_progs'].apply(lambda x: sum(x.values()))
    df['v2'] = (df['surplus_2_progs'].apply(lambda x: sum(x.values())) - df['v1']).clip(0, )
    df['value'] = df[['v1', 'v2']].sum(axis=1)
    return df
