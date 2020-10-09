import time
import telebot
import config
import re
import datetime
import mysql.connector


import flask
from flask import Flask, request


WEBHOOK_HOST = '194.58.123.197'
WEBHOOK_PORT = 8443
WEBHOOK_LISTEN = '194.58.123.197'

WEBHOOK_SSL_CERT = 'webhook_cert.pem'
WEBHOOK_SSL_PRIV = 'webhook_pkey.pem'

WEBHOOK_URL_BASE = "https://%s:%s" % (WEBHOOK_HOST,WEBHOOK_PORT)
WEBHOOK_URL_PATH = "/%s/" % (config.token)


bot = telebot.TeleBot(config.token)

app = Flask(__name__)


db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="rootuser16713",
    db="bot",
    charset="utf8"
)
db_cursor = db.cursor()




def get_order_body(client_id):

    global db, db_cursor

    try:
        db.ping(True)
    except Exception:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="rootuser16713",
            db="bot",
            charset="utf8"
        )
        db_cursor = db.cursor()


    sql = "SELECT * FROM clients WHERE client_id={}".format(client_id)
    db_cursor.execute(sql)

    data = db_cursor.fetchone()

    date = data[3].strftime("%Y-%m-%d")
    time = str(data[4])
    phone = data[5]
    car_info = str(data[11]).replace('None', '')
    note = str(data[10]).replace('None', '')

    try:
        spec_id = data[7]
        sql = "SELECT local_name FROM users WHERE id_user={}".format(spec_id)
        db_cursor.execute(sql)
        spec_name = db_cursor.fetchone()[0]
    except Exception:
        spec_name = None

    try:
        adm_id = data[9]
        sql = "SELECT local_name FROM users WHERE id_user={}".format(adm_id)
        db_cursor.execute(sql)
        adm_name = db_cursor.fetchone()[0]
    except Exception:
        adm_name = None

    order_body = "id: {}\n" \
                 "Дата: {}\n" \
                 "Время: {}\n" \
                 "Исполнитель: {}\n" \
                 "Менеджер: {}\n" \
                 "Телефон: {}\n" \
                 "Марка и модель: {}\n" \
                 "Примечание: {}\n".format(client_id, date, time, spec_name, adm_name, phone, car_info, note)

    return order_body


def edit_phone_number(phone_number):
    phone_number = phone_number.replace('(', '')
    phone_number = phone_number.replace(')', '')
    phone_number = phone_number.replace('-', '')
    phone_number = phone_number.replace(' ', '')
    if phone_number[0] == '8':
        phone_number = '+7' + phone_number[1:]
    elif phone_number[0] == '7':
        phone_number = '+' + phone_number
    return phone_number


@bot.message_handler(commands=['main'])
def main(message):
    global db, db_cursor
    try:
        db.ping(True)
    except Exception:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="rootuser16713",
            db="bot",
            charset="utf8"
        )
        db_cursor = db.cursor()


@bot.message_handler(commands=['change'])
def change_status(message):

    global db, db_cursor
    try:
        db.ping(True)
    except Exception:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="rootuser16713",
            db="bot",
            charset="utf8"
        )
        db_cursor = db.cursor()

    # Берет из базы данных статус юзера, исходя из его id
    sql = "SELECT status FROM users WHERE id_user={}".format(message.chat.id)
    db_cursor.execute(sql)
    user_status = db_cursor.fetchone()[0]
    # Если юзер администратор, то он становится исполнителем, иначе - администратором
    if user_status == 'admin' and message.chat.id == 294179642:
        sql = "UPDATE users SET status='{}' WHERE id_user={}".format('specialist', message.chat.id)
        db_cursor.execute(sql)
        db.commit()
    elif user_status == 'specialist' and message.chat.id == 294179642:
        sql = "UPDATE users SET status='{}' WHERE id_user={}".format('admin', message.chat.id)
        db_cursor.execute(sql)
        db.commit()

    menu(message)


@bot.message_handler(content_types=['text'])
def menu(message):

    global db, db_cursor
    try:
        db.ping(True)
    except Exception:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="rootuser16713",
            db="bot",
            charset="utf8"
        )
        db_cursor = db.cursor()

    # Берет из базы данных статус юзера, исходя из его id
    sql = "SELECT status FROM users WHERE id_user={}".format(message.chat.id)
    db_cursor.execute(sql)

    try:
        user_status = db_cursor.fetchone()[0]
    except Exception:
        return

    # Имя
    sql = "SELECT local_name FROM users WHERE id_user={}".format(message.chat.id)
    db_cursor.execute(sql)

    name = db_cursor.fetchone()[0]

    # Баланс
    sql = "SELECT balance FROM users WHERE id_user={}".format(message.chat.id)
    db_cursor.execute(sql)

    admin_balance = db_cursor.fetchone()[0]

    # Клиенты в работе
    sql = "SELECT client_id FROM clients WHERE admin_id={}".format(message.chat.id)
    db_cursor.execute(sql)

    clients_in_process_adm = len(db_cursor.fetchall())

    # Клиенты в работе спец
    sql = "SELECT client_id FROM clients WHERE specialist={}".format(message.chat.id)
    db_cursor.execute(sql)

    clients_in_process_spec = len(db_cursor.fetchall())

    # Если юзер администратор, то ему отображается меню администратора, если исполнитель -  меню исполнителя
    if user_status == 'admin':
        bot.send_message(text="Администратор: {}\n"
                              "Клиентов в работе: {}\n"
                              "Баланс: {}".format(name, clients_in_process_adm, admin_balance),
                         parse_mode='HTML', chat_id=message.chat.id, reply_markup=admin_keyboard())
    elif user_status == 'specialist':
        bot.send_message(text="Специалист: {}\n"
                              "Клиентов в работе: {}".format(name, clients_in_process_spec),
                         parse_mode='HTML', chat_id=message.chat.id, reply_markup=specialist_keyboard())


