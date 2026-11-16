import os
from django.db import models

class CourtBooking(models.Model):
    customer_name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=20)
    venue_name = models.CharField(max_length=255, default='มหาวิทยาลัยศรีปทุม (SPU Badminton Arena)')
    court_number = models.CharField(max_length=50)
    booking_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    equipment_summary = models.TextField(blank=True, null=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    class Meta:
        db_table = 'CourtBookings'
        # ถ้าอยู่บน Render ให้สร้างตารางอัตโนมัติ (True) แต่ถ้าอยู่ในเครื่องให้ใช้ตารางเดิมใน SSMS (False)
        managed = 'DATABASE_URL' in os.environ

    def __str__(self):
        return f"{self.customer_name} - {self.court_number}"