from visage import views
from django.conf.urls import url

urlpatterns = [
    url(r'^$', views.home, name='home'),
    url(r'^selfs_list/$', views.selfs_list, name='selfs_list'),
    url(r'^charge_credit/$', views.charge_credit, name='charge_credit'),
    url(r'^add_food/$', views.add_food, name='add_food'),
    url(r'^add_self/$', views.add_self, name='add_self'),
    url(r'^schedule/$', views.schedule, name='schedule'),
    url(r'^reservation_list/(?P<sname>[A-Za-z0-9._\-آ-ی ]+)/$', views.reservation_list, name='reservation_list'),
]
