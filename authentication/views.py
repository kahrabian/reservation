import psycopg2 as pg
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponseBadRequest
from django.shortcuts import render
from django.conf import settings


def index(request):
    if 'email' not in request.session:
        return HttpResponseRedirect(reverse('authentication:login'))
    else:
        return HttpResponseRedirect(reverse('visage:home'))


def singup(request):
    if 'email' in request.session:
        return HttpResponseRedirect(reverse('visage:home'))

    if request.method == 'GET':
        return render(request, 'signup.html', {})
    elif request.method == 'POST':
        email = request.POST.getlist('email')[0]
        password = request.POST.getlist('password')[0]
        fname = request.POST.getlist('fname')[0]
        lname = request.POST.getlist('lname')[0]

        conn = pg.connect(**settings.DSN)
        conn.autocommit = True
        curs = conn.cursor()

        curs.execute('SELECT COUNT(*) FROM auth WHERE email=%s', (email,))
        if curs.fetchone()[0] == 0:
            curs.execute('INSERT INTO auth VALUES (%s, %s, %s, %s)', (email, password, fname, lname))
            curs.close()
            conn.close()
            return HttpResponseRedirect(reverse('visage:home'))
        else:
            curs.close()
            conn.close()
            return render(request, 'signup.html', {'error': 'کاربر با مشخصات داده شده وجود دارد!'})
    else:
        return HttpResponseBadRequest('Unsupported method!')


def login(request):
    if 'email' in request.session:
        return HttpResponseRedirect(reverse('visage:home'))

    if request.method == 'GET':
        return render(request, 'login.html', {})
    elif request.method == 'POST':
        email = request.POST.getlist('email')[0]
        password = request.POST.getlist('password')[0]

        conn = pg.connect(**settings.DSN)
        conn.autocommit = True
        curs = conn.cursor()

        curs.execute('SELECT COUNT(*) FROM auth WHERE email=%s AND password=%s', (email, password))
        if curs.fetchone()[0] == 0:
            curs.close()
            conn.close()
            return render(request, 'login.html', {'error': 'کاربر با مشخصات داده شده وجود ندارد!'})
        else:
            curs.execute('SELECT is_admin FROM auth WHERE email=%s', (email,))
            request.session['email'] = email
            request.session['is_admin'] = curs.fetchone()[0]

            curs.close()
            conn.close()
            return HttpResponseRedirect(reverse('visage:home'))
    else:
        return HttpResponseBadRequest('Unsupported method!')


def logout(request):
    if 'email' not in request.session:
        return HttpResponseRedirect(reverse('authentication:login'))

    if request.method == 'GET':
        request.session.pop('email')
        request.session.pop('is_admin')
        return HttpResponseRedirect(reverse('authentication:login'))
    else:
        return HttpResponseBadRequest('Unsupported method!')
