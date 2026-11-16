from django.contrib import admin
from .models import CourtBooking

@admin.register(CourtBooking)
class CourtBookingAdmin(admin.ModelAdmin):
    # กำหนดให้หน้าลิสต์รายการโชว์หัวข้ออะไรบ้าง
    list_display = ('customer_name', 'court_number', 'booking_date', 'start_time')
    # เพิ่มระบบค้นหา (ตามเงื่อนไขโจทย์)
    search_fields = ('customer_name', 'phone_number')