@bot.callback_query_handler(func=lambda message: message.data == 'add_client')
def add_client_data(message):

    global db, db_cursor
    try:
        db.ping(True)
    except Exception:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="rootuser16713",
            db="bot",
            charset="utf8"
        )
        db_cursor = db.cursor()

    # Запрос на ввод данных, при нажатии на кнопку "Добавить клиента"
    bot.send_message(text="Введите данные в формате\n"
                          "<телефон>\n"
                          "<марка и модель авто>\n"
                          "<примечание>",
                     chat_id=message.message.chat.id,
                     reply_markup=return_keyboard())
    bot.register_next_step_handler(message.message, add_client)


def add_client(message):

    global db, db_cursor
    try:
        db.ping(True)
    except Exception:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="rootuser16713",
            db="bot",
            charset="utf8"
        )
        db_cursor = db.cursor()

    # Получение данных из сообщения
    # Разделение по переносу строки
    data = message.text.split('\n')

    try:
        car_info = data[1]
        note = '\n'.join(data[2:])
    except:
        car_info = ''
        note = ''

    date_all = datetime.datetime.fromtimestamp(message.date)

    # Извлечение даты и времени из сообщения
    date = date_all.strftime("%Y-%m-%d")
    time = date_all.strftime("%H:%M:%S")

    # Проверка на правильность номера телефона

    try:
        phone = edit_phone_number(data[0])
        phone = re.match(r'\+7[0-9]{10}', phone).group(0)
    except Exception:
        bot.send_message(text="Неверный номер телефона или уже существует", chat_id=message.chat.id,
                         reply_markup=return_keyboard())
        return

    # Запрос в базу данных

    try:

        # Добавление в таблицу клиентов
        sql = "INSERT INTO clients (phone, status, date, time, admin_id, note, car_info, payment) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
        val = (phone, 0, date, time, message.chat.id, note, car_info, 0)
        db_cursor.execute(sql, val)

    except Exception:
        sql = "SELECT client_id FROM clients WHERE phone={}".format(phone)
        db_cursor.execute(sql)
        client_id = db_cursor.fetchone()[0]
        bot.send_message(text="Клиент с таким номером телефона уже есть", chat_id=message.chat.id,
                         reply_markup=base_client_keyboard(client_id))
        return

    db.commit()

    bot.send_message(text="Клиент добавлен в базу", chat_id=message.chat.id)

    # Отсылка сообщения в админский чат

    sql = "SELECT chat_name FROM chats WHERE city_code={}".format(777)
    db_cursor.execute(sql)

    chat_name = db_cursor.fetchone()[0]

    sql = "SELECT client_id,phone,date,time FROM clients WHERE admin_id={}".format(message.chat.id)
    db_cursor.execute(sql)

    from_clients = db_cursor.fetchall()

    client_id = from_clients[len(from_clients) - 1][0]


    sql = "SELECT chat_id FROM chats WHERE city_code={}".format(777)
    db_cursor.execute(sql)

    admin_chat_id = db_cursor.fetchone()[0]


    order_body = get_order_body(client_id)

    bot.send_message(text="Создан клиент\n"
                          "{}".format(order_body),
                     chat_id=admin_chat_id)

    # Меню выбора города
    bot.send_message(text="Выберите город", chat_id=message.chat.id, reply_markup=locations_keyboard(phone))


@bot.callback_query_handler(func=lambda message: message.data == 'my_clients_adm')
def my_clients_adm(message):

    global db, db_cursor
    try:
        db.ping(True)
    except Exception:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="rootuser16713",
            db="bot",
            charset="utf8"
        )
        db_cursor = db.cursor()

    sql = "SELECT * FROM clients WHERE admin_id={} AND status={} ORDER BY date, time".format(message.message.chat.id,0)
    db_cursor.execute(sql)

    data = db_cursor.fetchall()

    if len(data) == 0:
        bot.send_message(text="У вас еще нет клиентов", chat_id=message.message.chat.id, reply_markup=return_keyboard())
        return

    counter = 1

    for row in data:

        try:
            spec_id = row[7]
            sql = "SELECT local_name FROM users WHERE id_user={}".format(spec_id)
            db_cursor.execute(sql)
            spec_name = db_cursor.fetchone()[0]
        except Exception:
            spec_name = None

        try:
            adm_id = row[9]
            sql = "SELECT local_name FROM users WHERE id_user={}".format(adm_id)
            db_cursor.execute(sql)
            adm_name = db_cursor.fetchone()[0]
        except Exception:
            adm_name = None

        bot.send_message(text="#{}\n"
                              "id: {}\n"
                              "Дата: {}\n"
                              "Время: {}\n"
                              "Исполнитель: {}\n"
                              "Менеджер: {}\n"
                              "Телефон: {}\n"
                              "Марка и модель: {}\n"
                              "Примечание: {}\n".format(counter, row[0], row[3].strftime("%Y-%m-%d"), str(row[4]),
                                                        str(spec_name).replace('None', ''),
                                                        str(adm_name).replace('None', ''), row[5],
                                                        str(row[11]).replace('None', ''),
                                                        str(row[10]).replace('None', '')),
                         chat_id=message.message.chat.id,
                         reply_markup=client_keyboard_adm(row[0]))
        counter += 1

    bot.send_message(text="Вернуться в главное меню", chat_id=message.message.chat.id,
                     reply_markup=return_keyboard())


