import pandas as pd


def create_df_from_player_data(players, key, additional_fields=None):
    data = []
    for player in players:
        for item in player[key]:
            row = {'pid': player['pid']}
            if key == 'ratings':
                row['current_tid'] = player['tid']
            if additional_fields:
                row.update({field: player[field] for field in additional_fields})
            row.update(item)
            data.append(row)
    return pd.DataFrame(data).convert_dtypes(dtype_backend='pyarrow')


def player_json_to_df(r_json, keep=['ratings', 'salaries', 'stats']):
    players = r_json['players']

    if 'ratings' in keep:
        ratings_df = create_df_from_player_data(players, 'ratings', ['firstName', 'lastName', 'born'])
        ratings_df['age'] = ratings_df['season'] - ratings_df['born'].apply(lambda x: x['year'])
        ratings_df = ratings_df.drop('born', axis=1).reset_index(drop=True)

    if 'stats' in keep:
        stats_df = create_df_from_player_data(players, 'stats')
        stats_df = stats_df[(stats_df.playoffs == False)].reset_index(drop=True)

    if 'salaries' in keep:
        salaries_df = create_df_from_player_data(players, 'salaries')
        salaries_df = salaries_df.reset_index(drop=True).rename(columns={'amount': 'salary'})

        def calculate_future_salaries(row):
            pid = row['pid']
            season = row['season']
            future_years = {}
            future_rows = salaries_df[(salaries_df['pid'] == pid) & (salaries_df['season'] >= season)]
            for i, (_, future_row) in enumerate(future_rows.iterrows()):
                future_years[i] = future_row['salary']
            return future_years

        # Apply the function to each row
        salaries_df['salaries'] = salaries_df.apply(lambda row: calculate_future_salaries(row), axis=1)

    if 'stats' in keep and 'salaries' in keep:
        df = ratings_df.merge(
            stats_df[
                ['pid', 'season', 'tid', 'gp', 'gs', 'min', 'usgp', 'ortg', 'drtg', 'obpm', 'dbpm', 'ows', 'dws', 'vorp',
                 'ewa']],
            on=['pid', 'season'], how='left').merge(
            salaries_df[['pid', 'season', 'salary', 'salaries']], on=['pid', 'season'], how='left')

        return df

    if 'stats' in keep:
        return ratings_df.merge(
            stats_df[
                ['pid', 'season', 'tid', 'gp', 'gs', 'min', 'usgp', 'ortg', 'drtg', 'obpm', 'dbpm', 'ows', 'dws', 'vorp',
                 'ewa']],
            on=['pid', 'season'], how='left')

    if 'salaries' in keep:
        return ratings_df.merge(
            salaries_df[['pid', 'season', 'salary', 'salaries']], on=['pid', 'season'], how='left')

    return ratings_df
