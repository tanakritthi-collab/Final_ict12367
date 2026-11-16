from django.contrib import admin
from django.urls import path
from booking import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # หน้าหลัก (List & Search)
    path('', views.index, name='index'),

    # เพิ่มการจอง
    path('create/', views.create_booking, name='create_booking'),

    # แก้ไขการจอง
    path('update/<int:booking_id>/', views.update_booking, name='update_booking'),

    # ลบการจอง
    path('delete/<int:booking_id>/', views.delete_booking, name='delete_booking'),

    # หน้าติดต่อ
    path('contact/', views.contact, name='contact'),

    # สมัครสมาชิกสำหรับลูกค้า
    path('register/', views.register_customer, name='register'),

    # เข้าสู่ระบบ (ทั้งลูกค้าและแอดมิน)
    path('login-user/', views.login_customer, name='login_user'),
]
