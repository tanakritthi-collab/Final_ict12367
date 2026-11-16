from django.contrib import admin
from django.urls import path
from booking import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('create/', views.create_booking, name='create_booking'),
    path('update/<int:booking_id>/', views.update_booking, name='update_booking'),
    path('delete/<int:booking_id>/', views.delete_booking, name='delete_booking'),
    path('contact/', views.contact, name='contact'),
    path('register/', views.register_customer, name='register'),
    path('login-user/', views.login_customer, name='login_user'),
    path('logout/', views.logout_view, name='logout'), # <--- เพิ่มบรรทัดนี้
]
