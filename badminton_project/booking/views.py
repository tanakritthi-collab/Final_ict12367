from django.shortcuts import render, redirect, get_object_or_404
from .models import CourtBooking
from django.db.models import Q
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate, logout
from datetime import datetime, timedelta, timezone
import json

EQUIPMENT_CATALOG = {
    'shoes': {'name': 'เช่ารองเท้าแบดมินตัน (1 คู่)', 'price': 60},
    'shuttlecock': {'name': 'ซื้อลูกแบดมินตัน (4 ลูก)', 'price': 40},
}

def get_thai_today():
    tz_th = timezone(timedelta(hours=7))
    return datetime.now(tz_th).date()

def get_7_days_options():
    today = get_thai_today()
    thai_days = ['จันทร์', 'อังคาร', 'พุธ', 'พฤหัสบดี', 'ศุกร์', 'เสาร์', 'อาทิตย์']
    days_list = []
    for i in range(7):
        d = today + timedelta(days=i)
        day_name = "วันนี้" if i == 0 else ("พรุ่งนี้" if i == 1 else f"วัน{thai_days[d.weekday()]}")
        days_list.append({
            'value': d.strftime('%Y-%m-%d'),
            'label': f"{d.strftime('%d/%m/%Y')} ({day_name})"
        })
    return days_list

# 1. หน้าแรก
def index(request):
    search_query = request.GET.get('search', '')
    all_customer_names = CourtBooking.objects.values_list('customer_name', flat=True).distinct()
    
    if request.user.is_authenticated:
        if request.user.is_staff:
            base_qs = CourtBooking.objects.all()
        else:
            base_qs = CourtBooking.objects.filter(customer_name=request.user.username)
    else:
        base_qs = CourtBooking.objects.none()

    if search_query and request.user.is_authenticated:
        bookings_qs = base_qs.filter(
            Q(customer_name__icontains=search_query) | 
            Q(court_number__icontains=search_query)
        ).order_by('-booking_date')
    else:
        bookings_qs = base_qs.order_by('-booking_date')

    booking_extras = request.session.get('booking_extras', {})
    bookings_with_extras = []
    for b in bookings_qs:
        extra = booking_extras.get(str(b.id), {'items_text': 'ไม่มีอุปกรณ์เสริม', 'total_price': 150, 'venue': 'มหาวิทยาลัยศรีปทุม', 'username': b.customer_name})
        b.venue_name = extra.get('venue', 'มหาวิทยาลัยศรีปทุม')
        b.display_username = extra.get('username', b.customer_name)
        b.equipment_text = extra['items_text']
        b.total_price = extra['total_price']
        bookings_with_extras.append(b)

    latest_receipt = None
    just_booked = request.session.pop('just_booked', False)
    if request.user.is_authenticated:
        receipt_id = request.session.get(f'receipt_user_{request.user.id}')
        if receipt_id:
            latest_receipt = CourtBooking.objects.filter(pk=receipt_id).first()
            if latest_receipt:
                extra = booking_extras.get(str(latest_receipt.id), {'items_text': 'ไม่มีอุปกรณ์เสริม', 'total_price': 150, 'venue': 'มหาวิทยาลัยศรีปทุม', 'username': request.user.username})
                latest_receipt.venue_name = extra.get('venue', 'มหาวิทยาลัยศรีปทุม')
                latest_receipt.display_username = extra.get('username', request.user.username)
                latest_receipt.equipment_text = extra['items_text']
                latest_receipt.total_price = extra['total_price']

    today = get_thai_today()
    all_bookings_qs = CourtBooking.objects.all()
    total_bookings_count = all_bookings_qs.count()
    today_bookings_count = all_bookings_qs.filter(booking_date=today).count()
    
    max_daily_slots = 24
    occupancy_rate = round((today_bookings_count / max_daily_slots) * 100, 1) if max_daily_slots > 0 else 0
    
    total_revenue = 0
    for b in all_bookings_qs:
        extra = booking_extras.get(str(b.id), {'total_price': 150})
        total_revenue += extra['total_price']
    
    context = {
        'bookings': bookings_with_extras, 
        'search_query': search_query,
        'all_customer_names': all_customer_names,
        'latest_receipt': latest_receipt,
        'just_booked': just_booked,
        'total_bookings_count': total_bookings_count,
        'today_bookings_count': today_bookings_count,
        'occupancy_rate': occupancy_rate,
        'total_revenue': total_revenue,
    }
    return render(request, 'booking/index.html', context)

