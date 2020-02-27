import datetime
import dash_table
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Output, Input
from dash.exceptions import PreventUpdate
import pandas as pd
import logging

from server import app
from constants import MOSCOW_TIMEZONE, percent_FROM, percent_TO, SYNC_TIME_MINUTE

DESCRIPTION = pd.read_excel('data/Model parameters.xlsx')


def get_conditional_style(df, percent_from, percent_to):
    data = [{'if': {'column_id': 'Параметр'}, 'textAlign': 'left'},
            {'if': {'column_id': 'Регулировка'}, 'textAlign': 'center'},
            {'if': {'column_id': 'Значение'}, 'textAlign': 'left'},
            ]

    for index, row in df.iterrows():
        configs = dict()
        system, optimal = row['Текущее'], row['Рекомендуемое']

        try:
            percent = abs(system * 100 / optimal - 100)
        except ZeroDivisionError:
            percent = 100

        if percent < percent_from:
            color = '#C0D2B2'
        elif percent_from <= percent < percent_to:
            color = '#FFD792'
        else:
            color = '#FF8A5D'

        configs['if'] = {'row_index': index}
        configs['backgroundColor'] = color

        data.append(configs)

    return data


layout = html.Div([
    html.Div([
        html.Div([
            html.Div(id='time', className='time')
        ], className='left'),
        html.Div([
            html.Div(id='reporting-time', className='reporting-time')
        ], className='right')
    ], className='times'),

    html.Div(id='table-mutable'),
    html.Div([
        dcc.Checklist(id='checklist', options=[{'label': 'Display all process parameters', 'value': 'Fire'}])
    ], className='checklist'),
    html.Div(id='table-immutable', className='table-immutable'),
    html.Div([
        html.Div([
            html.Div(id='predict', className='predict')
        ], className='left'),
        html.Div([
            html.Div(id='optimal', className='optimal')
        ], className='right')
    ], className='metrics'),
    html.Div([
        html.Div(id='figure-yields')
    ], className='figure'),

    dcc.Interval(id='interval', n_intervals=0, interval=1 * 1000),
    html.Div(id='intermediate-table', style={'display': 'none'}),
], className='operatorpage')


@app.callback(Output('time', 'children'),
              [Input('interval', 'n_intervals')])