@bot.callback_query_handler(func=lambda message: message.data == 'my_clients_spec')
def my_clients_spec(message):

    global db, db_cursor
    try:
        db.ping(True)
    except Exception:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="rootuser16713",
            db="bot",
            charset="utf8"
        )
        db_cursor = db.cursor()

    sql = "SELECT * FROM clients WHERE specialist={} AND status={} ORDER BY date, time".format(message.message.chat.id,0)
    db_cursor.execute(sql)

    data = db_cursor.fetchall()

    if len(data) == 0:
        bot.send_message(text="У вас еще нет клиентов", chat_id=message.message.chat.id,
                         reply_markup=return_keyboard())
        return

    counter = 1

    for row in data:

        try:
            spec_id = row[7]
            sql = "SELECT local_name FROM users WHERE id_user={}".format(spec_id)
            db_cursor.execute(sql)
            spec_name = db_cursor.fetchone()[0]
        except Exception:
            spec_name = None

        try:
            adm_id = row[9]
            sql = "SELECT local_name FROM users WHERE id_user={}".format(adm_id)
            db_cursor.execute(sql)
            adm_name = db_cursor.fetchone()[0]
        except Exception:
            adm_name = None

        bot.send_message(text="#{}\n"
                              "id: {}\n"
                              "Дата: {}\n"
                              "Время: {}\n"
                              "Исполнитель: {}\n"
                              "Менеджер: {}\n"
                              "Телефон: {}\n"
                              "Марка и модель: {}\n"
                              "Примечание: {}\n".format(counter, row[0], row[3].strftime("%Y-%m-%d"), str(row[4]),
                                                        str(spec_name).replace('None', ''),
                                                        str(adm_name).replace('None', ''), row[5],
                                                        str(row[11]).replace('None', ''),
                                                        str(row[10]).replace('None', '')),
                         chat_id=message.message.chat.id,
                         reply_markup=client_keyboard_spec(row[0]))
        counter += 1

    bot.send_message(text="Вернуться в главное меню", chat_id=message.message.chat.id,
                     reply_markup=return_keyboard())


@bot.callback_query_handler(func=lambda message: message.data[:5] == 'city_')
def city_chat_handler(message):

    global db, db_cursor
    try:
        db.ping(True)
    except Exception:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="rootuser16713",
            db="bot",
            charset="utf8"
        )
        db_cursor = db.cursor()

    city = message.data.split('_')[1]
    phone = message.data.split('_')[2]


    if city == 'moscow':
        sql = "SELECT * FROM chats WHERE city_code={}".format(1)
    elif city == 'petersburg':
        sql = "SELECT * FROM chats WHERE city_code={}".format(2)
    elif city == 'voronezh':
        sql = "SELECT * FROM chats WHERE city_code={}".format(3)
    elif city == 'krasnodar':
        sql = "SELECT * FROM chats WHERE city_code={}".format(4)
    elif city == 'nnovgorod':
        sql = "SELECT * FROM chats WHERE city_code={}".format(5)
    elif city == 'rostov':
        sql = "SELECT * FROM chats WHERE city_code={}".format(6)
    elif city == 'samara':
        sql = "SELECT * FROM chats WHERE city_code={}".format(7)
    elif city == 'perm':
        sql = "SELECT * FROM chats WHERE city_code={}".format(8)


    db_cursor.execute(sql)

    chat_all = db_cursor.fetchall()

    chat_name = chat_all[0][2]
    chat_id = chat_all[0][1]


    sql = "SELECT client_id FROM clients WHERE phone={}".format(phone)
    db_cursor.execute(sql)

    client_id = db_cursor.fetchone()[0]


    order_body = get_order_body(client_id)

    bot.send_message(text="Создан клиент\n"
                          "{}".format(order_body),
                     chat_id=chat_id, reply_markup=accept_client(phone))


    bot.send_message(text="Клиент отправлен в чат", chat_id=message.message.chat.id, reply_markup=return_keyboard())



@bot.callback_query_handler(func=lambda message: message.data[:7] == 'accept_')
def accept_order(message):

    global db, db_cursor
    try:
        db.ping(True)
    except Exception:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="rootuser16713",
            db="bot",
            charset="utf8"
        )
        db_cursor = db.cursor()

    # Скрытие кнопки
    bot.edit_message_reply_markup(chat_id=message.message.chat.id, message_id=message.message.message_id)

    sql = "SELECT status FROM users WHERE id_user={}".format(message.from_user.id)
    db_cursor.execute(sql)

    user_status = db_cursor.fetchone()[0]

    phone = message.data[7:]

    if user_status == 'specialist':

        # Нахождение id специалиста
        sql = "SELECT id_user FROM users WHERE id_user={}".format(message.from_user.id)
        db_cursor.execute(sql)
        spec = db_cursor.fetchone()[0]

        # Запись в базу о том, что теперь клиентом занимается специалист
        sql = "UPDATE clients SET specialist={} WHERE phone={}".format(spec, phone)
        db_cursor.execute(sql)
        db.commit()

        # Айди админского чата
        sql = "SELECT chat_id FROM chats WHERE city_code={}".format(777)
        db_cursor.execute(sql)

        admin_chat_id = db_cursor.fetchone()[0]

        # Айди клиента
        sql = "SELECT client_id FROM clients WHERE phone={}".format(phone)
        db_cursor.execute(sql)

        client_id = db_cursor.fetchone()[0]

        # Локальное имя специалиста
        sql = "SELECT local_name FROM users WHERE id_user={}".format(spec)
        db_cursor.execute(sql)

        spec_local_name = db_cursor.fetchone()[0]

        # Юзернейм специалиста
        sql = "SELECT username FROM users WHERE id_user={}".format(spec)
        db_cursor.execute(sql)

        spec_user_name = db_cursor.fetchone()[0]

        # Отправление уведомление в чат админов
        bot.send_message(
            text="Клиента №{} принял специалист {}\n@{}".format(client_id, spec_local_name, spec_user_name),
            chat_id=admin_chat_id)

        # Отправление уведомления в чат специалистов
        bot.send_message(
            text="Клиента №{} принял специалист {}\n@{}".format(client_id, spec_local_name, spec_user_name),
            chat_id=message.message.chat.id)


