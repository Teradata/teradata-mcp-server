from typing import List
from teradata_mcp_server.tools.plot.plot_utils import (get_plot_json_data,
                                                       get_radar_plot_json_data)
from teradatasql import TeradataConnection


def handle_generate_line_plot(conn: TeradataConnection, table_name: str, labels: str, columns: str|List[str]):
    """
    Function to generate a line plot for labels and columns.
    Columns mentioned in labels are used for x-axis and columns are used for y-axis.

    PARAMETERS:
        table_name:
            Required Argument.
            Specifies the name of the table to generate the donut plot.
            Types: str

        labels:
            Required Argument.
            Specifies the labels to be used for the line plot.
            Types: str

        columns:
            Required Argument.
            Specifies the column to be used for generating the line plot.
            Types: List[str]

    RETURNS:
        dict
    """
    # Labels must be always a string which represents a column.
    if not isinstance(labels, str):
        raise ValueError("labels must be a string representing the column name for x-axis.")

    return get_plot_json_data(conn, table_name, labels, columns)


def handle_generate_polar_area_plot(conn: TeradataConnection, table_name: str, labels: str, column: str):
    """
    Function to generate a polar area plot for labels and columns.
    Columns mentioned in labels are used as labels and column is used to plot.

    PARAMETERS:
        table_name:
            Required Argument.
            Specifies the name of the table to generate the donut plot.
            Types: str

        labels:
            Required Argument.
            Specifies the labels to be used for the line plot.
            Types: str

        column:
            Required Argument.
            Specifies the column to be used for generating the line plot.
            Types: str

    RETURNS:
        dict
    """
    # Labels must be always a string which represents a column.
    if not isinstance(labels, str):
        raise ValueError("labels must be a string representing the column name for x-axis.")

    return get_plot_json_data(conn, table_name, labels, column, 'polar')


def handle_generate_pie_plot(conn: TeradataConnection, table_name: str, labels: str, column: str):
    """
    Function to generate a pie chart plot for labels and columns.
    Columns mentioned in labels are used as labels and column is used to plot.

    PARAMETERS:
        table_name:
            Required Argument.
            Specifies the name of the table to generate the donut plot.
            Types: str

        labels:
            Required Argument.
            Specifies the labels to be used for the line plot.
            Types: str

        column:
            Required Argument.
            Specifies the column to be used for generating the line plot.
            Types: str

    RETURNS:
        dict
    """
    if not isinstance(labels, str):
        raise ValueError("labels must be a string representing the column name for x-axis.")

    return get_plot_json_data(conn, table_name, labels, column, 'pie')


def handle_generate_radar_plot(conn: TeradataConnection, table_name: str, labels: str, columns: str|List[str]):
    """
    Function to generate a radar plot for labels and columns.
    Columns mentioned in labels are used as labels and column is used to plot.

    PARAMETERS:
        table_name:
            Required Argument.
            Specifies the name of the table to generate the donut plot.
            Types: str

        labels:
            Required Argument.
            Specifies the labels to be used for the line plot.
            Types: str

        columns:
            Required Argument.
            Specifies the column to be used for generating the line plot.
            Types: str

    RETURNS:
        dict
    """
    if not isinstance(labels, str):
        raise ValueError("labels must be a string representing the column name for x-axis.")

    result = get_radar_plot_json_data(conn, table_name, labels, columns)
    return result
