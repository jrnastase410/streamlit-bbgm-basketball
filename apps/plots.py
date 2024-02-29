import plotly.graph_objects as go
import numpy as np

def player_plot(pid, df):
    # Filter the dataframe for the specific pid
    df_filtered = df[df.pid == pid]

    # Retrieve the player's first name and last name
    player = df_filtered['player'].values[0]

    # Create the title
    title = f'{player}'

    # Extract the rating, value, and bounds data
    rating_data = df_filtered['rating_prog'].values[0]
    rating_upper_data = df_filtered['rating_upper_prog'].values[0]
    rating_lower_data = df_filtered['rating_lower_prog'].values[0]
    cap_value_data = df_filtered['cap_value_prog'].values[0]
    cap_hits_data = df_filtered['cap_hits'].values[0]
    cap_filled_data = df_filtered['cap_hits_filled'].values[0]
    surplus_data = df_filtered['surplus_2_progs'].values[0]

    # Remove null values
    cap_hits_data = {key: val for key, val in cap_hits_data.items() if val != None}
    cap_filled_data = {key: val for key, val in cap_filled_data.items() if key not in cap_hits_data}

    # Create the plot for ratings
    fig = go.Figure()

    bar_width = 0.4

    # Rating Upper Bound
    fig.add_trace(
        go.Scatter(
            x=list(rating_upper_data.keys()),
            y=list(rating_upper_data.values()),
            name='Upper Bound',
            mode='lines',
            line=dict(width=0),
            hoverinfo='skip',
            showlegend=False,
        )
    )

    # Rating Lower Bound
    fig.add_trace(
        go.Scatter(
            x=list(rating_lower_data.keys()),
            y=list(rating_lower_data.values()),
            name='Lower Bound',
            mode='none',
            fill='tonexty',
            hoverinfo='skip',
            fillcolor='rgba(255, 90, 95, 0.2)',
            showlegend=False,
        )
    )

    # Rating
    fig.add_trace(
        go.Scatter(
            x=list(rating_data.keys()),
            y=list(rating_data.values()),
            name='Rating',
            line=dict(
                color='rgb(255, 90, 95)'
            ),
            customdata=np.stack((list(rating_lower_data.values()), list(rating_upper_data.values())), axis=-1),
            hovertemplate=
            '<b>Year</b>: %{x}<br>' +
            '<b>Rating</b>: %{y:.1f}<br>' +  # Round to 1 decimal place
            '<b>Lower Bound</b>: %{customdata[0]:.1f}<br>' +  # Round to 1 decimal place
            '<b>Upper Bound</b>: %{customdata[1]:.1f}<br>',  # Round to 1 decimal place
        )
    )

    # Surplus Value
    fig.add_trace(
        go.Scatter(
            x=list(surplus_data.keys()),
            y=list(surplus_data.values()),
            name='Value',
            line=dict(
                color='rgb(0, 90, 95)'
            ),
            yaxis='y2'
        )
    )

    # Cap Hits
    fig.add_trace(
        go.Bar(
            x=[x + 0.2 for x in list(cap_hits_data.keys())],
            y=list(cap_hits_data.values()),
            name='Cap Hit',
            yaxis='y2',
            width=bar_width,
            marker=dict(
                color='rgb(252,100,45)'
            ),
            text=[f'{val * 100:.1f}%' for val in list(cap_hits_data.values())],
            textposition='outside',
            textfont=dict(
                color='rgb(252,100,45)',
                size=14,
            ),
        )
    )

    # Cap Hits (Projected)
    fig.add_trace(
        go.Bar(
            x=[x + 0.2 for x in list(cap_filled_data.keys())],
            y=list(cap_filled_data.values()),
            name='Cap Hit',
            yaxis='y2',
            width=bar_width,
            marker=dict(
                color='rgba(252,100,45,0.5)'
            ),
            text=[f'{val * 100:.1f}%' for val in list(cap_filled_data.values())],
            textposition='outside',
            textfont=dict(
                color='rgb(252,100,45)',
                size=14,
            ),
            showlegend=False,
        )
    )

    # Cap Values
    fig.add_trace(
        go.Bar(
            x=[x - 0.2 for x in list(cap_value_data.keys())],
            y=list(cap_value_data.values()),
            name='Cap Value',
            yaxis='y2',
            width=bar_width,
            marker=dict(
                color='rgb(0, 166, 153)'
            ),
            text=[f'{val * 100:.1f}%' for val in list(cap_value_data.values())],
            textposition='outside',
            textfont=dict(
                color='rgb(0, 166, 153)',
                size=14,
            ),
        )
    )

    # Update the plot title
    fig.update_layout(
        template='simple_white',
        title=title,
        barmode='group',
        yaxis=dict(
            range=[0, 100],
            showgrid=False,
            showticklabels=True,
        ),
        yaxis2=dict(
            range=[0, 1],
            overlaying='y',
            side='right',
            showgrid=False,
            showticklabels=False,
        ),
    )
    return fig