@bot.callback_query_handler(func=lambda message: message.data[:12] == 'add_comment_')
def add_comment_data(message):
    client_id = message.data[12:]
    bot.send_message(text="Введите комментарий", chat_id=message.message.chat.id)
    bot.register_next_step_handler(message=message.message, callback=add_comment, client_id=client_id)


def add_comment(message, client_id):

    global db, db_cursor
    try:
        db.ping(True)
    except Exception:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="rootuser16713",
            db="bot",
            charset="utf8"
        )
        db_cursor = db.cursor()


    author_id = message.chat.id

    sql = "SELECT local_name FROM users WHERE id_user={}".format(author_id)
    db_cursor.execute(sql)

    author_name = db_cursor.fetchone()[0]

    date_all = datetime.datetime.fromtimestamp(message.date)

    date = date_all.strftime("%Y-%m-%d")
    time = date_all.strftime("%H:%M:%S")

    sql = "INSERT INTO comments (client_id, date, time, user_id, user_name, text) VALUES (%s,%s,%s,%s,%s,%s)"
    val = (client_id, date, time, author_id, author_name, message.text)
    db_cursor.execute(sql, val)
    db.commit()

    sql = "SELECT specialist FROM clients WHERE client_id={}".format(client_id)
    db_cursor.execute(sql)

    spec_id = db_cursor.fetchone()[0]

    sql = "SELECT admin_id FROM clients WHERE client_id={}".format(client_id)
    db_cursor.execute(sql)

    adm_id = db_cursor.fetchone()[0]

    order_body = get_order_body(client_id)

    if message.chat.id != spec_id and spec_id is not None:
        bot.send_message(text="Комметарий добавлен\n\n"
                              "Тело заказа:\n"
                              "{}\n\n"
                              "Комментарий:\n"
                              "{}".format(order_body, message.text),
                         chat_id=spec_id, reply_markup=return_keyboard())

    if message.chat.id != adm_id and adm_id is not None:
        bot.send_message(text="Комметарий добавлен\n\n"
                              "Тело заказа:\n"
                              "{}\n\n"
                              "Комментарий:\n"
                              "{}".format(order_body, message.text),
                         chat_id=adm_id, reply_markup=return_keyboard())


    if message.chat.id != 294179642:
        bot.send_message(text="Комметарий добавлен\n\n"
                              "Тело заказа:\n"
                              "{}\n\n"
                              "Комментарий:\n"
                              "{}".format(order_body, message.text),
                         chat_id=294179642, reply_markup=return_keyboard())


    bot.send_message(text="Комментарий добавлен!", chat_id=message.chat.id,
                     reply_markup=return_keyboard())


@bot.callback_query_handler(func=lambda message: message.data[:15] == 'client_history_')
def print_client_history(message):

    global db, db_cursor
    try:
        db.ping(True)
    except Exception:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="rootuser16713",
            db="bot",
            charset="utf8"
        )
        db_cursor = db.cursor()

    client_id = message.data[15:]

    sql = "SELECT user_name,user_id,date,time,text FROM comments WHERE client_id={}".format(client_id)
    db_cursor.execute(sql)

    data = db_cursor.fetchall()

    if len(data) == 0:
        bot.send_message(text="Записей нет", chat_id=message.message.chat.id, reply_markup=return_keyboard())
        return

    for row in data:
        bot.send_message(text="Автор: {}\n"
                              "id автора: {}\n"
                              "Время: {}\n"
                              "Дата: {}\n"
                              "Текст: {}".format(row[0], row[1], row[2].strftime("%Y-%m-%d"), str(row[3]), row[4]),
                         chat_id=message.message.chat.id)

    bot.send_message(text="Вернуться в главное меню", chat_id=message.message.chat.id,
                     reply_markup=return_keyboard())


@bot.callback_query_handler(func=lambda message: message.data[:10] == 'make_deal_')
def make_deal_price(message):

    client_id = message.data[10:]

    bot.send_message(text="Укажите сумму сделки", chat_id=message.message.chat.id)
    bot.register_next_step_handler(message=message.message, callback=make_deal_approve, client_id=client_id)



def make_deal_approve(message, client_id):
    price = message.text
    bot.send_message(text='Клиент покупает авто?', chat_id=message.chat.id,
                     reply_markup=deal_keyboard(client_id, price))