def update_time(n):
    time = datetime.datetime.now(MOSCOW_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")

    return [html.Span('Сurrent time: ' + time)]


@app.callback([Output('table-mutable', 'children'),
               Output('reporting-time', 'children')],
              [Input('interval', 'n_intervals')])
def update_table_mutable(n):
    if n == 0:
        logging.debug('UPDATE TABLE n == 0')
        try:
            df_mutable = pd.read_csv('data/parameters.csv')
        except FileNotFoundError:
            logging.info(FileNotFoundError)
        else:
            df_mutable = df_mutable.loc[df_mutable['Текущее'] != df_mutable['Рекомендуемое']].round(3)
            reporting_time = 'Reporting time: {}'.format(df_mutable['DT'].tail(1).values[0])
            df_mutable = df_mutable.merge(DESCRIPTION, on='Параметр', how='left')
            df_mutable = df_mutable[['Параметр', 'Значение', 'Текущее', 'Рекомендуемое', 'Регулировка']]

            table_mutable = dash_table.DataTable(
                style_cell_conditional=get_conditional_style(df_mutable, percent_FROM, percent_TO),
                columns=[{"name": i, "id": i} for i in df_mutable.columns],
                data=df_mutable.to_dict('records'),
                style_header={'backgroundColor': 'whitesmoke', 'fontWeight': 'bold', 'border': '1px solid whitesmoke'},
                style_cell={'font_family': 'sans-serif', 'font_size': '16px'},
                style_data={'border': '1px solid white'})

            return table_mutable, reporting_time

    else:
        time_moment = datetime.datetime.now(MOSCOW_TIMEZONE)
        minutes, seconds = int(time_moment.strftime("%M")), int(time_moment.strftime("%S"))

        if (minutes - SYNC_TIME_MINUTE) % 30 == 1 and (10 <= seconds <= 20):
            logging.debug('UPDATE TABLE n > 0 IF CASE')
            try:
                df_mutable = pd.read_csv('data/parameters.csv')
            except FileNotFoundError:
                logging.info(FileNotFoundError)
            else:
                df_mutable = df_mutable.loc[df_mutable['Текущее'] != df_mutable['Рекомендуемое']].round(3)
                reporting_time = 'Reporting time: {}'.format(df_mutable['DT'].tail(1).values[0])
                df_mutable = df_mutable.merge(DESCRIPTION, on='Параметр', how='left')
                df_mutable = df_mutable[['Параметр', 'Значение', 'Текущее', 'Рекомендуемое', 'Регулировка']]

                table_mutable = dash_table.DataTable(
                    style_cell_conditional=get_conditional_style(df_mutable, percent_FROM, percent_TO),
                    columns=[{"name": i, "id": i} for i in df_mutable.columns],
                    data=df_mutable.to_dict('records'),
                    style_header={'backgroundColor': 'whitesmoke', 'fontWeight': 'bold',
                                  'border': '1px solid whitesmoke'},
                    style_cell={'font_family': 'sans-serif', 'font_size': '16px'},
                    style_data={'border': '1px solid white'})

                return table_mutable, reporting_time
        else:
            raise PreventUpdate


@app.callback(Output('intermediate-table', 'children'),
              [Input('interval', 'n_intervals')])
def update_table_immutable(n):
    if n == 0:
        try:
            df_immutable = pd.read_csv('data/parameters.csv')
        except FileNotFoundError:
            logging.info(FileNotFoundError)
        else:
            df_immutable = df_immutable.loc[df_immutable['Текущее'] == df_immutable['Рекомендуемое']].round(3)
            df_immutable = df_immutable.merge(DESCRIPTION, on='Параметр', how='left')
            df_immutable = df_immutable[['Параметр', 'Значение', 'Текущее']]

            table_immutable = dash_table.DataTable(
                style_cell_conditional=[{'if': {'column_id': 'Параметр'}, 'textAlign': 'left'},
                                        {'if': {'column_id': 'Значение'}, 'textAlign': 'left'},
                                        {'if': {'column_id': 'Значение'}, 'width': '20px'}
                                        ],
                # style_cell_conditional=get_conditional_style(df_immutable, percent_FROM, percent_TO),
                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': 'rgb(248, 248, 248)'
                    }
                ],
                style_header={
                    'backgroundColor': 'rgb(230, 230, 230)',
                    'fontWeight': 'bold'
                },
                columns=[{"name": i, "id": i} for i in df_immutable.columns],
                data=df_immutable.to_dict('records'),
                # style_header={'backgroundColor': 'whitesmoke', 'fontWeight': 'bold', 'border': '1px solid whitesmoke'},
                style_cell={'font_family': 'sans-serif', 'font_size': '16px'},
                style_data={'border': '1px solid white'})

            return table_immutable

    else:
        time_moment = datetime.datetime.now(MOSCOW_TIMEZONE)
        minutes, seconds = int(time_moment.strftime("%M")), int(time_moment.strftime("%S"))

        if (minutes - SYNC_TIME_MINUTE) % 30 == 1 and (10 <= seconds <= 20):
            try:
                df_immutable = pd.read_csv('data/parameters.csv')
            except FileNotFoundError:
                logging.info(FileNotFoundError)
            else:
                df_immutable = df_immutable.loc[df_immutable['Текущее'] == df_immutable['Рекомендуемое']].round(3)
                df_immutable = df_immutable.merge(DESCRIPTION, on='Параметр', how='left')
                df_immutable = df_immutable[['Параметр', 'Значение', 'Текущее']]

                table_immutable = dash_table.DataTable(
                    # style_cell_conditional=get_conditional_style(df_immutable, percent_FROM, percent_TO),
                    style_cell_conditional=[{'if': {'column_id': 'Параметр'}, 'textAlign': 'left'},
                                            {'if': {'column_id': 'Значение'}, 'textAlign': 'left'}],
                    style_data_conditional=[
                        {
                            'if': {'row_index': 'odd'},
                            'backgroundColor': 'rgb(248, 248, 248)'
                        }
                    ],
                    style_header={
                        'backgroundColor': 'rgb(230, 230, 230)',
                        'fontWeight': 'bold'
                    },
                    columns=[{"name": i, "id": i} for i in df_immutable.columns],
                    data=df_immutable.to_dict('records'),
                    # style_header={'backgroundColor': 'whitesmoke', 'fontWeight': 'bold',
                    #               'border': '1px solid whitesmoke'},
                    style_cell={'font_family': 'sans-serif', 'font_size': '16px'},
                    style_data={'border': '1px solid white'})

                return table_immutable
        else:
            raise PreventUpdate


