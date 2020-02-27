import pandas as pd

parameters = dict()
parameters['W1_s3'] = 'Расход стружки в ДА2'
parameters['F1_s3'] = 'Расход питательной воды в ДА2'
parameters['F2_s3'] = 'Расход жомопрессовой вода в ДА2'
parameters['T1_s3'] = 'Температура в 1-ой зоне'
parameters['T2_s3'] = 'Температура во 2-ой зоне'
parameters['T3_s3'] = 'Температура в 3-ей зоне'
parameters['T4_s3'] = 'Температура в 4-ой зоне'
parameters['L1_s3'] = 'Уровень после сита ДА2'
parameters['L2_s3'] = 'Уровень перед ситом ДА2'
parameters['L7_s3'] = 'Уровень в сборнике конденсата №1 ДА2'
parameters['L8_s3'] = 'Уровень в сборнике конденсата №2 ДА2'
parameters['L18_s3'] = 'Уровень в шахте жомового пресса'
parameters['L3_s3'] = 'Уровень в 1-ой зоне ДА2'
parameters['L4_s3'] = 'Уровень во 2-ой зоне ДА2'
parameters['L5_s3'] = 'Уровень в 3-ей зоне ДА2'
parameters['L6_s3'] = 'Уровень в 4-ой зоне ДА2'
parameters['T6_s3'] = 'Температура в шкафу контроллера №2'
parameters['T7_s3'] = 'Температура питатетельной воды на ДА2'
parameters['D1_s3'] = 'Концентрация сухих веществ в диф. соке'
parameters['P1_s3'] = 'Давление масла жомпресса ДА2'
parameters['P2_s2'] = 'Давление воздуха в пневмосистеме'
parameters['Ei4_s3'] = 'Ток нагрузки привода насоса откачки дифсока ДА2'
parameters['Ei6_s3'] = 'Ток нагрузки жомового пресса №2'
parameters['Ei7_s3'] = 'Ток нагрузки привода шнека 06Н10'
parameters['Ei10_s3'] = 'Ток нагрузки привода шнека 06Н02'
parameters['Ei11_s3'] = 'Ток нагрузки привода шнека 06Н11'
parameters['Ei12_s3'] = 'Ток нагрузки привода шнека 06Н45'
parameters['Ei13_s3'] = 'Ток нагрузки привода шнека 06Н46'
parameters['Ei14_s3'] = 'Ток нагрузки привода шнека 06Н54'
parameters['L20_s3'] = 'Уровень жомопрессовой воды в сборнике перед диффаппаратами'
parameters['REZERV_s3'] = 'ph сульфитированной воды'

df_parameters = pd.DataFrame(pd.Series(parameters), columns=['Значение'])
df_parameters.reset_index(inplace=True)
df_parameters.rename(columns={'index': 'Параметр'}, inplace=True)

pids = dict()
pids['W1_s3'] = ''
pids['F1_s3'] = 'PID1'
pids['F2_s3'] = 'PID3'
pids['L1_s3'] = 'PID8'
pids['L2_s3'] = 'PID7'
pids['T1_s3'] = 'PID12'
pids['T2_s3'] = 'PID13'
pids['T3_s3'] = 'PID14'
pids['T4_s3'] = 'PID15'
pids['L7_s3'] = 'PID16'
pids['L8_s3'] = 'PID17'
pids['L18_s3'] = 'PID19'

df_pids = pd.DataFrame(pd.Series(pids), columns=['PID'])
df_pids.reset_index(inplace=True)
df_pids.rename(columns={'index': 'Параметр'}, inplace=True)

description = df_parameters.merge(df_pids, on='Параметр', how='left')
description.to_csv('data/description.csv')