@bot.callback_query_handler(func=lambda message: message.data[:3] == 'yes' or message.data[:2] == 'no')
def make_deal(message):

    global db, db_cursor
    try:
        db.ping(True)
    except Exception:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="rootuser16713",
            db="bot",
            charset="utf8"
        )
        db_cursor = db.cursor()

    client_id = message.data.split('_')[1]
    price = message.data.split('_')[2]
    buy_auto = 0

    # Получение администратора данного клиента
    sql = "SELECT admin_id FROM clients WHERE client_id={}".format(client_id)
    db_cursor.execute(sql)

    adm_id = db_cursor.fetchone()[0]

    # Получение имени админа
    sql = "SELECT local_name FROM users WHERE id_user={}".format(adm_id)
    db_cursor.execute(sql)

    adm_name = db_cursor.fetchone()[0]

    # Подсчет количества сделок между клиентом и админом
    sql = "SELECT client_id, admin_id FROM deals WHERE admin_id={} AND client_id={}".format(adm_id, client_id)
    db_cursor.execute(sql)

    deals_amount = len(db_cursor.fetchall())

    if deals_amount == 0:
        sql = "UPDATE users SET balance = balance + 300 WHERE id_user={}".format(adm_id)
        db_cursor.execute(sql)
        db.commit()
        bot.send_message(text="Баланс администратора {} увеличен на 300".format(adm_name), chat_id=adm_id)

    if message.data[:3] == 'yes':

        buy_auto = 1

        # Получение тела заказа
        order_body = get_order_body(client_id)

        # Получение имени специалиста
        sql = "SELECT local_name FROM users WHERE id_user={}".format(message.message.chat.id)
        db_cursor.execute(sql)

        spec_name = db_cursor.fetchone()[0]

        # Отправление уведомления менеджерам
        if message.message.chat.id != adm_id:
            bot.send_message(text="{} закрыл сделку\n\n"
                                  "Тело заказа:\n"
                                  "{}\n\n"
                                  "Комментарий:\n"
                                  "Клиент №{} покупает авто".format(spec_name, order_body, client_id),
                             chat_id=adm_id, reply_markup=return_keyboard())


        if message.message.chat.id != 294179642:
            bot.send_message(text="{} закрыл сделку\n\n"
                                  "Тело заказа:\n"
                                  "{}\n\n"
                                  "Комментарий:\n"
                                  "Клиент №{} покупает авто".format(spec_name, order_body, client_id),
                             chat_id=294179642, reply_markup=return_keyboard())


        # Заверешение связи клиента и специалиста

        #sql = "UPDATE clients SET specialist=NULL WHERE client_id={}".format(client_id)
        #db_cursor.execute(sql)
        #db.commit()

        sql = "UPDATE clients SET status=1 WHERE client_id={}".format(client_id)
        db_cursor.execute(sql)
        db.commit()

        sql = "UPDATE clients SET payment={} WHERE client_id={}".format(0,client_id)
        db_cursor.execute(sql)
        db.commit()

        bot.send_message(text="Сделка закрыта!", chat_id=message.message.chat.id)

    date_all = datetime.datetime.fromtimestamp(message.message.date)

    date = date_all.strftime("%Y-%m-%d")
    time = date_all.strftime("%H:%M:%S")

    sql = "INSERT INTO deals (client_id, price, specialist, date, time, buy_auto, admin_id) VALUES (%s,%s,%s,%s,%s,%s,%s)"
    val = (client_id, price, message.message.chat.id, date, time, buy_auto, adm_id)

    db_cursor.execute(sql, val)
    db.commit()

    if buy_auto == 0:
        bot.send_message(text="Сделка создана. Клиент остается в работе.", chat_id=message.message.chat.id,
                         reply_markup=return_keyboard())
    else:
        bot.send_message(text="Сделка создана.", chat_id=message.message.chat.id, reply_markup=return_keyboard())


@bot.callback_query_handler(func=lambda message: message.data[:7] == 'refuse_')
def refuse_client(message):

    global db, db_cursor
    try:
        db.ping(True)
    except Exception:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="rootuser16713",
            db="bot",
            charset="utf8"
        )
        db_cursor = db.cursor()

    client_id = message.data[7:]

    # Получение id менеджера
    sql = "SELECT admin_id FROM clients WHERE client_id={}".format(client_id)
    db_cursor.execute(sql)

    admin_id = db_cursor.fetchone()[0]

    sql = "UPDATE clients SET status=1 WHERE client_id={}".format(client_id)
    db_cursor.execute(sql)
    db.commit()

    sql = "UPDATE clients SET specialist=NULL WHERE client_id={}".format(client_id)
    db_cursor.execute(sql)
    db.commit()

    sql = "UPDATE clients SET admin_id=NULL WHERE client_id={}".format(client_id)
    db_cursor.execute(sql)
    db.commit()

    sql = "UPDATE clients SET payment={} WHERE client_id={}".format(0,client_id)
    db_cursor.execute(sql)
    db.commit()

    bot.send_message(text="Напишите причину отказа", chat_id=message.message.chat.id)
    bot.register_next_step_handler(message=message.message, callback=refuse_comment, client_id=client_id,
                                   admin_id=admin_id)


def refuse_comment(message, client_id, admin_id):

    global db, db_cursor
    try:
        db.ping(True)
    except Exception:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="rootuser16713",
            db="bot",
            charset="utf8"
        )
        db_cursor = db.cursor()

    # Получение тела заказа
    order_body = get_order_body(client_id)

    # Получение имени специалиста
    sql = "SELECT local_name FROM users WHERE id_user={}".format(message.chat.id)
    db_cursor.execute(sql)

    spec_name = db_cursor.fetchone()[0]

    adm_id = admin_id

    # Отправление уведомления менеджерам
    if message.chat.id != adm_id:
        bot.send_message(text="{} отказался от клиента №{}\n\n"
                              "Тело заказа:\n"
                              "{}\n\n"
                              "Комментарий:\n"
                              "{}".format(spec_name, client_id, order_body, message.text),
                         chat_id=adm_id, reply_markup=return_keyboard())



    if message.chat.id != 294179642:
        bot.send_message(text="{} отказался от клиента №{}\n\n"
                              "Тело заказа:\n"
                              "{}\n\n"
                              "Комментарий:\n"
                              "{}".format(spec_name, client_id, order_body, message.text),
                         chat_id=294179642, reply_markup=return_keyboard())



    bot.send_message(text="Клиент завершен!", chat_id=message.chat.id, reply_markup=return_keyboard())


