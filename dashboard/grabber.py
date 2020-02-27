import logging
import datetime
import threading
import psycopg2
import pandas as pd
import os
from constants import SYNC_TIME_MINUTE, MOSCOW_TIMEZONE, MINUTE_DELTA

AMOUNT_OF_PLOT_DOTS = 50
logging.basicConfig(format='%(asctime)-8s [%(filename)s: %(lineno)d] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.DEBUG)


def prepare_dir():
    try:
        os.remove('data/parameters.csv')
        os.remove('data/predictions.csv')
    except FileNotFoundError:
        logging.debug('NOTHING TO DELETE')


def get_time_period():
    reporting_time = (datetime.datetime.now(MOSCOW_TIMEZONE) - datetime.timedelta(minutes=SYNC_TIME_MINUTE))
    reporting_time_delta = (reporting_time - datetime.timedelta(minutes=MINUTE_DELTA * AMOUNT_OF_PLOT_DOTS))
    forecast_time = (datetime.datetime.now(MOSCOW_TIMEZONE) - datetime.timedelta(
        minutes=SYNC_TIME_MINUTE) + datetime.timedelta(minutes=MINUTE_DELTA))
    forecast_time_delta = (forecast_time - datetime.timedelta(minutes=MINUTE_DELTA * AMOUNT_OF_PLOT_DOTS))

    reporting_time, reporting_time_delta, forecast_time, forecast_time_delta = \
        reporting_time.strftime("%Y-%m-%d %H:%M:00"), \
        reporting_time_delta.strftime("%Y-%m-%d %H:%M:00"), \
        forecast_time.strftime("%Y-%m-%d %H:%M:00"), \
        forecast_time_delta.strftime("%Y-%m-%d %H:%M:00")

    return reporting_time, reporting_time_delta, forecast_time, forecast_time_delta


def get_data(reporting_time, reporting_time_delta, forecast_time, forecast_time_delta):
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

        sql_history = """SELECT "DT_msk",
                          "Object",
                          "Value"
                          FROM public.history30min
                          WHERE "DT_msk" <= '{}'
                          AND "DT_msk" > '{}'""".format(reporting_time, reporting_time_delta)
        cursor.execute(sql_history, conn)
        data_history = pd.DataFrame(cursor.fetchall(), columns=['DT', 'Параметр', 'Value'])

        sql_recommendations = """SELECT "DT",
                        "Object",
                        "Value"
                        FROM public.recommendations30min
                        WHERE "DT" = '{}'""".format(reporting_time)
        cursor.execute(sql_recommendations, conn)
        data_recommendations = pd.DataFrame(cursor.fetchall(), columns=['DT', 'Параметр', 'Value'])

        sql_predictions = """SELECT "DT", 
                              "yield", 
                              "optimal" 
                              FROM public.predictions30min
                              WHERE "DT" <= '{}'
                              AND "DT" > '{}'""".format(forecast_time, forecast_time_delta)
        cursor.execute(sql_predictions, conn)
        data_predictions = pd.DataFrame(cursor.fetchall(), columns=['DT', 'yield', 'optimal'])
        data_predictions = data_predictions.sort_values(by='DT', ascending=False)

        return data_history, data_recommendations, data_predictions

    except Exception as error:
        logging.info('EXCEPT: ' + repr(error))

    finally:
        if conn:
            conn.commit()
            cursor.close()
            conn.close()


def process_and_save_data(data_history, data_recommendations, data_predictions, reporting_time):
    # мерджим оптимальные и Factические параметры
    data_parameters = data_history.merge(data_recommendations[['Параметр', 'Value']], on='Параметр')
    data_parameters.rename(columns={'Value_x': 'Текущее', 'Value_y': 'Рекомендуемое', 'DT_msk': 'DT'}, inplace=True)
    data_parameters = data_parameters.loc[data_parameters['DT'] == reporting_time]

    # мерджим предсказанные и Factические выходы сахара
    data_predictions = data_predictions.merge(data_history[['DT', 'Value']].loc[data_history['Параметр'] == 'pR1d2_s1'],
                                              on='DT', how='left')
    data_predictions.rename(columns={'Value': 'fact'}, inplace=True)

    system, optimal = data_parameters['Текущее'], data_parameters['Рекомендуемое']
    try:
        data_parameters['Percent'] = abs(system * 100 / optimal - 100)
    except ZeroDivisionError:
        data_parameters['Percent'] = 100
    data_parameters.sort_values(by=['Параметр'], ascending=False, inplace=True)

    data_parameters.drop(['Percent'], axis=1, inplace=True)
    data_parameters.reset_index(inplace=True, drop=True)

    # регулирование
    # try:
    data_parameters.loc[data_parameters['Текущее'] < data_parameters['Рекомендуемое'], 'Регулировка'] = '▲'
    data_parameters.loc[data_parameters['Текущее'] > data_parameters['Рекомендуемое'], 'Регулировка'] = '▼'
    # except ValueError:
    #     logging.info('ValueError: grabber')
    #     return None

    data_predictions['yield'] = data_predictions['yield'] * 1.7
    data_predictions['optimal'] = data_predictions['optimal'] * 1.7
    data_predictions['fact'] = data_predictions['fact'] * 1.7
    data_predictions['optimal'] = data_predictions['optimal'] - 1

    try:
        data_parameters = data_parameters.drop(data_parameters[data_parameters['Параметр'] == 'F3_s3'].index)
    except Exception as err:
        repr(err)
    try:
        data_parameters = data_parameters.drop(data_parameters[data_parameters['Параметр'] == 'T5_s3'].index)
    except Exception as err:
        repr(err)
    try:
        data_parameters = data_parameters.drop(data_parameters[data_parameters['Параметр'] == 'pR1d2_s1'].index)
    except Exception as err:
        repr(err)
    try:
        data_parameters = data_parameters.drop(data_parameters[data_parameters['Параметр'] == 'T6_s3'].index)
    except Exception as err:
        repr(err)

    data_parameters.to_csv('data/parameters.csv', index=False)
    data_predictions.to_csv('data/predictions.csv', index=False)

    logging.info('Thread completed')


def orchestra():
    threading.Timer(interval=1800, function=orchestra).start()

    logging.debug('GRABBER STARTED')

    # очистить папку, если в ней что-то есть
    prepare_dir()
    # получить временной промежуток
    reporting_time, reporting_time_delta, forecast_time, forecast_time_delta = get_time_period()
    # получить данные
    data_history, data_recommendations, data_predictions = get_data(reporting_time,
                                                                    reporting_time_delta,
                                                                    forecast_time,
                                                                    forecast_time_delta)
    # обработать данные
    process_and_save_data(data_history, data_recommendations, data_predictions, reporting_time)

    logging.debug('GRABBER FINISHED')
