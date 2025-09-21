from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import base64
import math
from datetime import datetime, timedelta
from functools import wraps
import os
from werkzeug.utils import secure_filename
import hashlib
import hmac
import urllib.parse
from datetime import datetime


app = Flask(__name__)
app.secret_key = "secret_key_123"  

# ------------------- KẾT NỐI DATABASE -------------------
def get_db_connection():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",       
        password="DNoHz137@",      
        database="clinicscheduler",   
        auth_plugin='mysql_native_password'
    )
    return conn

# ------------------- DECORATORS -------------------
# Bảo vệ route cần đăng nhập
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash("Vui lòng đăng nhập để tiếp tục.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# Bảo vệ route admin
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'admin':
            flash("Bạn không có quyền truy cập.", "danger")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated
#---------------Nhận diên id ----------------------
def get_current_user_id():
    return session.get('user_id')
# ------------------- TRANG CHỦ -------------------
@app.route("/")
def index():
    return render_template("index.html")

# ------------------- ĐĂNG NHẬP -------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM nguoidung WHERE username=%s", (username,))
        user = cur.fetchone()
        conn.close()

        if user:
            if check_password_hash(user['password'], password):
                # Lưu session
                session['user_id'] = user['idnguoidung']
                session['username'] = user['username']
                session['role'] = user['role']

                flash(f"Xin chào {user['username']}!", "success")

                # Phân quyền
                if user['role'].lower() == 'admin':  # tránh case-sensitive
                    return redirect(url_for('admin_dashboard'))
                else:
                    return redirect(url_for('index'))
            else:
                flash("Mật khẩu không đúng.", "danger")
        else:
            flash("Username không tồn tại.", "danger")

    return render_template('login.html')

# ------------------- ĐĂNG KÝ -------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hoten = request.form.get('hoten')
        email = request.form.get('email')
        hashed_pw = generate_password_hash(password)

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            # Chỉ tạo user bình thường
            cur.execute("""
                INSERT INTO nguoidung (username, password, hoten, email, role)
                VALUES (%s, %s, %s, %s, 'user')
            """, (username, hashed_pw, hoten, email))
            conn.commit()
            flash("Đăng ký thành công! Bạn có thể đăng nhập.", "success")
            return redirect(url_for('login'))
        except mysql.connector.IntegrityError:
            flash("Username hoặc email đã tồn tại.", "danger")
        finally:
            conn.close()

    return render_template('register.html')

# ------------------- ĐĂNG XUẤT -------------------
@app.route('/logout')
def logout():
    session.clear()
    flash("Bạn đã đăng xuất.", "success")
    return redirect(url_for('index'))

# ------------------- ADMIN -------------------
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    return render_template('admin/admin_dashboard.html')

@app.route('/admin/users')
@admin_required
def admin_manage_users():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM nguoidung")
    users = cur.fetchall()
    conn.close()
    return render_template('admin/manage_users.html', users=users)

@app.route("/admin/doctors")
@admin_required
def admin_manage_doctors():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)     # dictionary=True để trả về dict
    cur.execute("SELECT idBacSi, tenBacSi, chuyenKhoa FROM BacSi ORDER BY idBacSi DESC")
    doctors = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("admin/manage_doctors.html", doctors=doctors)


UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/admin/doctors/add", methods=["GET", "POST"])
def admin_add_doctor():
    if request.method == "POST":
        # Lấy dữ liệu từ form
        ten_bac_si = request.form.get("tenBacSi")
        chuyen_khoa = request.form.get("chuyenKhoa")
        chuc_vu = request.form.get("chucVu")
        trinh_do = request.form.get("trinhDo")
        kinh_nghiem = request.form.get("kinhNghiem", 0)
        dia_chi = request.form.get("diaChiPhongKham")
        description = request.form.get("description")
        certifications = request.form.get("certifications")

        # xử lý file ảnh
        file = request.files.get("hinhAnh")
        image_path = None
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(save_path)
            image_path = f"uploads/{filename}"  # lưu path tương đối vào DB

        # lưu vào database
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO BacSi 
            (tenBacSi, chuyenKhoa, chucVu, trinhDo, kinhNghiem, diaChiPhongKham, GioiThieu, ChungChi, hinhAnh, danhGia)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (ten_bac_si, chuyen_khoa, chuc_vu, trinh_do, kinh_nghiem, dia_chi, description, certifications, image_path, 0)
        )
        conn.commit()
        cur.close()
        conn.close()

        flash("Thêm bác sĩ thành công!", "success")
        return redirect(url_for("admin_manage_doctors"))

    # GET -> render form
    return render_template("admin/add_doctor.html")