def get_booked_slots_json():
    today = get_thai_today()
    end_date = today + timedelta(days=6)
    qs = CourtBooking.objects.filter(booking_date__range=[today, end_date])
    booked_list = []
    for b in qs:
        booked_list.append({
            'date': b.booking_date.strftime('%Y-%m-%d'),
            'court': str(b.court_number),
            'start': b.start_time.strftime('%H:%M'),
            'end': b.end_time.strftime('%H:%M'),
        })
    return json.dumps(booked_list)

# 2. สร้างการจอง
def create_booking(request):
    if not request.user.is_authenticated:
        messages.error(request, 'กรุณาล็อกอินก่อนจองสนาม')
        return redirect('index')

    all_customer_names = CourtBooking.objects.values_list('customer_name', flat=True).distinct()
    date_options = get_7_days_options()
    booked_slots_json = get_booked_slots_json()

    if request.method == "POST":
        username_val = request.user.username
        phone = request.POST.get('phone')
        venue = request.POST.get('venue')
        court = request.POST.get('court')
        date = request.POST.get('date')
        start = request.POST.get('start')
        end = request.POST.get('end')
        
        shoes_qty = int(request.POST.get('shoes_qty', 0))
        shuttle_qty = int(request.POST.get('shuttle_qty', 0))

        is_booked = CourtBooking.objects.filter(
            court_number=court,
            booking_date=date,
            start_time__lt=end,
            end_time__gt=start
        ).exists()

        if is_booked:
            return render(request, 'booking/form.html', {
                'error': 'ขออภัย สนามและช่วงเวลานี้ถูกจองไปแล้ว กรุณาเลือกเวลาอื่น',
                'data': request.POST,
                'all_customer_names': all_customer_names,
                'date_options': date_options,
                'booked_slots_json': booked_slots_json,
            })

        new_booking = CourtBooking.objects.create(
            customer_name=username_val,
            phone_number=phone,
            court_number=court,
            booking_date=date,
            start_time=start,
            end_time=end
        )

        base_price = 150
        extra_price = 0
        item_labels = []

        if shoes_qty > 0:
            cost = shoes_qty * 60
            extra_price += cost
            item_labels.append(f"รองเท้าแบด {shoes_qty} คู่ (+{cost}฿)")

        if shuttle_qty > 0:
            cost = shuttle_qty * 40
            extra_price += cost
            item_labels.append(f"ลูกแบด {shuttle_qty * 4} ลูก (+{cost}฿)")

        total_price = base_price + extra_price
        items_text = ", ".join(item_labels) if item_labels else "ไม่มีอุปกรณ์เสริม"

        booking_extras = request.session.get('booking_extras', {})
        booking_extras[str(new_booking.id)] = {
            'items_text': items_text,
            'total_price': total_price,
            'venue': venue,
            'username': username_val,
        }
        request.session['booking_extras'] = booking_extras
        request.session[f'receipt_user_{request.user.id}'] = new_booking.id
        request.session['just_booked'] = True
        return redirect('index')
        
    return render(request, 'booking/form.html', {
        'data': {},
        'all_customer_names': all_customer_names,
        'date_options': date_options,
        'booked_slots_json': booked_slots_json,
    })

