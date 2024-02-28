import numpy as np
import pandas as pd
import pickle

poly_under = np.load('./models/poly_under.npy')
poly_over = np.load('./models/poly_over.npy')

cap_hit_model = pickle.load(open('models/cap_hit_model.pkl', 'rb'))

UNDER_OVER = 56.064

progs = pd.read_parquet('./constants/progression.parquet')
for i in range(1, 10):
    progs[f'y_{i}'] = progs[f'y_{i}'] / (np.sum(progs[f'y_{i}']) / progs.age.nunique())


def ovr_to_vorp(ovr):
    if ovr <= UNDER_OVER:
        return np.polyval(poly_under, ovr)
    else:
        return np.polyval(poly_over, ovr)

def compute_kde_percentile_fast(x_values, y_values, percentile):
    # Calculate the cumulative sum of the y_values
    cumulative_sum = np.cumsum(y_values)

    # Find the index where the cumulative sum is just greater than or equal to the desired percentile
    index = np.searchsorted(cumulative_sum, percentile)

    # Return the corresponding x_value at this index
    return x_values[index]


def calc_progs(ovr, age, q=0.9):
    x_prog = progs[progs.age == age]['x'].values
    x_rating = x_prog + ovr
    x_pred = np.array([ovr_to_vorp(x) for x in x_rating])
    x_value = np.clip(x_pred, 0, None)
    x_cap_hit = 30 * x_value / 312.77

    rating_dict = {}
    rating_uppper_dict = {}
    rating_lower_dict = {}
    vorp_added_dict = {}
    cap_value_dict = {}

    rating_dict[0] = ovr
    rating_uppper_dict[0] = ovr
    rating_lower_dict[0] = ovr
    vorp_added_dict[0] = ovr_to_vorp(ovr)
    cap_value_dict[0] = 30 * np.maximum(0, vorp_added_dict[0]) / 312.77

    progs_age = progs[progs.age == age]
    y_values = progs_age[[f'y_{i}' for i in range(1, 10)]].values

    for i in range(1, 10):
        y = y_values[:, i - 1]
        rating_dict[i] = np.dot(x_rating, y) / np.sum(y)
        rating_uppper_dict[i] = compute_kde_percentile_fast(x_rating, y, q)
        rating_lower_dict[i] = compute_kde_percentile_fast(x_rating, y, 1 - q)
        vorp_added_dict[i] = np.dot(x_value, y) / np.sum(y)
        cap_value_dict[i] = np.dot(x_cap_hit, y) / np.sum(y)

    return {
        'rating': rating_dict,
        'rating_upper': rating_uppper_dict,
        'rating_lower': rating_lower_dict,
        'vorp_added': vorp_added_dict,
        'cap_value': cap_value_dict
    }

def predict_cap_hit(row):
    age = row['age']
    rating_prog = row['rating_prog']
    pot = row['rating_upper']

    cap_hit_proj = {}
    for year, rating in rating_prog.items():
        # The model takes 'age', 'rating', and 'pot' as inputs
        features = [age + year, rating, pot]
        cap_hit_proj[year] = cap_hit_model.predict([features])[0]

    return cap_hit_proj


def fill_cap_hits(cap_hits, cap_hits_proj, division_factor):
    filled_cap_hits = {}
    null_count = 0
    last_non_null_year = None

    for i in range(10):
        if cap_hits[i] is not None:
            last_non_null_year = i

    for i in range(10):
        if cap_hits[i] is None:
            if last_non_null_year is not None:
                filled_cap_hits[i] = cap_hits_proj.get(last_non_null_year, 0) / (division_factor ** null_count)
            else:
                filled_cap_hits[i] = 0  # or some default value if no non-null year found
            null_count += 1
        else:
            filled_cap_hits[i] = cap_hits[i]
            null_count = 0  # Reset null count if non-None value is encountered

    return filled_cap_hits