@app.route('/admin/doctor/edit/<int:doctor_id>', methods=['GET', 'POST'])
def admin_edit_doctor(doctor_id):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    # Lấy thông tin bác sĩ hiện tại
    cur.execute("SELECT * FROM BacSi WHERE idBacSi=%s", (doctor_id,))
    doctor = cur.fetchone()
    if not doctor:
        flash("Bác sĩ không tồn tại", "danger")
        return redirect(url_for('admin_manage_doctors'))

    if request.method == 'POST':
        # Lấy dữ liệu từ form
        name = request.form['name']
        specialty = request.form['specialty']
        position = request.form.get('position', '')
        address = request.form.get('address', '')
        experience = request.form.get('experience', 0)
        description = request.form.get('description', '')
        education = request.form.get('education', '')
        certifications = request.form.get('certifications', '')

        # Xử lý upload ảnh
        image_file = request.files.get('image')
        if image_file and image_file.filename != '':
            upload_folder = os.path.join('static', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            image_filename = image_file.filename
            image_path = os.path.join(upload_folder, image_filename)
            image_file.save(image_path)
            # Cập nhật cả ảnh vào MySQL
            cur.execute("""
                UPDATE BacSi
                SET tenBacSi=%s, chuyenKhoa=%s, chucVu=%s, diaChiPhongKham=%s,
                    kinhNghiem=%s, GioiThieu=%s, HocVan=%s, ChungChi=%s, hinhAnh=%s
                WHERE idBacSi=%s
            """, (name, specialty, position, address, experience, description,
                  education, certifications, 'uploads/' + image_filename, doctor_id))
        else:
            # Không đổi ảnh, update các trường khác
            cur.execute("""
                UPDATE BacSi
                SET tenBacSi=%s, chuyenKhoa=%s, chucVu=%s, diaChiPhongKham=%s,
                    kinhNghiem=%s, GioiThieu=%s, HocVan=%s, ChungChi=%s
                WHERE idBacSi=%s
            """, (name, specialty, position, address, experience, description,
                  education, certifications, doctor_id))

        conn.commit()
        flash("Cập nhật thông tin bác sĩ thành công", "success")
        return redirect(url_for('admin_manage_doctors'))

    return render_template('admin/edit_doctor.html', doctor=doctor)

@app.route('/admin/doctors/delete/<int:doctor_id>', methods=['POST', 'GET'])
@admin_required
def admin_delete_doctor(doctor_id):
    conn = get_db_connection()
    cur = conn.cursor()

    # Kiểm tra bác sĩ tồn tại
    cur.execute("SELECT * FROM BacSi WHERE idBacSi=%s", (doctor_id,))
    doctor = cur.fetchone()

    if doctor:
        try:
            # Xoá tất cả lịch hẹn liên quan trước
            cur.execute("DELETE FROM LichHen WHERE idBacSi=%s", (doctor_id,))

            # Sau đó xoá bác sĩ
            cur.execute("DELETE FROM BacSi WHERE idBacSi=%s", (doctor_id,))
            conn.commit()

            flash("Đã xoá bác sĩ và các lịch hẹn liên quan", "success")
        except mysql.connector.Error as e:
            conn.rollback()
            flash(f"Lỗi khi xoá bác sĩ: {e}", "danger")
    else:
        flash("Bác sĩ không tồn tại.", "warning")

    cur.close()
    conn.close()
    return redirect(url_for('admin_manage_doctors'))


# ------------------- USER -------------------
# Danh sách bác sĩ
@app.route('/doctors')
def doctors():
    page = request.args.get('page', 1, type=int)
    per_page = 4
    offset = (page - 1) * per_page

    search_name = request.args.get('q', '', type=str).strip()
    search_specialty = request.args.get('specialty', '', type=str).strip()
    search_address = request.args.get('address', '', type=str).strip()

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    # Dropdown filter
    cur.execute("SELECT DISTINCT chuyenKhoa FROM BacSi ORDER BY chuyenKhoa ASC")
    specialties = [row['chuyenKhoa'] for row in cur.fetchall()]

    cur.execute("SELECT DISTINCT diaChiPhongKham FROM BacSi ORDER BY diaChiPhongKham ASC")
    addresses = [row['diaChiPhongKham'] for row in cur.fetchall()]

    # Điều kiện WHERE
    conditions = []
    params = []
    if search_name:
        conditions.append("tenBacSi LIKE %s")
        params.append(f"%{search_name}%")
    if search_specialty:
        conditions.append("chuyenKhoa LIKE %s")
        params.append(f"%{search_specialty}%")
    if search_address:
        conditions.append("diaChiPhongKham LIKE %s")
        params.append(f"%{search_address}%")

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    # Tổng số bản ghi
    cur.execute(f"SELECT COUNT(*) AS total FROM BacSi {where_clause}", tuple(params))
    total = cur.fetchone()['total']
    total_pages = math.ceil(total / per_page) if total else 1

    # Lấy dữ liệu trang hiện tại
    cur.execute(f"""
        SELECT * FROM BacSi
        {where_clause}
        ORDER BY idBacSi ASC
        LIMIT %s OFFSET %s
    """, tuple(params + [per_page, offset]))
    doctors = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "doctor.html",
        doctors=doctors,
        page=page,
        total_pages=total_pages,
        specialties=specialties,
        addresses=addresses,
        search_name=search_name,
        search_specialty=search_specialty,
        search_address=search_address
    )