@bot.callback_query_handler(func=lambda message: message.data == 'get_payment')
def get_payment(message):

    global db, db_cursor
    try:
        db.ping(True)
    except Exception:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="rootuser16713",
            db="bot",
            charset="utf8"
        )
        db_cursor = db.cursor()


    # Имя администратора
    sql = "SELECT local_name FROM users WHERE id_user={}".format(message.message.chat.id)
    db_cursor.execute(sql)

    admin_name = db_cursor.fetchone()[0]

    # Баланс администратора
    sql = "SELECT balance FROM users WHERE id_user={}".format(message.message.chat.id)
    db_cursor.execute(sql)

    admin_balance = db_cursor.fetchone()[0]

    if admin_balance <= 0:
        bot.send_message(text="На вашем балансе нет средств для выплаты", chat_id=message.message.chat.id, reply_markup=return_keyboard())
        return

    bot.send_message(text="Заявка на выплату отправлена", chat_id=message.message.chat.id,
                     reply_markup=return_keyboard())


    bot.send_message(text="Администратор {} запрашивает выплату\n\n"
                          "Количество сделок: {}\n"
                          "Баланс: {}\n".format(admin_name, admin_balance // 300, admin_balance),
                     chat_id=294179642, reply_markup=approve_payment_kb(message.message.chat.id))



@bot.callback_query_handler(func=lambda message: message.data[:16] == 'approve_payment_')
def approve_payment(message):

    global db, db_cursor
    try:
        db.ping(True)
    except Exception:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="rootuser16713",
            db="bot",
            charset="utf8"
        )
        db_cursor = db.cursor()

    admin_id = message.data[16:]

    # Получение даты и времени
    date_all = datetime.datetime.fromtimestamp(message.message.date)

    date = date_all.strftime("%Y-%m-%d")
    time = date_all.strftime("%H:%M:%S")

    # Получение баланса админа
    sql = "SELECT balance FROM users WHERE id_user={}".format(admin_id)
    db_cursor.execute(sql)

    admin_balance = db_cursor.fetchone()[0]


    sql = "SELECT client_id FROM clients WHERE admin_id={} AND payment={}".format(admin_id,0)
    db_cursor.execute(sql)

    clients = db_cursor.fetchall()

    clients_text_list = []

    for client in clients:
        clients_text_list.append('№' + str(client[0]))

    clients_text = ', '.join(clients_text_list)


    # Добавление в базу оплаты
    sql = "INSERT INTO payments (client_id,admin_id,paid_sum,date,time) VALUES (%s,%s,%s,%s,%s)"
    val = (clients_text, admin_id, admin_balance, date, time)
    db_cursor.execute(sql,val)
    db.commit()

    # Обнуление баланса
    sql = "UPDATE users SET balance=0 WHERE id_user={}".format(admin_id)
    db_cursor.execute(sql)
    db.commit()

    # Внесение информации об оплате в базу клиентов
    sql = "UPDATE clients SET payment=1 WHERE admin_id={}".format(admin_id)
    db_cursor.execute(sql)
    db.commit()

    bot.send_message(text="Выплата прозведена", chat_id=message.message.chat.id,
                     reply_markup=return_keyboard())


@bot.callback_query_handler(func=lambda message: message.data == 'return')
def return_to_menu(message):
    menu(message.message)


@bot.callback_query_handler(func=lambda message: message.data[:23] == 'start_work_with_client_')
def start_work_with_client(message):

    global db, db_cursor
    try:
        db.ping(True)
    except Exception:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="rootuser16713",
            db="bot",
            charset="utf8"
        )
        db_cursor = db.cursor()

    client_id = message.data[23:]


    # Получение id старого админа
    sql = "SELECT admin_id FROM clients WHERE client_id={}".format(client_id)
    db_cursor.execute(sql)

    old_adm_id = db_cursor.fetchone()[0]


    # Получение имени нового админа
    sql = "SELECT local_name FROM users WHERE id_user={}".format(message.message.chat.id)
    db_cursor.execute(sql)

    admin_name = db_cursor.fetchone()[0]

    # Отправление уведомления старому админу
    bot.send_message(text="Клиент №{} перешел к администратору {}".format(client_id, admin_name),
                     chat_id=old_adm_id)

    # Обновление статуса клиента
    sql = "UPDATE clients SET status=0 WHERE client_id={}".format(client_id)
    db_cursor.execute(sql)
    db.commit()

    # Обновление статуса оплаты клиента
    sql = "UPDATE clients SET payment={} WHERE client_id={}".format(0,client_id)
    db_cursor.execute(sql)
    db.commit()

    # Установка нового администратора клиенту
    sql = "UPDATE clients SET admin_id={} WHERE client_id={}".format(message.message.chat.id, client_id)
    db_cursor.execute(sql)
    db.commit()

    bot.send_message(text="Начата работа с клиентом №{}!".format(client_id),
                     chat_id=message.message.chat.id,
                     reply_markup=return_keyboard())


