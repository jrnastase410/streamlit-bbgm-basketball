import numpy as np
import yaml

with open('../params.yaml') as f:
    params = yaml.safe_load(f)

poly_under = np.load('../models/poly_under.npy')
poly_over = np.load('../models/poly_over.npy')

UNDER_OVER = params['UNDER_OVER']


def ovr_to_vorp(ovr):
    if ovr <= UNDER_OVER:
        return np.polyval(poly_under, ovr)
    else:
        return np.polyval(poly_over, ovr)