# Chi tiết bác sĩ
@app.route('/doctor/<int:doctor_id>')
def doctor_detail(doctor_id):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM BacSi WHERE idBacSi = %s", (doctor_id,))
    doctor = cur.fetchone()
    
    if not doctor:
        flash("Bác sĩ không tồn tại", "warning")
        cur.close()
        conn.close()
        return redirect(url_for('doctors'))

    # --- Xử lý ảnh ---
    if doctor.get("hinhAnh"):
        # doctor['hinhAnh'] là path trong static/uploads/ hoặc tương tự
        doctor["image_url"] = url_for("static", filename=doctor["hinhAnh"])
    else:
        doctor["image_url"] = url_for("static", filename="images/default.png")

    # --- Lấy tuần hiển thị ---
    week_start_str = request.args.get('week_start')
    if week_start_str:
        try:
            week_start = datetime.strptime(week_start_str, "%Y-%m-%d")
        except ValueError:
            week_start = datetime.today()
    else:
        week_start = datetime.today()

    # Bắt đầu tuần là thứ 2
    week_start = week_start - timedelta(days=week_start.weekday())
    week_end = week_start + timedelta(days=6)
    days = [week_start + timedelta(days=i) for i in range(7)]
    hours = list(range(8, 18))  # giờ làm việc 8-17h

    # --- Lấy lịch làm việc ---
    schedule_map = {}
    cur.execute("SELECT ngayHen, buoiTrongNgay FROM LichHen WHERE idBacSi = %s", (doctor_id,))
    for row in cur.fetchall():
        d = row['ngayHen'].date()
        h_list = schedule_map.get(d, [])
        if row['buoiTrongNgay'] == "Sáng":
            h_list.extend(range(8, 12))
        elif row['buoiTrongNgay'] == "Chiều":
            h_list.extend(range(13, 18))
        schedule_map[d] = h_list

    cur.close()
    conn.close()

    # --- Tuần trước / tuần sau ---
    prev_week = (week_start - timedelta(days=7)).strftime("%Y-%m-%d")
    next_week = (week_start + timedelta(days=7)).strftime("%Y-%m-%d")
    week_label = f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d, %Y')}"

    # --- Trả dữ liệu cho template ---
    return render_template(
        "doctor_detail.html",
        doctor=doctor,
        days=days,
        hours=hours,
        schedule_map=schedule_map,
        prev_week=prev_week,
        next_week=next_week,
        week_label=week_label
    )