# 3. แก้ไขข้อมูล
@staff_member_required
def update_booking(request, booking_id):
    booking = get_object_or_404(CourtBooking, pk=booking_id)
    all_customer_names = CourtBooking.objects.values_list('customer_name', flat=True).distinct()
    date_options = get_7_days_options()
    booked_slots_json = get_booked_slots_json()
    
    booking_extras = request.session.get('booking_extras', {})

    if request.method == "POST":
        username_val = booking.customer_name
        court = request.POST.get('court')
        venue = request.POST.get('venue')
        date = request.POST.get('date')
        start = request.POST.get('start')
        end = request.POST.get('end')
        
        shoes_qty = int(request.POST.get('shoes_qty', 0))
        shuttle_qty = int(request.POST.get('shuttle_qty', 0))

        is_booked = CourtBooking.objects.filter(
            court_number=court,
            booking_date=date,
            start_time__lt=end,
            end_time__gt=start
        ).exclude(pk=booking_id).exists()

        if is_booked:
            return render(request, 'booking/form.html', {
                'error': 'ไม่สามารถเปลี่ยนเป็นเวลานี้ได้ เนื่องจากมีการจองอื่นทับซ้อนอยู่',
                'booking': booking,
                'all_customer_names': all_customer_names,
                'date_options': date_options,
                'booked_slots_json': booked_slots_json,
            })

        booking.court_number = court
        booking.booking_date = date
        booking.start_time = start
        booking.end_time = end
        booking.save()

        base_price = 150
        extra_price = 0
        item_labels = []

        if shoes_qty > 0:
            cost = shoes_qty * 60
            extra_price += cost
            item_labels.append(f"รองเท้าแบด {shoes_qty} คู่ (+{cost}฿)")

        if shuttle_qty > 0:
            cost = shuttle_qty * 40
            extra_price += cost
            item_labels.append(f"ลูกแบด {shuttle_qty * 4} ลูก (+{cost}฿)")

        booking_extras[str(booking.id)] = {
            'items_text': ", ".join(item_labels) if item_labels else "ไม่มีอุปกรณ์เสริม",
            'total_price': base_price + extra_price,
            'venue': venue,
            'username': username_val,
        }
        request.session['booking_extras'] = booking_extras

        messages.info(request, "แก้ไขข้อมูลสำเร็จ!")
        return redirect('index')
        
    return render(request, 'booking/form.html', {
        'booking': booking,
        'all_customer_names': all_customer_names,
        'date_options': date_options,
        'booked_slots_json': booked_slots_json,
    })

# 4. ยกเลิก / ลบการจอง (อนุญาตให้ลูกค้าเจ้าของบัญชี หรือแอดมิน ลบได้)
def delete_booking(request, booking_id):
    if not request.user.is_authenticated:
        messages.error(request, 'กรุณาล็อกอินก่อนดำเนินการ')
        return redirect('index')

    booking = get_object_or_404(CourtBooking, pk=booking_id)

    # ถ้าไม่ใช่แอดมิน และไม่ใช่เจ้าของรายการจองนี้ จะไม่ได้รับอนุญาตให้ลบ
    if not request.user.is_staff and booking.customer_name != request.user.username:
        messages.error(request, 'คุณไม่มีสิทธิ์ยกเลิกการจองนี้')
        return redirect('index')

    booking.delete()
    messages.warning(request, "ยกเลิกการจองเรียบร้อยแล้ว")
    return redirect('index')

def contact(request):
    return render(request, 'booking/contact.html')

def register_customer(request):
    if request.method == "POST":
        username = request.POST.get('reg_username', '').strip()
        password = request.POST.get('reg_password', '')
        confirm_password = request.POST.get('reg_confirm_password', '')

        if not username or not password:
            messages.error(request, 'กรุณากรอกชื่อผู้ใช้และรหัสผ่านให้ครบถ้วน')
            return redirect('/admin/login/')

        if password != confirm_password:
            messages.error(request, 'รหัสผ่านทั้งสองช่องไม่ตรงกัน')
            return redirect('/admin/login/')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'ชื่อผู้ใช้นี้มีคนใช้งานแล้ว กรุณาใช้ชื่ออื่น')
            return redirect('/admin/login/')

        user = User.objects.create_user(username=username, password=password)
        login(request, user)
        messages.success(request, f'สมัครสมาชิกสำเร็จ! ยินดีต้อนรับคุณ {username}')
        return redirect('index')

    return redirect('/admin/login/')

def login_customer(request):
    if request.method == "POST":
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'ยินดีต้อนรับคุณ {user.username}')
            return redirect('index')
        else:
            messages.error(request, 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง กรุณาลองใหม่อีกครั้ง')
            return redirect('/admin/login/')

    return redirect('/admin/login/')

def logout_view(request):
    logout(request)
    messages.info(request, "ออกจากระบบเรียบร้อยแล้ว")
    return redirect('index')