@app.callback(Output('table-immutable', 'children'),
              [Input('intermediate-table', 'children'),
               Input('checklist', 'value')])
def show_table_immutable(table, check):
    if check:
        return table


@app.callback([Output('figure-yields', 'children'),
               Output('predict', 'children'),
               Output('optimal', 'children')],
              [Input('interval', 'n_intervals')])
def update_yields(n):
    if n == 0:
        try:
            df_yields = pd.read_csv('data/predictions.csv')
        except FileNotFoundError:
            logging.info(FileNotFoundError)
        else:
            predict_message = 'Predicted: {} %/30мин'.format(df_yields['yield'].round(3).head(1).values[0])
            optimal_message = 'Optimal: {} %/30мин'.format(df_yields['optimal'].round(3).head(1).values[0])

            data = [
                dict(
                    type="scatter",
                    mode="lines+markers",
                    name="Predicted",
                    x=df_yields['DT'],
                    y=df_yields['yield'],
                    line=dict(shape="spline", smoothing=2, width=2, color="#fac1b7"),
                    marker=dict(symbol="diamond-open"),
                ),
                dict(
                    type="scatter",
                    mode="lines+markers",
                    name="Recommended",
                    x=df_yields['DT'],
                    y=df_yields['optimal'],
                    line=dict(shape="spline", smoothing=2, width=2, color="#a9bb95"),
                    marker=dict(symbol="diamond-open"),
                ),
            ]

            figure = dcc.Graph(figure=dict(data=data))

            return figure, predict_message, optimal_message
    else:
        time_moment = datetime.datetime.now(MOSCOW_TIMEZONE)
        minutes, seconds = int(time_moment.strftime("%M")), int(time_moment.strftime("%S"))

        if (minutes - SYNC_TIME_MINUTE) % 30 == 1 and (10 <= seconds <= 20):
            try:
                df_yields = pd.read_csv('data/predictions.csv')
            except FileNotFoundError:
                logging.info(FileNotFoundError)
            else:
                predict_message = 'Predicted: {} %/30мин'.format(
                    df_yields['yield'].round(3).head(1).values[0])
                optimal_message = 'Optimal: {} %/30мин'.format(
                    df_yields['optimal'].round(3).head(1).values[0])

                data = [
                    dict(
                        type="scatter",
                        mode="lines+markers",
                        name="Predicted",
                        x=df_yields['DT'],
                        y=df_yields['yield'],
                        line=dict(shape="spline", smoothing=2, width=2, color="#fac1b7"),
                        marker=dict(symbol="diamond-open"),
                    ),
                    dict(
                        type="scatter",
                        mode="lines+markers",
                        name="Recommended",
                        x=df_yields['DT'],
                        y=df_yields['optimal'],
                        line=dict(shape="spline", smoothing=2, width=2, color="#a9bb95"),
                        marker=dict(symbol="diamond-open"),
                    ),
                ]

                figure = dcc.Graph(figure=dict(data=data))

                return figure, predict_message, optimal_message
        else:
            raise PreventUpdate