# Đặt lịch khám
@app.route("/booking", methods=["GET", "POST"])
@login_required
def booking():
    if request.method == "POST":
        id_bacsi = request.form.get("idBacSi")
        ngay_hen = request.form.get("ngayHen")
        thoi_gian = request.form.get("thoiGianHen")
        ly_do = request.form.get("lyDoKham")
        ten_benh_nhan = request.form.get("tenBenhNhan")
        tien_dat_coc = 300000  # mặc định
        user_id = session.get("user_id")

        # Giả lập thanh toán thành công
        thanh_toan_thanh_cong = True
        if not thanh_toan_thanh_cong:
            flash("Thanh toán thất bại. Vui lòng thử lại.", "danger")
            return redirect(url_for("booking"))

        # Lưu lịch hẹn
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO LichHen 
            (idBacSi, idNguoiDung, tenBenhNhan, ngayHen, thoiGianHen, lyDoKham, tienDatCoc, vnpay_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'Đã thanh toán')
        """, (id_bacsi, user_id, ten_benh_nhan, ngay_hen, thoi_gian, ly_do, tien_dat_coc))
        conn.commit()
        cursor.close()
        conn.close()

        flash(f"Đặt lịch thành công! Đã thanh toán {tien_dat_coc} VND.", "success")
        return redirect(url_for("appointments"))


    # Lấy danh sách bác sĩ
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT idBacSi, tenBacSi, chuyenKhoa FROM BacSi")
    bacsi_list = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("booking.html", bacsi_list=bacsi_list)


# Danh sách cuộc hẹn của user
@app.route('/appointments', endpoint='appointments')
@login_required
def appointments():
    user_id = session.get('user_id')

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT lh.idLichHen, lh.tenBenhNhan, lh.ngayHen, lh.thoiGianHen, lh.lyDoKham,
               lh.tienDatCoc, lh.vnpay_status,
               bs.tenBacSi, bs.chuyenKhoa, bs.diaChiPhongKham
        FROM LichHen lh
        JOIN BacSi bs ON lh.idBacSi = bs.idBacSi
        WHERE lh.idNguoiDung = %s
        ORDER BY lh.ngayHen, lh.thoiGianHen
    """, (user_id,))
    appointments = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("appointments.html", appointments=appointments)


