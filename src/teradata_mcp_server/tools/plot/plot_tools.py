from teradatasql import TeradataConnection

from teradata_mcp_server.tools.plot.plot_utils import get_plot_json_data, get_radar_plot_json_data


def handle_plot_line_chart(conn: TeradataConnection, table_name: str, labels: str, columns: str | list[str]):
    """
    Generate a line chart that reads directly from a Teradata table — do NOT use base_readQuery to pre-fetch data first. Specify the table in `table_name`, the x-axis column in `labels` (typically a date or time field), and one or more y-axis numeric columns in `columns`. Use for time-series, trend lines, or sequential data. Do NOT use for proportional category breakdowns — use plot_pie_chart or plot_polar_chart. Do NOT use for multi-dimensional spider comparisons — use plot_radar_chart.

    PARAMETERS:
        table_name:
            Required Argument.
            Specifies the name of the table to generate the line chart.
            Types: str

        labels:
            Required Argument.
            Specifies the x-axis column (typically date or time).
            Types: str

        columns:
            Required Argument.
            Specifies the y-axis numeric column(s) for the line chart.
            Types: List[str]

    RETURNS:
        dict
    """
    # Labels must be always a string which represents a column.
    if not isinstance(labels, str):
        raise ValueError("labels must be a string representing the column name for x-axis.")

    return get_plot_json_data(conn, table_name, labels, columns)


def handle_plot_polar_chart(conn: TeradataConnection, table_name: str, labels: str, column: str):
    """
    Generate a polar area chart that reads directly from a Teradata table — do NOT use base_readQuery first. Specify the table in `table_name`, the category column in `labels`, and the numeric value column in `column`. Use when the user explicitly asks for a polar chart or polar area chart. For standard pie-style breakdowns, use plot_pie_chart instead.

    PARAMETERS:
        table_name:
            Required Argument.
            Specifies the name of the table to generate the polar chart.
            Types: str

        labels:
            Required Argument.
            Specifies the category column for labels.
            Types: str

        column:
            Required Argument.
            Specifies the numeric value column for the polar chart.
            Types: str

    RETURNS:
        dict
    """
    # Labels must be always a string which represents a column.
    if not isinstance(labels, str):
        raise ValueError("labels must be a string representing the column name for x-axis.")

    return get_plot_json_data(conn, table_name, labels, column, "polar")


def handle_plot_pie_chart(conn: TeradataConnection, table_name: str, labels: str, column: str):
    """
    Generate a pie chart that reads directly from a Teradata table — do NOT use base_readQuery to pre-fetch or aggregate data first. Specify the table in `table_name`, the category column in `labels`, and the numeric value column in `column`. Use when the user asks for proportions, shares, or how a total breaks down by category. For polar area charts, use plot_polar_chart. For time-series trends, use plot_line_chart.

    PARAMETERS:
        table_name:
            Required Argument.
            Specifies the name of the table to generate the pie chart.
            Types: str

        labels:
            Required Argument.
            Specifies the category column for labels.
            Types: str

        column:
            Required Argument.
            Specifies the numeric value column for the pie chart.
            Types: str

    RETURNS:
        dict
    """
    if not isinstance(labels, str):
        raise ValueError("labels must be a string representing the column name for x-axis.")

    return get_plot_json_data(conn, table_name, labels, column, "pie")


def handle_plot_radar_chart(conn: TeradataConnection, table_name: str, labels: str, columns: str | list[str]):
    """
    Generate a radar chart (spider chart or web chart) that reads directly from a Teradata table — do NOT use base_readQuery to pre-fetch data first. Specify the table in `table_name`, the category column in `labels`, and one or more value columns in `columns`. Use when the user asks for a spider chart, radar chart, web chart, or multi-dimensional comparison across categories. For time-series or trend data, use plot_line_chart instead.

    PARAMETERS:
        table_name:
            Required Argument.
            Specifies the name of the table to generate the radar chart.
            Types: str

        labels:
            Required Argument.
            Specifies the category column for labels.
            Types: str

        columns:
            Required Argument.
            Specifies the value column(s) for the radar chart.
            Types: str | List[str]

    RETURNS:
        dict
    """
    if not isinstance(labels, str):
        raise ValueError("labels must be a string representing the column name for x-axis.")

    result = get_radar_plot_json_data(conn, table_name, labels, columns)
    return result
