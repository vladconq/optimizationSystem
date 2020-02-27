import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State

from server import app, User
from flask_login import login_user
from werkzeug.security import check_password_hash

layout = html.Div(
    children=[
        html.Div(
            className="login",
            children=[
                dcc.Location(id='url_login', refresh=True),
                html.Div('''Sign in to continue:''', id='h1'),
                html.Div(
                    # method='Post',
                    children=[
                        dcc.Input(
                            placeholder='login',
                            type='text',
                            id='uname-box'
                        ),
                        dcc.Input(
                            placeholder='password',
                            type='password',
                            id='pwd-box'
                        ),
                        html.Button(
                            children='Enter',
                            n_clicks=0,
                            type='submit',
                            id='login-button'
                        ),
                        html.Div(children='', id='output-state')
                    ]
                ),
            ]
        )
    ]
)


@app.callback(Output('url_login', 'pathname'),
              [Input('login-button', 'n_clicks')],
              [State('uname-box', 'value'),
               State('pwd-box', 'value')])
def sucess(n_clicks, input1, input2):
    user = User.query.filter_by(username=input1).first()
    if user:
        if user.role == 'operator':
            if check_password_hash(user.password, input2):
                login_user(user)
                return '/operatorpage'
            else:
                pass
        if user.role == 'admin':
            if check_password_hash(user.password, input2):
                login_user(user)
                return '/adminpage'
            else:
                pass
    else:
        pass


@app.callback(Output('output-state', 'children'),
              [Input('login-button', 'n_clicks')],
              [State('uname-box', 'value'),
               State('pwd-box', 'value')])
def update_output(n_clicks, input1, input2):
    if n_clicks > 0:
        user = User.query.filter_by(username=input1).first()
        if user:
            if check_password_hash(user.password, input2):
                return ''
            else:
                return 'Неправильный логин или пароль'
        else:
            return 'Неправильный логин или пароль'
    else:
        return ''
