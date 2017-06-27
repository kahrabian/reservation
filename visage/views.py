import psycopg2 as pg
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponseBadRequest
from django.shortcuts import render
from django.conf import settings


def home(request):
    if 'email' not in request.session:
        return HttpResponseRedirect(reverse('authentication:login'))
    elif request.session.get('is_admin', False):
        return HttpResponseRedirect(reverse('visage:schedule'))
    elif not request.session.get('is_admin', False):
        return HttpResponseRedirect(reverse('visage:selfs_list'))


def selfs_list(request):
    if 'email' not in request.session:
        return HttpResponseRedirect(reverse('authentication:login'))

    if request.session.get('is_admin', False):
        return HttpResponseRedirect(reverse('visage:home'))

    if request.method == 'GET':
        email = request.session.get('email')

        conn = pg.connect(**settings.DSN)
        conn.autocommit = True
        curs = conn.cursor()

        curs.execute('SELECT name FROM self')
        selfs = curs.fetchall()

        curs.execute('SELECT balance FROM auth WHERE email=%s', (email,))
        credit = curs.fetchone()[0]

        curs.close()
        conn.close()

        return render(request, 'selfs_list.html', {'selfs': selfs, 'credit': credit, 'is_admin': False})
    else:
        return HttpResponseBadRequest('Unsupported method!')


def charge_credit(request):
    if 'email' not in request.session:
        return HttpResponseRedirect(reverse('authentication:login'))

    if request.session.get('is_admin', False):
        return HttpResponseRedirect(reverse('visage:home'))

    if request.method == 'GET':
        email = request.session.get('email')

        conn = pg.connect(**settings.DSN)
        conn.autocommit = True
        curs = conn.cursor()

        curs.execute('SELECT balance FROM auth WHERE email=%s', (email,))
        credit = curs.fetchone()[0]

        curs.close()
        conn.close()
        return render(request, 'charge_credit.html', {'credit': credit, 'is_admin': False})
    elif request.method == 'POST':
        email = request.session.get('email')
        charge = request.POST.getlist('credit')[0]

        conn = pg.connect(**settings.DSN)
        conn.autocommit = True
        curs = conn.cursor()

        if int(charge) <= 0:
            curs.execute('SELECT balance FROM auth WHERE email=%s', (email,))
            credit = curs.fetchone()[0]

            curs.close()
            conn.close()
            return render(request, 'charge_credit.html', {
                'credit': credit, 'error': 'مقدار افزایش اعتبار باید مثبت باشد!', 'is_admin': False
            })

        curs.execute('UPDATE auth SET balance=balance+%s WHERE email=%s', (charge, email))
        curs.close()
        conn.close()
        return HttpResponseRedirect(reverse('visage:charge_credit'))
    else:
        return HttpResponseBadRequest('Unsupported method!')


def reservation_list(request, sname):
    if 'email' not in request.session:
        return HttpResponseRedirect(reverse('authentication:login'))

    if request.session.get('is_admin', False):
        return HttpResponseRedirect(reverse('visage:home'))

    if request.method == 'GET':
        email = request.session.get('email')

        conn = pg.connect(**settings.DSN)
        conn.autocommit = True
        curs = conn.cursor()

        curs.execute('SELECT balance FROM auth WHERE email=%s', (email,))
        credit = curs.fetchone()[0]

        curs.execute('SELECT address, description FROM self WHERE name=%s', (sname,))
        address, description = curs.fetchone()

        curs.execute(
            """
            SELECT to_char(sf.due_date, 'YYYY-MM-DD'), f.name, f.description, f.price, coalesce(r.count, 0)
            FROM (self_food AS sf LEFT JOIN reserved AS r ON sf.sname = r.sname 
                AND sf.fname = r.fname 
                AND sf.due_date = r.due_date 
                AND (email=%s OR email IS NULL)), food AS f
            WHERE sf.due_date >= CURRENT_DATE::DATE
                AND sf.due_date <= CURRENT_DATE::DATE + '6 day'::INTERVAL
                AND sf.sname=%s
                AND sf.fname=f.name
            ORDER BY sf.due_date
            """, (email, sname)
        )
        choices = curs.fetchall()

        curs.close()
        conn.close()
        return render(request, 'reservation_list.html', {
            'credit': credit, 'sname': sname, 'address': address, 'description': description, 'choices': choices,
            'is_admin': False
        })
    elif request.method == 'POST':
        email = request.session.get('email')
        warn = False
        for k, v in request.POST.items():
            if k == 'csrfmiddlewaretoken' or int(v) <= 0:
                continue
            sname, fname, due_date = k.split('#')
            count = int(v)

            conn = pg.connect(**settings.DSN)
            conn.autocommit = True
            curs = conn.cursor()

            curs.execute('SELECT balance FROM auth WHERE email=%s', (email,))
            credit = curs.fetchone()[0]

            curs.execute('SELECT price FROM food WHERE name=%s', (fname,))
            fprice = curs.fetchone()[0]

            curs.execute(
                'SELECT count FROM self_food WHERE sname=%s AND fname=%s AND due_date=%s', (sname, fname, due_date)
            )
            fcount = int(curs.fetchone()[0])

            if credit < fprice * count or fcount < count:
                warn = True
            else:
                curs.execute('UPDATE auth SET balance=balance-%s WHERE email=%s', (fprice * count, email))
                curs.execute('UPDATE self_food SET count=count-%s WHERE fname=%s', (count, fname))
                curs.execute(
                    """
                    INSERT INTO reserved VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT ON CONSTRAINT reserved_pkey
                    DO UPDATE SET count=reserved.count+%s
                    """, (email, sname, fname, due_date, count, count)
                )

            curs.close()
            conn.close()
        if warn:
            conn = pg.connect(**settings.DSN)
            conn.autocommit = True
            curs = conn.cursor()

            curs.execute('SELECT balance FROM auth WHERE email=%s', (email,))
            credit = curs.fetchone()[0]

            curs.execute('SELECT address, description FROM self WHERE name=%s', (sname,))
            address, description = curs.fetchone()

            curs.execute(
                """
                SELECT to_char(sf.due_date, 'YYYY-MM-DD'), f.name, f.description, f.price, coalesce(r.count, 0)
                FROM (self_food AS sf LEFT JOIN reserved AS r ON sf.sname = r.sname 
                    AND sf.fname = r.fname 
                    AND sf.due_date = r.due_date 
                    AND (email=%s OR email IS NULL)), food AS f
                WHERE sf.due_date >= CURRENT_DATE::DATE
                    AND sf.due_date <= CURRENT_DATE::DATE + '6 day'::INTERVAL
                    AND sf.sname=%s
                    AND sf.fname=f.name
                ORDER BY sf.due_date
                """, (email, sname)
            )
            choices = curs.fetchall()

            curs.close()
            conn.close()
            return render(request, 'reservation_list.html', {
                'credit': credit, 'sname': sname, 'address': address, 'description': description, 'choices': choices,
                'warn': 'امکان رزرو غذاهای انتخاب شده وجود ندارد!'
            })
        else:
            return HttpResponseRedirect(reverse('visage:reservation_list', kwargs={'sname': sname}))
    else:
        return HttpResponseBadRequest('Unsupported method!')