@bot.callback_query_handler(func=lambda message: message.data[:15] == 'set_specialist_')
def set_specialist_options(message):
    client_id = message.data[15:]
    bot.send_message(text="Выберите способ назначения специалиста",
                     chat_id=message.message.chat.id,
                     reply_markup=set_spec_keyboard(client_id))


@bot.callback_query_handler(func=lambda message: message.data[:19] == 'send_order_to_chat_')
def send_order_to_chat(message):

    global db, db_cursor
    try:
        db.ping(True)
    except Exception:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="rootuser16713",
            db="bot",
            charset="utf8"
        )
        db_cursor = db.cursor()

    client_id = message.data[19:]
    sql = "SELECT phone FROM clients WHERE client_id={}".format(client_id)
    db_cursor.execute(sql)
    phone = db_cursor.fetchone()[0]
    bot.send_message(text="Выберите город",
                     chat_id=message.message.chat.id,
                     reply_markup=locations_keyboard(phone))


@bot.callback_query_handler(func=lambda message: message.data[:12] == 'set_by_hand_')
def set_spec_by_hand(message):
    client_id = message.data[12:]
    bot.send_message(text="Выберите специалиста",
                     chat_id=message.message.chat.id,
                     reply_markup=spec_list_keyboard(client_id))


@bot.callback_query_handler(func=lambda message: message.data[:8] == 'spec_id_')
def set_spec_from_admin(message):

    global db, db_cursor
    try:
        db.ping(True)
    except Exception:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="rootuser16713",
            db="bot",
            charset="utf8"
        )
        db_cursor = db.cursor()

    spec_id = message.data.split('_')[2]
    client_id = message.data.split('_')[3]

    # Обновление статуса клиента
    sql = "UPDATE clients SET status=0 WHERE client_id={}".format(client_id)
    db_cursor.execute(sql)
    db.commit()

    sql = "UPDATE clients SET specialist={} WHERE client_id={}".format(spec_id, client_id)
    db_cursor.execute(sql)
    db.commit()

    sql = "UPDATE clients SET payment={} WHERE client_id={}".format(0,client_id)
    db_cursor.execute(sql)
    db.commit()



    # Отправка уведомления специалисту
    order_body = get_order_body(client_id)

    bot.send_message(text="Вам назначен клиент №{}\n\n"
                         "{}".format(client_id,order_body),
                    chat_id=spec_id)

    # Имя специалиста
    sql = "SELECT local_name FROM users WHERE id_user={}".format(spec_id)
    db_cursor.execute(sql)

    spec_name = db_cursor.fetchone()[0]

    # Уведомление админа
    bot.send_message(text="Клиент №{} отправлен специалисту {}".format(client_id,spec_name),
                     chat_id=message.message.chat.id,reply_markup=return_keyboard())




@bot.callback_query_handler(func=lambda message: message.data[:20] == 'get_payment_history')
def get_payment_history(message):

    global db, db_cursor
    try:
        db.ping(True)
    except Exception:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="rootuser16713",
            db="bot",
            charset="utf8"
        )
        db_cursor = db.cursor()

    sql = "SELECT * FROM payments WHERE admin_id={} AND paid_sum>{} ORDER BY date,time".format(message.message.chat.id,0)
    db_cursor.execute(sql)

    payment_history = db_cursor.fetchall()

    if len(payment_history) == 0:
        bot.send_message(text="У вас пока не было выплат", chat_id=message.message.chat.id,
                         reply_markup=return_keyboard())
        return

    counter = 1

    for payment in payment_history:
        client_id = payment[1]
        paid_sum = payment[3]
        date = payment[4].strftime("%Y-%m-%d")
        time = str(payment[5])
        bot.send_message(text="#{}\n"
                              "Клиент: {}\n"
                              "Выплачено: {}\n"
                              "Дата: {}\n"
                              "Время: {}\n".format(counter,client_id,paid_sum,date,time),
                         chat_id=message.message.chat.id)
        counter += 1

    bot.send_message(text="Вернуться в главное меню", chat_id=message.message.chat.id,
                     reply_markup=return_keyboard())






def next_five_clients_kb():
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(telebot.types.InlineKeyboardButton(text="Дальше", callback_data='next'))
    return keyboard


def spec_list_keyboard(client_id):

    global db, db_cursor
    try:
        db.ping(True)
    except Exception:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="rootuser16713",
            db="bot",
            charset="utf8"
        )
        db_cursor = db.cursor()

    # Список специалистов
    sql = "SELECT local_name,id_user FROM users WHERE status='specialist'"
    db_cursor.execute(sql)

    spec_list = db_cursor.fetchall()

    keyboard = telebot.types.InlineKeyboardMarkup()

    for spec in spec_list:
        spec_name = str(spec[0])
        spec_id = spec[1]
        keyboard.add(telebot.types.InlineKeyboardButton(text=spec_name,
                                                        callback_data="spec_id_{}_{}".format(spec_id, client_id)))

    return keyboard


def set_spec_keyboard(client_id):
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(telebot.types.InlineKeyboardButton(text="Отправить заказ в чат", callback_data='send_order_to_chat_{}'.format(client_id)))
    keyboard.add(telebot.types.InlineKeyboardButton(text="Назначить специалиста вручную",
                                                    callback_data='set_by_hand_{}'.format(client_id)))
    return keyboard


