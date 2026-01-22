import json
import logging

from teradata_mcp_server.tools.utils import create_response

# Define the logger.
logger = logging.getLogger("teradata_mcp_server")


def get_plot_json_data(conn, table_name, labels, columns, chart_type='line'):
    """
    Helper function to fetch data from a Teradata table and formats it for plotting.
    Right now, designed only to support line plots from chart.js .
    """
    # Define the colors first.
    colors = ['rgb(75, 192, 192)', '#99cbba', '#d7d0c4', '#fac778', '#e46c59', '#F9CB99', '#280A3E', '#F2EDD1', '#689B8A']
    # Chart properties. Every chart needs different property for colors.
    chart_properties = {'line': 'borderColor', 'polar': 'backgroundColor', 'pie': 'backgroundColor'}

    columns = [columns] if isinstance(columns, str) else columns
    sql = "select {labels}, {columns} from {table_name} order by {labels}".format(
          labels=labels, columns=','.join(columns), table_name=table_name)

    # Prepare the statement.
    with conn.cursor() as cur:
        recs = cur.execute(sql).fetchall()

    # Define the structure of the chart data. Below is the structure expected by chart.js
    # {
    #     labels: labels,
    #     datasets: [{
    #         label: 'My First Dataset',
    #         data: [65, 59, 80, 81, 56, 55, 40],
    #         fill: false,
    #         borderColor: 'rgb(75, 192, 192)',
    #         tension: 0.1
    #     }]
    # }
    labels = []
    datasets = [[] for _ in range(len(columns))]
    for rec in recs:
        labels.append(rec[0])
        for i_, val in enumerate(rec[1:]):
            datasets[i_].append(val)

    # Prepare the datasets for chart.js
    datasets_ = []
    for i, dataset in enumerate(datasets):
        datasets_.append({
            'label': columns[i],
            'data': dataset,
            'borderColor': colors[i],
            'fill': False
        })

    # For polar plot, every dataset needs different colors.
    if chart_type in ('polar', 'pie'):
        for _i, dataset in enumerate(datasets_):
            # Remove borderColor and add backgroundColor
            dataset.pop('borderColor', None)
            dataset['backgroundColor'] = colors

    chart_data = {
        "labels": [str(L) for L in labels],
        "datasets": datasets_
    }
    logger.debug("Chart data: %s", json.dumps(chart_data, indent=2))

    return create_response(data=chart_data, metadata={
            "tool_description": f"chart js {chart_type} plot data",
            "table_name": table_name,
            "labels": labels,
            "columns": columns
        })


def get_radar_plot_json_data(conn, table_name, labels, columns):
    """
    Helper function to fetch data from a Teradata table and formats it for plotting.
    Right now, designed only to support line plots from chart.js .
    """
    logger.debug("Tool: get_json_data_for_plotting")
    # Define the colors first.
    border_colors = [
        'rgb(255, 99, 132)',
        'rgb(54, 162, 235)',
        '#d7d0c4',
        '#fac778',
        '#e46c59',
        '#F9CB99',
        '#280A3E',
        '#F2EDD1',
        '#689B8A'
    ]
    background_colors = [
        'rgba(255, 99, 132, 0.2)',
        'rgba(54, 162, 235, 0.2)',
        'rgb(222, 232, 206, 0.2)',
        'rgb(187, 102, 83, 0.2)',
        'rgb(240, 139, 81, 0.2)',
        'rgb(255, 248, 232, 0.2)'
    ]
    point_background_color = [
        'rgba(255, 99, 132)',
        'rgba(54, 162, 235)',
        'rgb(222, 232, 206)',
        'rgb(187, 102, 83)',
        'rgb(240, 139, 81)',
        'rgb(255, 248, 232)'
    ]

    columns = [columns] if isinstance(columns, str) else columns
    sql = "select {labels}, {columns} from {table_name} order by {labels}".format(
          labels=labels, columns=','.join(columns), table_name=table_name)

    # Execute the SQL query

    # Prepare the statement.
    with conn.cursor() as cur:
        recs = cur.execute(sql).fetchall()

    labels = []
    datasets = [[] for _ in range(len(columns))]
    for rec in recs:
        labels.append(rec[0])
        for i_, val in enumerate(rec[1:]):
            datasets[i_].append(val)

    # Prepare the datasets for chart.js
    datasets_ = []
    for i, dataset in enumerate(datasets):
        datasets_.append({
            'label': columns[i],
            'data': dataset,
            'fill': True,
            "backgroundColor": background_colors[i % len(background_colors)],
            'borderColor': border_colors[i % len(border_colors)],
            "pointBackgroundColor": point_background_color[i % len(point_background_color)],
            "pointBorderColor": '#fff',
            "pointHoverBackgroundColor": '#fff',
            "pointHoverBorderColor": point_background_color[i % len(point_background_color)]
        })

    chart_data = {
        "labels": [str(L) for L in labels],
        "datasets": datasets_
    }
    logger.debug("Chart data: %s", json.dumps(chart_data, indent=2))

    return create_response(data=chart_data, metadata={
            "tool_description": "chart js radar plot data",
            "table_name": table_name,
            "labels": labels,
            "columns": columns
        })
