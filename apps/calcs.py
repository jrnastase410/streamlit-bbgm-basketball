import numpy as np
import pandas as pd

poly_under = np.load('./models/poly_under.npy')
poly_over = np.load('./models/poly_over.npy')

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
    x_pred = [ovr_to_vorp(x) for x in x_rating]
    x_value = np.array(x_pred).clip(0, )
    x_cap_hit = 30 * x_value / 433.58

    rating_dict = dict()
    rating_uppper_dict = dict()
    rating_lower_dict = dict()
    vorp_added_dict = dict()
    cap_value_dict = dict()

    rating_dict[0] = ovr
    rating_uppper_dict[0] = ovr
    rating_lower_dict[0] = ovr
    vorp_added_dict[0] = ovr_to_vorp(ovr)
    cap_value_dict[0] = 30 * vorp_added_dict[0] / 433.58

    for i in range(1, 10):
        y = progs[progs.age == age][f'y_{i}'].values
        rating_dict[i] = np.dot(x_rating, y) / np.sum(y)
        rating_uppper_dict[i] = compute_kde_percentile_fast(x_rating, y, q)
        rating_lower_dict[i] = compute_kde_percentile_fast(x_rating, y, 1 - q)
        vorp_added_dict[i] = np.dot(x_value, y) / np.sum(y)
        cap_value_dict[i] = np.dot(x_cap_hit, y) / np.sum(y)

    return {'rating': rating_dict,
            'rating_upper': rating_uppper_dict,
            'rating_lower': rating_lower_dict,
            'vorp_added': vorp_added_dict,
            'cap_value': cap_value_dict}