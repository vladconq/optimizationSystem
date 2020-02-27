# index page
import datetime
import time
from waitress import serve
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import logging

from server import app, server
from flask_login import logout_user, current_user
from views import login, login_fd, adminpage, operatorpage
import grabber

from constants import MOSCOW_TIMEZONE, SYNC_TIME_MINUTE

logging.basicConfig(format='%(asctime)-8s [%(filename)s: %(lineno)d] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.DEBUG)

header = html.Div([
    html.Div([
        html.Img(src="assets/ml.png", className='logo'),
    ], className='left'),
    html.Div([
        html.Span("Optimization system of Diffusion Apparatus No. 2", className='text'),
    ], className='middle'),
    html.Div([
        html.Div([
            html.Div(id='user-name', className='username'),
            html.Div(id='logout', className='logout')
        ], className='auth')
    ], className='right')
], className='header')

app.layout = html.Div(
    [
        header,
        html.Div(id='page-content', className='main'),
        dcc.Location(id='url', refresh=False),
    ]
)

@app.callback(Output('page-content', 'children'),
              [Input('url', 'pathname')])
def display_page(pathname):
    if pathname == '/':
        if current_user.is_authenticated:
            if current_user.role == 'admin':
                return adminpage.layout
        else:
            return login.layout
    elif pathname == '/login':
        return login.layout
    elif pathname == '/adminpage':
        print('ok')
        if current_user.is_authenticated:
            return adminpage.layout
        else:
            return login_fd.layout
    elif pathname == '/operatorpage':
        if current_user.is_authenticated:
            return operatorpage.layout
        else:
            return login_fd.layout
    elif pathname == '/logout':
        if current_user.is_authenticated:
            logout_user()
            return login.layout
        else:
            return login.layout
    else:
        return '404'


@app.callback(Output('user-name', 'children'),
              [Input('page-content', 'children')])
def cur_user(input1):
    if current_user.is_authenticated:
        return html.Div('User: ' + current_user.username)
    else:
        return ''


@app.callback(Output('logout', 'children'),
              [Input('page-content', 'children')])
def user_logout(input1):
    if current_user.is_authenticated:
        return html.A('Exit', href='/logout')
    else:
        return ''


if __name__ == '__main__':
    logging.info('SYNC STARTED')

    # # для сборщика данных необходимо синхронизировать время
    # while True:
    #     moment = datetime.datetime.now(MOSCOW_TIMEZONE)
    #     minute, second = int(moment.strftime("%M")), int(moment.strftime("%S"))
    #     if (minute - SYNC_TIME_MINUTE) % 30 == 1 and second == 0:
    #         break
    #     # time.sleep(1)
    #
    # grabber.orchestra()

    # запуск приложения
    serve(server, host='0.0.0.0', port=80)
