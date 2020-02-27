import logging
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Output, Input
import dash_table
import psycopg2
import pandas as pd

from server import app

reference = pd.read_excel('Model parameters.xlsx')
objects = reference['Object'].tolist()
objects_to_optimize = ['T1_s3', 'T2_s3', 'T3_s3', 'T4_s3', 'T7_s3', 'T10_s2', 'Q4_s2', 'W1_s3']

logging.basicConfig(format='%(asctime)-8s [%(filename)s: %(lineno)d] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.DEBUG)
pd.options.mode.chained_assignment = None

SET_POINTS = dict({'T1_s3': 'PID12',
                   'T2_s3': 'PID13',
                   'T3_s3': 'PID14',
                   'T4_s3': 'PID15'})


def get_connection():
    fail = 0
    for attempt in range(0, 2):
        try:
            conn = psycopg2.connect(
                host="******",
                user="******",
                dbname="******",
                password="******",
                sslmode="require"
            )
            return conn

        except Exception:
            fail += 1

    if fail == 2:
        raise ConnectionError


def get_total_percent_system(df_history, df_recommendations, desired_deviation_percent):
    percents_dict = dict()

    for object in objects_to_optimize:
        df_history_copy = df_history.copy()
        df_history_copy = df_history_copy[[object]]

        df_recommendations_copy = df_recommendations.copy()
        df_recommendations_copy = df_recommendations_copy[[object]]

        df_merge = df_recommendations_copy.merge(df_history_copy, left_on=df_recommendations_copy.index,
                                                 right_on=df_history_copy.index)

        df_merge['Percent'] = abs(1 - df_merge['{}_x'.format(object)] / df_merge['{}_y'.format(object)]) * 100

        count_all = len(df_merge)
        count_good = len(df_merge.loc[df_merge['Percent'] < desired_deviation_percent])

        try:
            percent = round(count_good / count_all * 100, 2)
        except ZeroDivisionError:
            percent = 0

        percents_dict[object] = percent

    return percents_dict


def get_total_percent_setpoints(df_setpoints, df_recommendations, desired_deviation_percent):
    percents_dict = dict()

    for pid in SET_POINTS.keys():
        # обработать df_setpoints
        df_setpoints_copy = preprocess_setpoints(SET_POINTS[pid], df_setpoints, df_recommendations)

        # привести к соответствующему типу
        df_setpoints_copy['DT'] = pd.to_datetime(df_setpoints_copy['DT'])
        df_recommendations['DT'] = pd.to_datetime(df_recommendations['DT'])

        df_merge = df_recommendations[['DT', pid]].merge(df_setpoints_copy, on='DT', how='left')
        df_merge = df_merge.fillna(method='ffill')
        df_merge = df_merge.dropna()

        df_merge['Percent'] = abs(1 - df_merge['{}'.format(pid)] / df_merge['{}'.format(SET_POINTS[pid])]) * 100

        count_all = len(df_merge)
        count_good = len(df_merge.loc[df_merge['Percent'] < desired_deviation_percent])

        try:
            percent = round(count_good / count_all * 100, 2)
        except ZeroDivisionError:
            percent = 0

        percents_dict[pid] = percent

    return percents_dict


def get_processed_df_history(df_history):
    df_history['DT'] = df_history['DT'].astype(str).str.replace('T', ' ')
    df_history = df_history.round(3)
    df_history = df_history.rename(columns={'DT': 'Time stamp', 'real': 'Fact',
                                            'predict': 'Predicted', 'optimal': 'Optimum'})

    return df_history


def get_processed_df_sum(df_history):
    df_total = pd.DataFrame(df_history.sum(numeric_only=True)).T
    df_total['Measure'] = 'Сумма'
    df_total = df_total[['Measure', 'Fact', 'Predicted', 'Optimum']]
    df_total = df_total.round(3)

    return df_total


def preprocess_setpoints(pid, df_setpoints, df_optimal_points):
    # обработать определенный pid - берем колонку
    df_setpoints = df_setpoints[[pid]]
    df_setpoints.dropna(inplace=True)
    df_setpoints.reset_index(inplace=True)

    # вычленяем необходимые даты по пидам из df_optimal
    start_date = df_optimal_points['DT'].head(1).dt.strftime('%Y-%m-%d %H:%M:%S').values[0]
    end_date = df_optimal_points['DT'].tail(1).dt.strftime('%Y-%m-%d %H:%M:%S').values[0]

    # уставки в пределах искомых значений
    df_setpoints_cut = df_setpoints.loc[(df_setpoints['DT'] > start_date) & (df_setpoints['DT'] <= end_date)]

    # но уставки есть и за временными диапазонами
    df_setpoints_start = df_setpoints.loc[df_setpoints['DT'] < start_date]

    df_setpoints_start['DT'] = start_date

    if not df_setpoints_start.empty:
        df_setpoints_start = df_setpoints_start.tail(1).copy()

    # соединить начало и конец
    df_setpoints_with_start = pd.concat([df_setpoints_start, df_setpoints_cut]).reset_index(drop=True)

    # а нужно еще конец сделать
    df_setpoints_end = df_setpoints_with_start.tail(1).copy()
    df_setpoints_end['DT'] = end_date

    # соединить начало и конец
    df_setpoints = pd.concat([df_setpoints_with_start, df_setpoints_end]).reset_index(drop=True)

    df_setpoints.dropna(inplace=True)

    return df_setpoints


layout = html.Div([
    # main
    html.Div([

        # date picker block
        html.Div([
            html.Div([
                html.Span('Select reporting period: ', className='text'),
                dcc.DatePickerRange(
                    id='datepicker-component',
                    start_date_placeholder_text='Beginning of period',
                    end_date_placeholder_text='End of period',
                    with_portal=True,
                    show_outside_days=True,
                    display_format='D MMMM Y',
                )
            ], className='left'),

            html.Div([
                html.Span('Select percent deviation: ', className='text'),
                dcc.Input(
                    id="desired-deviation-percent", type="number",
                    min=0, max=100, step=1, value=5, debounce=True
                ),
                html.Span(' %', className='text'),
            ], className='right')
        ], className='admin-input'),

        html.Div([
            html.Div([
                html.Div(id='total-percent-system', className='text'),
            ], className='left'),
            html.Div([
                html.Div(id='total-percent-setpoints', className='text'),
            ], className='right')
        ], className='total-messages'),

        # yields
        html.Div([
            html.Div([
                html.Div(id='table-history', className='table-component'),
                html.Div(id='table-sum')
            ], className='left'),
            html.Div([
                html.Div(id='figure-history', className='figure')
            ], className='right')
        ], className='yields'),

        # main dropdown
        html.Div([
            html.Span('Display deviation percentage by parameter:', className='text'),
            html.Div([
                dcc.Dropdown(
                    id='dropdown-component',
                    placeholder='Parameter',
                    options=[
                        {'label': 'T1 – Temperature in the 1st zone', 'value': 'T1_s3'},
                        {'label': 'T2 – Temperature in the 2nd zone', 'value': 'T2_s3'},
                        {'label': 'T3 – Temperature in the 3rd zone', 'value': 'T3_s3'},
                        {'label': 'T4 – Temperature in the 4th zone', 'value': 'T4_s3'},
                        {'label': 'T7_s3 – Temperature of sulphonated water', 'value': 'T7_s3'},
                        {'label': 'T10_s2 – Temperature of pulp press water', 'value': 'T10_s2'},
                        {'label': 'Q4_s2 – pH of sulphonated water', 'value': 'Q4_s2'},
                        {'label': 'W1_s3 – Beet consumption', 'value': 'W1_s3'},
                    ],
                    value='T2_s3',
                    clearable=False,
                    searchable=False)
            ],
                style=dict(
                    width='50%',
                    textAlign='left',
                )
            )
        ], className='dropdown'),

        html.Div([
            html.Div([
                html.Div([
                    html.Div(id='dropdown-percent-system', className='text'),
                ], className='left'),
                html.Div([
                    html.Div(id='dropdown-percent-setpoints', className='text'),
                ], className='right')
            ], className='messages'),
            html.Div(id='figure-dropdown', className='figure')
        ], className='set-points')

    ], className='adminpage')
])


@app.callback(
    [
        Output('total-percent-system', 'children'),
        Output('dropdown-percent-system', 'children'),
    ],
    [
        Input('datepicker-component', 'start_date'),
        Input('datepicker-component', 'end_date'),
        Input('desired-deviation-percent', 'value'),
        Input('dropdown-component', 'value')
    ]
)
def update_system_percents(start_date, end_date, desired_deviation_percent, dropdown_value):
    if start_date and end_date:
        end_date += ' 23:50:00'

        conn, cursor = None, None
        try:
            conn = get_connection()
        except ConnectionError:
            return ['Нет связи с Postgres',
                    'Нет связи с Postgres']
        else:
            cursor = conn.cursor()

            sql_history = """SELECT "DT_msk", "Object", "Value"
                             FROM public.history30min
                             WHERE "DT_msk" >= '{}' 
                             AND "DT_msk" <= '{}'""".format(start_date, end_date)
            cursor.execute(sql_history, conn)
            df_history = pd.DataFrame(cursor.fetchall(), columns=['DT_msk', 'Object', 'Value'])
            if not df_history.empty:
                df_history = df_history.pivot_table(values='Value', index='DT_msk', columns='Object')
            else:
                return ['No data for the indicated dates', 'No data for the indicated dates']

            sql_recommendations = """SELECT "DT", "Object", "Value"
                             FROM public.recommendations30min
                             WHERE "DT" >= '{}' 
                             AND "DT" <= '{}'""".format(start_date, end_date)
            cursor.execute(sql_recommendations, conn)
            df_recommendations = pd.DataFrame(cursor.fetchall(), columns=['DT', 'Object', 'Value'])
            if not df_recommendations.empty:
                df_recommendations = df_recommendations.pivot_table(values='Value', index='DT', columns='Object')
            else:
                return ['No data for the indicated dates', 'No data for the indicated dates']

            percents_dict = get_total_percent_system(df_history, df_recommendations, desired_deviation_percent)

            total_percent_system_temp = 0
            for value in percents_dict.values():
                total_percent_system_temp += value
            total_percent_system = round(total_percent_system_temp / len(percents_dict), 2)
            message1 = 'Optimum - System: {} %'.format(total_percent_system)

            dropdown_percent_system = percents_dict[dropdown_value]
            message2 = 'Optimum - System ({}): {} %'.format(dropdown_value, dropdown_percent_system)

            return [message1, message2]

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.commit()
                conn.close()
    else:
        return [
            'Enter dates', 'Enter dates'
        ]


@app.callback(
    [
        Output('total-percent-setpoints', 'children'),
        Output('dropdown-percent-setpoints', 'children'),
    ],
    [
        Input('datepicker-component', 'start_date'),
        Input('datepicker-component', 'end_date'),
        Input('desired-deviation-percent', 'value'),
        Input('dropdown-component', 'value')
    ]
)
def update_setpoints_percents(start_date, end_date, desired_deviation_percent, dropdown_value):
    if start_date and end_date:
        end_date += ' 23:50:00'

        conn, cursor = None, None
        try:
            conn = get_connection()

        except ConnectionError:
            return ['Нет связи с Postgres',
                    'Нет связи с Postgres']

        else:
            cursor = conn.cursor()

            sql_query = """SELECT "DT_msk", "Object", "Value"
                           FROM public.setpoints"""
            cursor.execute(sql_query, conn)
            df_setpoints = pd.DataFrame(cursor.fetchall(), columns=['DT', 'Object', 'Value'])
            df_setpoints = df_setpoints.pivot_table(values='Value', index='DT', columns='Object')

            sql_query = """SELECT "DT", "Object", "Value"
                           FROM public.recommendations30min
                           WHERE "DT" >= '{}'
                           AND "DT" <= '{}'""".format(start_date, end_date)

            cursor.execute(sql_query, conn)
            df_recommendations = pd.DataFrame(cursor.fetchall(), columns=['DT', 'Object', 'Value'])
            if not df_recommendations.empty:
                df_recommendations = df_recommendations.pivot_table(values='Value', index='DT', columns='Object')
                df_recommendations.reset_index(inplace=True)
            else:
                return ['No data for the indicated dates', 'No data for the indicated dates']

            percents_dict = get_total_percent_setpoints(df_setpoints, df_recommendations, desired_deviation_percent)

            total_percent_setpoints_temp = 0
            for value in percents_dict.values():
                total_percent_setpoints_temp += value
            total_percent_setpoints = round(total_percent_setpoints_temp / len(percents_dict), 2)
            message1 = 'Optimum - PID: {} %'.format(total_percent_setpoints)

            if dropdown_value in SET_POINTS.keys():
                dropdown_percent_setpoints = percents_dict[dropdown_value]
                message2 = 'Optimum - PID ({}): {} %'.format(dropdown_value, dropdown_percent_setpoints)
            else:
                message2 = 'There is no PID controller for this sensor'

            return [message1, message2]

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.commit()
                conn.close()
    else:
        return [
            'Enter dates', 'Enter dates'
        ]


@app.callback([
    Output('table-history', 'children'),
    Output('table-sum', 'children'),
    Output('figure-history', 'children')],
    [Input('datepicker-component', 'start_date'),
     Input('datepicker-component', 'end_date')])
def update_records(start_date, end_date):
    if start_date and end_date:
        end_date += ' 23:50:00'

        conn = None
        cursor = None
        try:
            conn = psycopg2.connect(
                host="******",
                user="******",
                dbname="******",
                password="******",
                sslmode="require"
            )

            cursor = conn.cursor()

            sql_fact = """SELECT "DT", "fact"
                          FROM public.fact30min
                          WHERE "DT" >= '{}' 
                          AND "DT" <= '{}'""".format(start_date, end_date)
            cursor.execute(sql_fact, conn)
            records_fact = cursor.fetchall()

            sql_predictions = """SELECT "DT", "yield", "optimal"
                               FROM public.predictions30min
                               WHERE "DT" >= '{}' 
                               AND "DT" <= '{}'""".format(start_date, end_date)
            cursor.execute(sql_predictions, conn)
            records_predictions = cursor.fetchall()

        finally:
            if conn:
                conn.commit()
                cursor.close()
                conn.close()

        # создадим датафреймы
        df_fact = pd.DataFrame(records_fact, columns=['DT', 'fact'])
        df_predictions = pd.DataFrame(records_predictions, columns=['DT', 'predict', 'optimal'])

        if df_fact.empty | df_predictions.empty:
            return [
                html.H6(''),
                html.H6(''),
                html.H6(''),
            ]

        df_total = df_fact.merge(df_predictions, left_on='DT', right_on='DT')
        df_total = df_total[['DT', 'fact', 'predict', 'optimal']]
        df_total['DT'] = df_total['DT'].astype(str).str.replace('T', ' ')
        df_total = df_total.rename(columns={'DT': 'Time stamp', 'fact': 'Fact',
                                            'predict': 'Predicted', 'optimal': 'Optimum'})
        df_total = df_total[['Time stamp', 'Fact', 'Predicted', 'Optimum']]
        df_total['Fact'] = df_total['Fact'] * 1.7
        df_total['Predicted'] = df_total['Predicted'] * 1.7
        df_total['Optimum'] = df_total['Optimum'] * 1.7
        df_total['Optimum'] = df_total['Optimum'] - 1
        df_total = df_total.round(3)

        df_sum = pd.DataFrame(df_total.mean(numeric_only=True)).T
        df_sum['Measure'] = 'Mean'
        df_sum = df_sum[['Measure', 'Fact', 'Predicted', 'Optimum']]
        df_sum = df_sum.round(3)

        table_history = dash_table.DataTable(
            data=df_total.to_dict('records'),
            columns=[{"name": i, "id": i} for i in df_total.columns],
            style_cell={'font_family': 'sans-serif', 'font_size': '16px', 'textAlign': 'center'},
            style_table={'overflowY': 'auto', 'maxHeight': '390px'},
            style_data_conditional=[
                {'if': {'column_id': 'Fact'}, 'backgroundColor': '#ffded9'},
                {'if': {'column_id': 'Predicted'}, 'backgroundColor': '#c1ccb6'},
                {'if': {'column_id': 'Optimum'}, 'backgroundColor': '#b3e8e8'}
            ]
        )

        table_sum = dash_table.DataTable(
            data=df_sum.to_dict('records'),
            columns=[{"name": i, "id": i} for i in df_sum.columns],
            style_cell={'font_family': 'sans-serif', 'font_size': '16px', 'textAlign': 'center'},
            style_table={'overflowY': 'auto', 'maxHeight': '450px'},
            style_data_conditional=[
                {'if': {'column_id': 'Fact'}, 'backgroundColor': '#ffded9'},
                {'if': {'column_id': 'Predicted'}, 'backgroundColor': '#c1ccb6'},
                {'if': {'column_id': 'Optimum'}, 'backgroundColor': '#b3e8e8'}
            ]
        )

        data = [
            dict(
                type="scatter",
                mode="lines+markers",
                name="Fact",
                x=df_total['Time stamp'],
                y=df_total['Fact'],
                line=dict(shape="spline", smoothing=1, width=2, color="#fac1b7"),
                marker=dict(symbol="diamond-open"),
            ),
            dict(
                type="scatter",
                mode="lines+markers",
                name="Predicted",
                x=df_total['Time stamp'],
                y=df_total['Predicted'],
                line=dict(shape="spline", smoothing=1, width=2, color="#a9bb95"),
                marker=dict(symbol="diamond-open"),
            ),
            dict(
                type="scatter",
                mode="lines+markers",
                name="Optimum",
                x=df_total['Time stamp'],
                y=df_total['Optimum'],
                line=dict(shape="spline", smoothing=1, width=2, color="#92d8d8"),
                marker=dict(symbol="diamond-open"),
            ),
        ]

        figure = dcc.Graph(figure=dict(data=data))

        return table_history, table_sum, figure
    else:
        return [
            'Enter dates', 'Enter dates', 'Enter dates'
        ]


@app.callback(Output('figure-dropdown', 'children'),
              [Input('datepicker-component', 'start_date'),
               Input('datepicker-component', 'end_date'),
               Input('dropdown-component', 'value')])
def update_figure_dropdown(start_date, end_date, dropdown_object):
    if start_date and end_date:
        end_date += ' 23:50:00'

        conn, cursor = None, None
        try:
            conn = get_connection()
        except ConnectionError:
            return ['Нет связи с Postgres']
        else:

            cursor = conn.cursor()

            sql_query = """SELECT "DT_msk", "Object", "Value"
                           FROM public.history30min
                           WHERE "DT_msk" >= '{}'
                             AND "DT_msk" <= '{}'
                             AND "Object" = '{}'""".format(start_date, end_date, dropdown_object)
            cursor.execute(sql_query, conn)
            df_history = pd.DataFrame(cursor.fetchall(), columns=['DT_msk', 'Object', 'Value'])
            df_history = df_history.sort_values(by='DT_msk')

            sql_query = """SELECT "DT", "Object", "Value"
                           FROM public.recommendations30min
                           WHERE "DT" >= '{}'
                             AND "DT" <= '{}'
                             AND "Object" = '{}'""".format(start_date, end_date, dropdown_object)
            cursor.execute(sql_query, conn)
            df_recommendations = pd.DataFrame(cursor.fetchall(), columns=['DT', 'Object', 'Value'])

            if df_history.empty | df_recommendations.empty:
                return ''

            data_plot = [
                dict(
                    type="scatter",
                    mode="lines+markers",
                    name="Fact",
                    x=df_history['DT_msk'],
                    y=df_history['Value'],
                    line=dict(shape="spline", smoothing=1, width=2, color="#849E68"),
                    marker=dict(symbol="diamond-open"),
                ),
                dict(
                    type="scatter",
                    mode="lines+markers",
                    name="Recommendation",
                    x=df_recommendations['DT'],
                    y=df_recommendations['Value'],
                    line=dict(shape="spline", smoothing=1, width=2, color="#59C3C3"),
                    marker=dict(symbol="diamond-open"),
                ),
            ]

            if dropdown_object in ['T1_s3', 'T2_s3', 'T3_s3', 'T4_s3']:
                sql_query = """SELECT "DT_msk", "Object", "Value"
                               FROM public.setpoints
                               WHERE "Object" = '{}'""".format(SET_POINTS[dropdown_object])
                cursor.execute(sql_query, conn)
                df_setpoints = pd.DataFrame(cursor.fetchall(), columns=['DT', 'Object', 'Value'])
                df_setpoints = df_setpoints.pivot_table(values='Value', index='DT', columns='Object')
                df_history.rename(columns={'DT_msk': 'DT'}, inplace=True)
                df_setpoints = preprocess_setpoints(SET_POINTS[dropdown_object], df_setpoints, df_history)

                if not df_setpoints.empty:
                    data_plot.append(
                        dict(
                            type="scatter",
                            mode="lines+markers",
                            name="Setpoint",
                            x=df_setpoints['DT'],
                            y=df_setpoints[SET_POINTS[dropdown_object]],
                            line=dict(shape="hv", width=2, color="#F9ADA0"),
                            marker=dict(symbol="diamond-open"),
                        ))

            figure = dcc.Graph(figure=dict(data=data_plot))

            return figure

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.commit()
                conn.close()
    else:
        return [
            ''
        ]