# Chi tiết cuộc hẹn
@app.route('/appointment/<int:id>')
@login_required
def appointment_detail(id):
    user_id = session.get('user_id')

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT lh.idLichHen, lh.tenBenhNhan, lh.ngayHen, lh.thoiGianHen, lh.lyDoKham,
               lh.tienDatCoc, lh.vnpay_status,
               bs.tenBacSi, bs.chuyenKhoa, bs.diaChiPhongKham
        FROM LichHen lh
        JOIN BacSi bs ON lh.idBacSi = bs.idBacSi
        WHERE lh.idLichHen = %s AND lh.idNguoiDung = %s
    """, (id, user_id))
    appointment = cur.fetchone()
    cur.close()
    conn.close()

    if not appointment:
        flash("Cuộc hẹn không tồn tại hoặc không thuộc về bạn.", "danger")
        return redirect(url_for('appointments'))

    return render_template("appointment_detail.html", appointment=appointment)


#----------thanhtoan-----------------
@app.route('/pay/<int:appointment_id>')
def pay(appointment_id):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM LichHen WHERE idLichHen=%s", (appointment_id,))
    appointment = cur.fetchone()
    cur.close()
    conn.close()

    if not appointment:
        flash("Cuộc hẹn không tồn tại", "danger")
        return redirect(url_for('appointments'))

    # Thông tin VNPAY
    vnp_url = "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html"
    vnp_returnurl = "https://abcd1234.ngrok.io/vnpay_return"  # URL public của bạn
    vnp_TmnCode = "YOUR_TMN_CODE"
    vnp_HashSecret = "YOUR_HASH_SECRET"

    vnp_Params = {
        "vnp_Version": "2.1.0",
        "vnp_Command": "pay",
        "vnp_TmnCode": vnp_TmnCode,
        "vnp_Amount": str(appointment['tienDatCoc'] * 100),  # VNPAY tính theo đơn vị 100đ
        "vnp_CurrCode": "VND",
        "vnp_TxnRef": str(appointment_id),
        "vnp_OrderInfo": f"Đặt cọc cuộc hẹn {appointment_id}",
        "vnp_OrderType": "other",
        "vnp_Locale": "vn",
        "vnp_ReturnUrl": vnp_returnurl,
        "vnp_IpAddr": request.remote_addr,
        "vnp_CreateDate": datetime.now().strftime("%Y%m%d%H%M%S")
    }

    # Sắp xếp tham số và tạo query string
    sorted_params = sorted(vnp_Params.items())
    query_string = "&".join(f"{k}={urllib.parse.quote_plus(v)}" for k, v in sorted_params)
    hash_data = "&".join(f"{k}={v}" for k, v in sorted_params)
    vnp_secure_hash = hmac.new(bytes(vnp_HashSecret, 'utf-8'), bytes(hash_data, 'utf-8'), hashlib.sha512).hexdigest()
    payment_url = f"{vnp_url}?{query_string}&vnp_SecureHash={vnp_secure_hash}"

    return redirect(payment_url)
#-------------callback---------
@app.route('/vnpay_return')
def vnpay_return():
    vnp_ResponseCode = request.args.get('vnp_ResponseCode')
    txn_ref = request.args.get('vnp_TxnRef')

    conn = get_db_connection()
    cur = conn.cursor()
    if vnp_ResponseCode == "00":
        # Thanh toán thành công
        cur.execute("UPDATE LichHen SET vnpay_status=%s WHERE idLichHen=%s", ("Đã thanh toán", txn_ref))
        flash("Thanh toán thành công!", "success")
    else:
        cur.execute("UPDATE LichHen SET vnpay_status=%s WHERE idLichHen=%s", ("Thanh toán thất bại", txn_ref))
        flash("Thanh toán thất bại!", "danger")
    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for('appointments'))
#-------------------- Bác Sĩ --------------------
@app.route('/doctor/profile', methods=['GET', 'POST'])
def doctor_profile():
    if 'doctor_id' not in session:
        flash("Vui lòng đăng nhập", "warning")
        return redirect(url_for('login'))

    doctor_id = session['doctor_id']
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM BacSi WHERE idBacSi = %s", (doctor_id,))
    doctor = cur.fetchone()

    if not doctor:
        flash("Bác sĩ không tồn tại", "warning")
        cur.close()
        conn.close()
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Lấy dữ liệu từ form
        tenBacSi = request.form.get("tenBacSi")
        chuyenKhoa = request.form.get("chuyenKhoa")
        chucVu = request.form.get("chucVu")
        kinhNghiem = request.form.get("kinhNghiem") or 0
        diaChiPhongKham = request.form.get("diaChiPhongKham")
        description = request.form.get("description")
        education = request.form.get("education")
        certifications = request.form.get("certifications")

        # Xử lý file ảnh nếu upload
        file = request.files.get("hinhAnh")
        image_path = doctor.get("hinhAnh")  # giữ ảnh cũ nếu không upload
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(save_path)
            image_path = f"uploads/{filename}"

        # Cập nhật DB
        cur.execute("""
            UPDATE BacSi 
            SET tenBacSi=%s, chuyenKhoa=%s, chucVu=%s, kinhNghiem=%s,
                diaChiPhongKham=%s, description=%s, education=%s, certifications=%s,
                hinhAnh=%s
            WHERE idBacSi=%s
        """, (tenBacSi, chuyenKhoa, chucVu, kinhNghiem, diaChiPhongKham,
              description, education, certifications, image_path, doctor_id))
        conn.commit()
        flash("Cập nhật thông tin thành công!", "success")

        # load lại doctor sau khi cập nhật
        cur.execute("SELECT * FROM BacSi WHERE idBacSi = %s", (doctor_id,))
        doctor = cur.fetchone()

    # Xử lý ảnh để template hiển thị
    if doctor.get("hinhAnh"):
        doctor["image_url"] = url_for("static", filename=doctor["hinhAnh"])
    else:
        doctor["image_url"] = url_for("static", filename="images/default.png")

    # --- Lấy lịch làm việc ---
    week_start_str = request.args.get('week_start')
    if week_start_str:
        try:
            week_start = datetime.strptime(week_start_str, "%Y-%m-%d")
        except ValueError:
            week_start = datetime.today()
    else:
        week_start = datetime.today()
    week_start = week_start - timedelta(days=week_start.weekday())
    week_end = week_start + timedelta(days=6)
    days = [week_start + timedelta(days=i) for i in range(7)]
    hours = list(range(8, 18))

    schedule_map = {}
    cur.execute("SELECT ngayHen, buoiTrongNgay FROM LichHen WHERE idBacSi=%s", (doctor_id,))
    for row in cur.fetchall():
        d = row['ngayHen'].date()
        h_list = schedule_map.get(d, [])
        if row['buoiTrongNgay'] == "Sáng":
            h_list.extend(range(8, 12))
        elif row['buoiTrongNgay'] == "Chiều":
            h_list.extend(range(13, 18))
        schedule_map[d] = h_list

    cur.close()
    conn.close()

    prev_week = (week_start - timedelta(days=7)).strftime("%Y-%m-%d")
    next_week = (week_start + timedelta(days=7)).strftime("%Y-%m-%d")
    week_label = f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d, %Y')}"

    return render_template(
        "doctor_profile.html",
        doctor=doctor,
        days=days,
        hours=hours,
        schedule_map=schedule_map,
        prev_week=prev_week,
        next_week=next_week,
        week_label=week_label
    )



# ------------------- RUN APP -------------------
if __name__ == "__main__":
    app.run(debug=True)
