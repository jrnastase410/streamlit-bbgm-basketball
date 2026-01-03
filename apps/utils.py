import pickle
from pathlib import Path
import xgboost as xgb


def apply_model_predictions(df, models_dir="../models/ovr"):
    """Load models and apply predictions to calculate new_ovr"""
    models_dir = Path(models_dir)

    # Load metadata
    with open(models_dir / "metadata.pkl", "rb") as f:
        metadata = pickle.load(f)

    features = metadata["features"]
    targets = metadata["targets"]

    # Load all models
    models = {}
    for target in targets:
        with open(models_dir / f"{target}_model.pkl", "rb") as f:
            models[target] = pickle.load(f)

    # Make predictions
    X_predict = df[features].to_numpy()
    dpred = xgb.DMatrix(X_predict)

    for target, model in models.items():
        df[f"pred_{target}"] = model.predict(dpred)

    # Calculate BPM and WS
    df["bpm"] = df["pred_obpm"] + df["pred_dbpm"]
    df["ws"] = df["pred_ows_rate"] + df["pred_dws_rate"]

    # Scale to ovr distribution
    ovr_mean = df["ovr"].mean()
    ovr_std = df["ovr"].std()

    df["bpm_scaled"] = (df["bpm"] - df["bpm"].mean()) / df[
        "bpm"
    ].std() * ovr_std + ovr_mean
    df["ws_scaled"] = (df["ws"] - df["ws"].mean()) / df["ws"].std() * ovr_std + ovr_mean

    # Create new_ovr (weighted average - ws gets 4x weight based on your code)
    df["new_ovr"] = (df["bpm_scaled"] + 4 * df["ws_scaled"]) / 5

    # Replace ovr with new_ovr
    df["ovr"] = df["new_ovr"]

    return df


def load_and_process_data(
    r_json,
    keep=["ratings", "salaries"],
    ci_q=0.75,
    inflation_factor=1.0275,
    scale_factor=0.9,
    filter_column=None,
    filter_values=None,
    use_model_ovr=True,
):
    league_settings = get_league_settings(r_json)
    df = player_json_to_df(r_json, keep=keep)
    df = cleanup_df(df, league_settings, r_json)

    # Apply model predictions if requested
    if use_model_ovr:
        df = apply_model_predictions(df)

    df = filter_df(df, filter_column, filter_values)
    df = calculate_progs(df, ci_q)
    df = calculate_potential(df)
    df = calculate_salary_projections(df, league_settings, inflation_factor)
    df = calculate_cap_hits(df)
    df = predict_cap_hits(df)
    df["cap_hits_filled"] = df.apply(
        lambda row: fill_cap_hits(
            row["cap_hits"], row["cap_hits_prog"], inflation_factor
        ),
        axis=1,
    )
    df = calculate_surplus(df)
    df = scale_surplus(df, scale_factor)
    df = sum_values(df)

    columns_to_keep = [
        "pid",
        "player",
        "season",
        "ovr",
        "pot",
        "age",
        "pos",
        "salary",
        "salaries",
        "tid",
        "team",
        "rating_prog",
        "rating_upper_prog",
        "rating_lower_prog",
        "cap_value_prog",
        "rating_upper",
        "salary_caps",
        "cap_hits",
        "cap_hits_prog",
        "cap_hits_filled",
        "surplus_1_progs",
        "surplus_2_progs",
        "v1",
        "v2",
        "value",
        "cap_hit",
        "years",
    ]

    return_df = df[~df.team.isna()][columns_to_keep].reset_index()
    return return_df, league_settings