def add_food(request):
    if 'email' not in request.session:
        return HttpResponseRedirect(reverse('authentication:login'))

    if not request.session.get('is_admin', False):
        return HttpResponseRedirect(reverse('visage:home'))

    if request.method == 'GET':
        email = request.session.get('email')

        conn = pg.connect(**settings.DSN)
        conn.autocommit = True
        curs = conn.cursor()

        curs.execute('SELECT balance FROM auth WHERE email=%s', (email,))
        credit = curs.fetchone()[0]

        curs.close()
        conn.close()
        return render(request, 'add_food.html', {'credit': credit, 'is_admin': True})
    elif request.method == 'POST':
        name = request.POST.getlist('name')[0]
        price = request.POST.getlist('price')[0]
        description = request.POST.getlist('description')[0]

        conn = pg.connect(**settings.DSN)
        conn.autocommit = True
        curs = conn.cursor()

        curs.execute(
            """
            INSERT INTO food VALUES (%s, %s, %s)
            ON CONFLICT ON CONSTRAINT food_pkey
            DO UPDATE SET price=%s, description=%s
            """, (name, price, description, price, description)
        )

        curs.close()
        conn.close()
        return HttpResponseRedirect(reverse('visage:add_food'))
    else:
        return HttpResponseBadRequest('Unsupported method!')


def add_self(request):
    if 'email' not in request.session:
        return HttpResponseRedirect(reverse('authentication:login'))

    if not request.session.get('is_admin', False):
        return HttpResponseRedirect(reverse('visage:home'))

    if request.method == 'GET':
        email = request.session.get('email')

        conn = pg.connect(**settings.DSN)
        conn.autocommit = True
        curs = conn.cursor()

        curs.execute('SELECT balance FROM auth WHERE email=%s', (email,))
        credit = curs.fetchone()[0]

        curs.close()
        conn.close()
        return render(request, 'add_self.html', {'credit': credit, 'is_admin': True})
    elif request.method == 'POST':
        name = request.POST.getlist('name')[0]
        address = request.POST.getlist('address')[0]
        description = request.POST.getlist('description')[0]

        conn = pg.connect(**settings.DSN)
        conn.autocommit = True
        curs = conn.cursor()

        curs.execute(
            """
            INSERT INTO self VALUES (%s, %s, %s)
            ON CONFLICT ON CONSTRAINT self_pkey
            DO UPDATE SET address=%s, description=%s
            """, (name, address, description, address, description)
        )

        curs.close()
        conn.close()
        return HttpResponseRedirect(reverse('visage:add_self'))
    else:
        return HttpResponseBadRequest('Unsupported method!')


def schedule(request):
    if 'email' not in request.session:
        return HttpResponseRedirect(reverse('authentication:login'))

    if not request.session.get('is_admin', False):
        return HttpResponseRedirect(reverse('visage:home'))

    if request.method == 'GET':
        email = request.session.get('email')

        conn = pg.connect(**settings.DSN)
        conn.autocommit = True
        curs = conn.cursor()

        curs.execute('SELECT balance FROM auth WHERE email=%s', (email,))
        credit = curs.fetchone()[0]

        curs.execute('SELECT name FROM food')
        foods = curs.fetchall()

        curs.execute('SELECT name FROM self')
        selfs = curs.fetchall()

        curs.close()
        conn.close()
        return render(request, 'schedule.html', {'credit': credit, 'is_admin': True, 'foods': foods, 'selfs': selfs})
    elif request.method == 'POST':
        sname = request.POST.getlist('self')[0]
        fname = request.POST.getlist('food')[0]
        due_date = request.POST.getlist('due_date')[0]
        count = request.POST.getlist('count')[0]

        conn = pg.connect(**settings.DSN)
        conn.autocommit = True
        curs = conn.cursor()

        curs.execute(
            """
            INSERT INTO self_food VALUES (%s, %s, %s, %s)
            ON CONFLICT ON CONSTRAINT self_food_pkey
            DO UPDATE SET count=%s
            """, (sname, fname, due_date, count, count)
        )

        curs.close()
        conn.close()
        return HttpResponseRedirect(reverse('visage:schedule'))
    else:
        return HttpResponseBadRequest('Unsupported method!')
