import pandas as pd


def create_df_from_player_data(players, key, additional_fields=None):
    data = []
    for player in players:
        for item in player[key]:
            row = {'pid': player['pid'], 'current_tid': player['tid']}
            if additional_fields:
                row.update({field: player[field] for field in additional_fields})
            row.update(item)
            data.append(row)
    return pd.DataFrame(data).convert_dtypes(dtype_backend='pyarrow')


def player_json_to_df(r_json):
    players = r_json['players']

    stats_df = create_df_from_player_data(players, 'stats')
    stats_df = stats_df[(stats_df.playoffs == False)].reset_index(drop=True)

    ratings_df = create_df_from_player_data(players, 'ratings', ['firstName', 'lastName', 'born'])
    ratings_df['age'] = ratings_df['season'] - ratings_df['born'].apply(lambda x: x['year'])
    ratings_df = ratings_df.drop('born', axis=1).reset_index(drop=True)

    salaries_df = create_df_from_player_data(players, 'salaries')
    salaries_df = salaries_df.reset_index(drop=True)

    def calculate_future_years(group, season):
        future_years = {}
        max_season = group['season'].max()
        num_records = max_season - season + 1
        for i in range(min(num_records, len(group))):
            future_years[i] = group['amount'].iloc[i]
        return future_years

    grouped = salaries_df.groupby('pid')

    new_rows = []

    # Iterate over groups
    for pid, group in grouped:
        for idx, row in group.iterrows():
            pid = row['pid']
            season = row['season']
            amount = row['amount']
            future_salaries = calculate_future_years(group, season)

            new_row = {
                'pid': pid,
                'season': season,
                'salary': amount,
                'salaries': future_salaries
            }
            new_rows.append(new_row)

    # Create a new DataFrame
    salaries_df = pd.DataFrame(new_rows)

    return ratings_df.merge(
        stats_df[
            ['pid', 'season', 'tid', 'gp', 'gs', 'min', 'usgp', 'ortg', 'drtg', 'obpm', 'dbpm', 'ows', 'dws', 'vorp',
             'ewa']],
        on=['pid', 'season'], how='left').merge(
        salaries_df[['pid', 'season', 'salary', 'salaries']], on=['pid', 'season'], how='left')