def base_client_keyboard(client_id):
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(telebot.types.InlineKeyboardButton(text="Начать работу с клиентом",
                                                    callback_data='start_work_with_client_{}'.format(client_id)))
    keyboard.add(telebot.types.InlineKeyboardButton(text="Назначить специалиста",
                                                    callback_data="set_specialist_{}".format(client_id)))
    return keyboard


def approve_payment_kb(admin_id):
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(telebot.types.InlineKeyboardButton(text="Подтвердить выплату",
                                                    callback_data='approve_payment_{}'.format(admin_id)))
    return keyboard


def deal_keyboard(client_id, price):
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(telebot.types.InlineKeyboardButton(text="Да", callback_data='yes_{}_{}'.format(client_id, price)))
    keyboard.add(telebot.types.InlineKeyboardButton(text="Нет", callback_data='no_{}_{}'.format(client_id, price)))
    return keyboard


def return_keyboard():
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(telebot.types.InlineKeyboardButton(text="🔙", callback_data='return'))
    return keyboard


def client_keyboard_adm(client_id):
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(telebot.types.InlineKeyboardButton(text="⏳ Получить историю клиента",
                                                    callback_data='client_history_{}'.format(client_id)))
    keyboard.add(telebot.types.InlineKeyboardButton(text="💬 Добавить комментарий",
                                                    callback_data='add_comment_{}'.format(client_id)))
    keyboard.add(telebot.types.InlineKeyboardButton(text='❌ Отказ', callback_data='refuse_{}'.format(client_id)))
    return keyboard


def client_keyboard_spec(client_id):
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(telebot.types.InlineKeyboardButton(text="⏳ Получить историю клиента",
                                                    callback_data='client_history_{}'.format(client_id)))
    keyboard.add(telebot.types.InlineKeyboardButton(text="💬 Добавить комментарий",
                                                    callback_data='add_comment_{}'.format(client_id)))
    keyboard.add(telebot.types.InlineKeyboardButton(text='❌ Отказ', callback_data='refuse_{}'.format(client_id)))
    keyboard.add(
        telebot.types.InlineKeyboardButton(text="🤝 Создать сделку", callback_data='make_deal_{}'.format(client_id)))
    return keyboard


def admin_keyboard():
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(telebot.types.InlineKeyboardButton(text="➕ Добавить клиента", callback_data='add_client'))
    keyboard.add(telebot.types.InlineKeyboardButton(text="💼 Мои клиенты", callback_data='my_clients_adm'))
    keyboard.add(telebot.types.InlineKeyboardButton(text="⬇️💰 Заказать выплату", callback_data='get_payment'))
    keyboard.add(
        telebot.types.InlineKeyboardButton(text="⏳💰 Получить историю выплат", callback_data='get_payment_history'))
    return keyboard


def accept_client(phone):
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(telebot.types.InlineKeyboardButton(text="Принять", callback_data='accept_{}'.format(phone)))
    return keyboard


def specialist_keyboard():
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(telebot.types.InlineKeyboardButton(text="🛠 Мои клиенты", callback_data='my_clients_spec'))
    return keyboard


def locations_keyboard(phone):

    global db, db_cursor
    try:
        db.ping(True)
    except Exception:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="rootuser16713",
            db="bot",
            charset="utf8"
        )
        db_cursor = db.cursor()

    sql = "SELECT client_id FROM clients WHERE phone={}".format(phone)
    db_cursor.execute(sql)

    client_id = db_cursor.fetchone()[0]

    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(telebot.types.InlineKeyboardButton(text="🏙 Москва", callback_data='city_moscow_{}'.format(phone)))
    keyboard.add(telebot.types.InlineKeyboardButton(text="🏙 Санкт-Петербург", callback_data='city_petersburg_{}'.format(phone)))
    keyboard.add(telebot.types.InlineKeyboardButton(text="🏙 Воронеж", callback_data='city_voronezh_{}'.format(phone)))
    keyboard.add(telebot.types.InlineKeyboardButton(text="🏙 Краснодар", callback_data='city_krasnodar_{}'.format(phone)))
    keyboard.add(telebot.types.InlineKeyboardButton(text="🏙 Нижний Новгород", callback_data='city_nnovgorod_{}'.format(phone)))
    keyboard.add(telebot.types.InlineKeyboardButton(text="🏙 Ростов-на-Дону", callback_data='city_rostov_{}'.format(phone)))
    keyboard.add(telebot.types.InlineKeyboardButton(text="🏙 Самара", callback_data='city_samara_{}'.format(phone)))
    keyboard.add(telebot.types.InlineKeyboardButton(text="🏙 Пермь", callback_data='city_perm_{}'.format(phone)))
    keyboard.add(telebot.types.InlineKeyboardButton(text="Назначить специалиста вручную", callback_data='set_by_hand_{}'.format(client_id)))
    return keyboard


bot.enable_save_next_step_handlers(delay=2)
bot.load_next_step_handlers()


@app.route(WEBHOOK_URL_PATH, methods=['GET','POST'])
def webhook():
    print(flask.request.headers)
    if flask.request.headers.get('content-type') == 'application/json':
        json_string = flask.request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        print('You NOT made it!')
        flask.abort(403)


bot.remove_webhook()

time.sleep(1)

bot.set_webhook(url=WEBHOOK_URL_BASE+WEBHOOK_URL_PATH,
                certificate=open(WEBHOOK_SSL_CERT, 'r'))


app.run(
    host=WEBHOOK_LISTEN,
    port=WEBHOOK_PORT,
    ssl_context=(WEBHOOK_SSL_CERT,WEBHOOK_SSL_PRIV),
    debug=True
)

"""
if __name__ == '__main__':
    bot.polling(none_stop=True)
"""