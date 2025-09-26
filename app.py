from flask import Flask, render_template, request, redirect, url_for, session, flash
from config import get_db_connection
import hashlib
from datetime import datetime
import json
from datetime import datetime, date
from datetime import timedelta
from datetime import datetime, timedelta
import json
from flask import render_template, request
from flask import Flask, render_template, request, session
from math import ceil

app = Flask(__name__)
app.secret_key = "secret_key_123"

def get_conn_or_abort():
    conn = get_db_connection()
    if not conn:
        flash("Lỗi kết nối CSDL. Kiểm tra config.py và MySQL server.", "danger")
        return None
    return conn

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = hashlib.sha256(request.form["password"].encode()).hexdigest()

        conn = get_conn_or_abort()
        if conn is None:
            return render_template("login.html")

        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM nguoidung WHERE username=%s AND password=%s", (username, password))
        user = cur.fetchone()

        cur.close()
        conn.close()

        if user:
            session["user"] = {
                "id_nguoidung": user["id_nguoidung"],
                "username": user["username"],
                "role": user["role"],
                "email": user.get("email")
            }
            # cố gắng tìm bản ghi benhnhan có ten_benhnhan = username (nếu khi register bạn điền)
            try:
                conn2 = get_db_connection()
                cur2 = conn2.cursor()
                cur2.execute("SELECT id_benhnhan FROM benhnhan WHERE ten_benhnhan=%s LIMIT 1", (username,))
                r = cur2.fetchone()
                if r:
                    session["id_benhnhan"] = r[0]
                cur2.close()
                conn2.close()
            except Exception:
                # bỏ qua nếu không tìm được
                pass

            flash("Đăng nhập thành công!", "success")
            if user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))
            elif user["role"] == "doctor":
                return redirect(url_for("doctor_dashboard"))
            else:
                return redirect(url_for("index"))
        else:
            flash("Sai tài khoản hoặc mật khẩu!", "danger")
    return render_template("login.html")


# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        email = request.form.get("email", "").strip()
        password = hashlib.sha256(request.form["password"].encode()).hexdigest()
        ten_benhnhan = request.form.get("ten_benhnhan", username).strip()
        sodienthoai = request.form.get("sodienthoai", "").strip()

        conn = get_conn_or_abort()
        if conn is None:
            return render_template("register.html")

        try:
            cur = conn.cursor()
            # tao nguoidung
            cur.execute("INSERT INTO nguoidung (username, password, email, role) VALUES (%s, %s, %s, %s)",
                        (username, password, email, "user"))
            id_user = cur.lastrowid

            # tao benhnhan (khong co lien ket id_nguoidung theo schema goc)
            cur.execute("INSERT INTO benhnhan (ten_benhnhan, sodienthoai) VALUES (%s, %s)",
                        (ten_benhnhan, sodienthoai))
            id_benhnhan = cur.lastrowid

            conn.commit()
            cur.close()
            flash("Đăng ký thành công! Vui lòng đăng nhập.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            conn.rollback()
            flash("Lỗi khi đăng ký: " + str(e), "danger")
            return render_template("register.html")
        finally:
            conn.close()

    return render_template("register.html")


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.pop("user", None)
    session.pop("id_benhnhan", None)
    flash("Đã đăng xuất.", "info")
    return redirect(url_for("index"))


# ---------------- TRANG CHỦ ----------------
@app.route("/")
def index():
    return render_template("index.html", datetime=datetime)


# ---------------- DANH SÁCH BÁC SĨ ----------------

@app.route("/doctor")
def doctor_list():
    conn = get_conn_or_abort()
    if conn is None:
        return render_template("doctor/list.html", doctors=[], page=1, total_pages=1,
                               specialties=[], addresses=[], search_name='', search_specialty='', search_address='')

    # Tham số tìm kiếm
    search_name = request.args.get('q', '').strip()
    search_specialty = request.args.get('specialty', '').strip()
    search_address = request.args.get('address', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 4
    offset = (page - 1) * per_page

    cur = conn.cursor(dictionary=True)

    # Lấy danh sách chuyên khoa và địa chỉ để hiển thị dropdown
    cur.execute("SELECT DISTINCT chuyen_khoa FROM bacsi ORDER BY chuyen_khoa ASC")
    specialties = [row['chuyen_khoa'] for row in cur.fetchall()]

    cur.execute("SELECT DISTINCT dia_chi FROM bacsi ORDER BY dia_chi ASC")
    addresses = [row['dia_chi'] for row in cur.fetchall()]

    # Điều kiện WHERE động
    conditions = []
    params = []
    if search_name:
        conditions.append("ten_bacsi LIKE %s")
        params.append(f"%{search_name}%")
    if search_specialty:
        conditions.append("chuyen_khoa LIKE %s")
        params.append(f"%{search_specialty}%")
    if search_address:
        conditions.append("dia_chi LIKE %s")
        params.append(f"%{search_address}%")
    
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    # Tổng số bản ghi
    cur.execute(f"SELECT COUNT(*) AS total FROM bacsi {where_clause}", tuple(params))
    total = cur.fetchone()['total']
    total_pages = ceil(total / per_page) if total else 1

    # Lấy dữ liệu trang hiện tại
    cur.execute(f"""
        SELECT id_bacsi, ten_bacsi, kinh_nghiem, hocvan, mo_ta, id_user, hinhanh, chuyen_khoa, dia_chi
        FROM bacsi
        {where_clause}
        ORDER BY id_bacsi ASC
        LIMIT %s OFFSET %s
    """, tuple(params + [per_page, offset]))
    doctors = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "doctor/list.html",
        doctors=doctors,
        page=page,
        total_pages=total_pages,
        specialties=specialties,
        addresses=addresses,
        search_name=search_name,
        search_specialty=search_specialty,
        search_address=search_address
    )


# ---------------- CHI TIẾT BÁC SĨ ----------------

@app.route("/doctor/<int:doctor_id>")
def doctor_detail(doctor_id):
    conn = get_conn_or_abort()
    if conn is None:
        return render_template(
            "doctor/detail.html",
            doctor=None,
            lichlam={},
            week_dates=[],
            hours=range(8, 18),
            reviews=[],
            week_offset=0
        )

    cur = conn.cursor(dictionary=True)

    # Lấy thông tin bác sĩ
    cur.execute("""
        SELECT id_bacsi, ten_bacsi, kinh_nghiem, hocvan, mo_ta, id_user, hinhanh, chuyen_khoa, dia_chi
        FROM bacsi
        WHERE id_bacsi=%s
    """, (doctor_id,))
    doctor = cur.fetchone()

    if not doctor:
        cur.close()
        conn.close()
        return render_template(
            "doctor/detail.html",
            doctor=None,
            lichlam={},
            week_dates=[],
            hours=range(8, 18),
            reviews=[],
            week_offset=0
        )

    # Xác định tuần hiển thị
    week_offset = int(request.args.get("week", 0))
    start_of_week = datetime.today() + timedelta(days=week_offset*7)
    week_dates = [start_of_week + timedelta(days=i) for i in range(7)]

    # Chuẩn bị lichlam: mặc định tất cả giờ trống
    lichlam = {d.strftime("%Y-%m-%d"): {h: "free" for h in range(8, 18)} for d in week_dates}

    # Lấy giờ bác sĩ đánh dấu bận (lichlamviec)
    cur.execute("SELECT lichlam FROM lichlamviec WHERE id_bacsi=%s", (doctor_id,))
    for row in cur.fetchall():
        if not row["lichlam"]:
            continue
        try:
            slots = json.loads(row["lichlam"])
            for slot in slots:
                ngay = slot.get("ngay")
                gio_str = slot.get("batdau")
                if not ngay or not gio_str:
                    continue
                gio = int(gio_str.split(":")[0])
                if ngay in lichlam and gio in lichlam[ngay]:
                    lichlam[ngay][gio] = "booked"
        except Exception:
            continue

    # Lấy lịch hẹn đã xác nhận (trang_thai='xac_nhan') → chỉ slot này mới ảnh hưởng lichlam
    cur.execute("""
        SELECT ThoiGianHen 
        FROM lichhen 
        WHERE id_bacsi=%s AND trang_thai='xac_nhan'
    """, (doctor_id,))
    for row in cur.fetchall():
        if row["ThoiGianHen"]:
            ngay = row["ThoiGianHen"].strftime("%Y-%m-%d")
            gio = row["ThoiGianHen"].hour
            if ngay in lichlam and gio in lichlam[ngay] and lichlam[ngay][gio] == "free":
                lichlam[ngay][gio] = "reserved"

    # Lấy review
    cur.execute("""
        SELECT r.id_review, r.so_sao, r.binhluan, r.created_at, u.username
        FROM review r
        LEFT JOIN nguoidung u ON r.id_nguoidung = u.id_nguoidung
        WHERE r.id_bacsi=%s
        ORDER BY r.created_at DESC
    """, (doctor_id,))
    reviews = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "doctor/detail.html",
        doctor=doctor,
        lichlam=lichlam,
        week_dates=week_dates,
        hours=range(8, 18),
        reviews=reviews,
        week_offset=week_offset
    )



# ---------------- ĐẶT LỊCH ----------------
@app.route("/book/<int:doctor_id>", methods=["GET", "POST"])
def book_appointment(doctor_id):
    if "user" not in session or session["user"]["role"] != "user":
        flash("Bạn cần đăng nhập bằng tài khoản user để đặt lịch!", "warning")
        return redirect(url_for("login"))

    conn = get_conn_or_abort()
    if conn is None:
        return redirect(url_for("doctor_detail", doctor_id=doctor_id))

    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id_bacsi, ten_bacsi FROM bacsi WHERE id_bacsi = %s", (doctor_id,))
    doctor = cur.fetchone()
    if not doctor:
        flash("Bác sĩ không tồn tại!", "danger")
        cur.close()
        conn.close()
        return redirect(url_for("index"))

    today_str = date.today().isoformat()  # min date cho template

    if request.method == "POST":
        ngay_hen = request.form.get("ngay_hen", "").strip()
        gio_hen = request.form.get("gio_hen", "").strip()
        ten_benhnhan = request.form.get("ten_benhnhan", "").strip()
        sodienthoai = request.form.get("sodienthoai", "").strip()
        mota = request.form.get("mota", "").strip()

        if not ten_benhnhan:
            flash("Tên bệnh nhân không được để trống!", "warning")
            cur.close()
            conn.close()
            return redirect(url_for("book_appointment", doctor_id=doctor_id))

        if ngay_hen < today_str:
            flash("Ngày hẹn không được chọn ngày quá khứ!", "warning")
            cur.close()
            conn.close()
            return redirect(url_for("book_appointment", doctor_id=doctor_id))

        try:
            ThoiGianHen = datetime.strptime(f"{ngay_hen} {gio_hen}", "%Y-%m-%d %H:%M")
        except ValueError:
            flash("Ngày giờ không hợp lệ!", "danger")
            cur.close()
            conn.close()
            return redirect(url_for("book_appointment", doctor_id=doctor_id))

        # Kiểm tra giờ đã có người đặt trong lichhen, loại trừ các lịch đã hủy
        cur.execute("""
            SELECT id_lichhen 
            FROM lichhen 
            WHERE id_bacsi=%s AND ThoiGianHen=%s AND trang_thai != 'da_huy'
        """, (doctor_id, ThoiGianHen))
        if cur.fetchone():
            flash("Giờ này đã có người đặt, vui lòng chọn giờ khác.", "warning")
            cur.close()
            conn.close()
            return redirect(url_for("book_appointment", doctor_id=doctor_id))

        # Tạo bệnh nhân và lịch hẹn
        try:
            cur.execute("INSERT INTO benhnhan (ten_benhnhan, sodienthoai) VALUES (%s, %s)",
                        (ten_benhnhan, sodienthoai))
            id_benhnhan = cur.lastrowid

            cur.execute("""
                INSERT INTO lichhen (id_bacsi, id_benhnhan, id_nguoidung, ThoiGianHen, mota)
                VALUES (%s, %s, %s, %s, %s)
            """, (doctor_id, id_benhnhan, session["user"]["id_nguoidung"], ThoiGianHen, mota))
            conn.commit()

            flash("Đặt lịch thành công!", "success")
            cur.close()
            conn.close()
            return redirect(url_for("history"))

        except Exception as e:
            conn.rollback()
            cur.close()
            conn.close()
            flash("Lỗi khi đặt lịch: " + str(e), "danger")
            return redirect(url_for("book_appointment", doctor_id=doctor_id))

    cur.close()
    conn.close()
    return render_template("book.html", doctor=doctor, today=today_str)




# ---------------- LỊCH SỬ (USER) ----------------
from datetime import datetime

@app.route("/history")
def history():
    if "user" not in session or session["user"]["role"] != "user":
        return redirect(url_for("login"))

    conn = get_conn_or_abort()
    if conn is None:
        return render_template("history.html", lichhen=[], now=datetime.now())

    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT l.id_lichhen, l.ThoiGianHen, l.trang_thai, b.ten_bacsi, bn.ten_benhnhan
    FROM lichhen l
    LEFT JOIN bacsi b ON l.id_bacsi = b.id_bacsi
    LEFT JOIN benhnhan bn ON l.id_benhnhan = bn.id_benhnhan
    WHERE l.id_nguoidung = %s
    ORDER BY l.id_lichhen DESC
    """, (session["user"]["id_nguoidung"],))
    lichhen = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("history.html", lichhen=lichhen, now=datetime.now())

# ---------------- cancel ----------------
from datetime import datetime

@app.route("/cancel/<int:id_lichhen>")
def cancel_appointment(id_lichhen):
    if "user" not in session or session["user"]["role"] != "user":
        return redirect(url_for("login"))

    conn = get_conn_or_abort()
    if conn is None:
        flash("Lỗi kết nối cơ sở dữ liệu", "danger")
        return redirect(url_for("history"))

    cur = conn.cursor(dictionary=True)
    try:
        # Lấy thông tin lịch hẹn
        cur.execute("""
            SELECT id_bacsi, ThoiGianHen, trang_thai
            FROM lichhen
            WHERE id_lichhen = %s AND id_nguoidung = %s
        """, (id_lichhen, session["user"]["id_nguoidung"]))
        row = cur.fetchone()

        if not row:
            flash("Lịch hẹn không tồn tại hoặc không thuộc quyền của bạn.", "warning")
        else:
            id_bacsi = row['id_bacsi']
            ThoiGianHen = row['ThoiGianHen']
            trang_thai = row['trang_thai']

            # Chỉ hủy nếu lịch chưa hủy và chưa qua
            if ThoiGianHen <= datetime.now():
                flash("Không thể hủy lịch đã qua.", "warning")
            elif trang_thai == "da_huy":
                flash("Lịch này đã bị hủy trước đó.", "info")
            else:
                # 1. Cập nhật trạng thái lichhen
                cur.execute("""
                    UPDATE lichhen
                    SET trang_thai = %s
                    WHERE id_lichhen = %s
                """, ("da_huy", id_lichhen))

                # 2. Cập nhật lichlamviec: xóa slot bận tương ứng
                cur.execute("SELECT lichlam FROM lichlamviec WHERE id_bacsi = %s", (id_bacsi,))
                row_ll = cur.fetchone()
                if row_ll and row_ll['lichlam']:
                    try:
                        slots = json.loads(row_ll['lichlam'])
                        ngay_str = ThoiGianHen.strftime("%Y-%m-%d")
                        gio_hen = ThoiGianHen.hour
                        # Loại bỏ slot trùng ngày và giờ
                        slots = [s for s in slots if not (s.get("ngay") == ngay_str and int(s.get("batdau","0").split(":")[0]) == gio_hen)]
                        # Lưu lại JSON mới
                        cur.execute("UPDATE lichlamviec SET lichlam=%s WHERE id_bacsi=%s", (json.dumps(slots), id_bacsi))
                    except Exception as e:
                        print("Lỗi cập nhật lichlamviec:", e)

                conn.commit()
                flash("Hủy lịch thành công và cập nhật lịch bác sĩ!", "success")

    except Exception as e:
        conn.rollback()
        flash(f"Lỗi khi hủy lịch: {e}", "danger")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for("history"))


# ---------------- REVIEW ----------------
@app.route("/review/<int:doctor_id>", methods=["GET", "POST"])
def review_doctor(doctor_id):
    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        so_sao = int(request.form["so_sao"])
        binhluan = request.form["binhluan"]

        conn = get_conn_or_abort()
        if conn is None:
            return redirect(url_for("doctor_detail", doctor_id=doctor_id))
        cur = conn.cursor()
        cur.execute("INSERT INTO review (id_nguoidung, id_bacsi, so_sao, binhluan) VALUES (%s, %s, %s, %s)",
                    (session["user"]["id_nguoidung"], doctor_id, so_sao, binhluan))
        conn.commit()
        cur.close()
        conn.close()
        flash("Đánh giá thành công!", "success")
        return redirect(url_for("doctor_detail", doctor_id=doctor_id))

    return render_template("review.html", doctor_id=doctor_id)


# ---------------- DASHBOARD ADMIN ----------------
@app.route("/admin")
def admin_dashboard():
    if "user" not in session or session["user"]["role"] != "admin":
        return redirect(url_for("login"))

    conn = get_conn_or_abort()
    if conn is None:
        return render_template("admin/dashboard.html", tong_bacsi=0, tong_benhnhan=0, tong_lichhen=0, tong_nguoidung=0)

    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT COUNT(*) AS tong_bacsi FROM bacsi")
    tong_bacsi = cur.fetchone()["tong_bacsi"]
    cur.execute("SELECT COUNT(*) AS tong_benhnhan FROM benhnhan")
    tong_benhnhan = cur.fetchone()["tong_benhnhan"]
    cur.execute("SELECT COUNT(*) AS tong_lichhen FROM lichhen")
    tong_lichhen = cur.fetchone()["tong_lichhen"]
    cur.execute("SELECT COUNT(*) AS tong_nguoidung FROM nguoidung")
    tong_nguoidung = cur.fetchone()["tong_nguoidung"]
    cur.close()
    conn.close()

    return render_template("admin/dashboard.html",
                           tong_bacsi=tong_bacsi,
                           tong_benhnhan=tong_benhnhan,
                           tong_lichhen=tong_lichhen,
                           tong_nguoidung=tong_nguoidung)

#-----------------Admin/doctors----------------
@app.route("/admin/doctors")
def admin_doctors():
    if "user" not in session or session["user"]["role"] != "admin":
        return redirect(url_for("login"))

    conn = get_conn_or_abort()
    if conn is None:
        return render_template("admin/doctors.html", doctors=[])

    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM bacsi ORDER BY id_bacsi DESC")
    doctors = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("admin/doctors.html", doctors=doctors)

@app.route("/admin/doctors/add", methods=["GET", "POST"])
def admin_doctor_add():
    if "user" not in session or session["user"]["role"] != "admin":
        return redirect(url_for("login"))

    if request.method == "POST":
        # Lấy dữ liệu từ form
        ten_bacsi = request.form.get("ten_bacsi", "").strip()
        kinh_nghiem = request.form.get("kinh_nghiem", "").strip()
        hocvan = request.form.get("hocvan", "").strip()
        mo_ta = request.form.get("mo_ta", "").strip()
        chuyen_khoa = request.form.get("chuyen_khoa", "").strip()  # thêm chuyên khoa
        dia_chi = request.form.get("dia_chi", "").strip()          # thêm địa chỉ
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        # Xử lý upload ảnh
        file = request.files.get("hinhanh")
        hinhanh_filename = None
        if file and file.filename:
            import os
            from werkzeug.utils import secure_filename
            filename = secure_filename(file.filename)
            upload_folder = os.path.join("static/images")
            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)
            hinhanh_filename = f"images/{filename}"  # lưu path tương đối

        # Kiểm tra bắt buộc
        if not ten_bacsi or not username or not password:
            flash("Tên bác sĩ, username và mật khẩu không được để trống!", "warning")
            return redirect(url_for("admin_doctor_add"))

        conn = get_conn_or_abort()
        if conn is None:
            return redirect(url_for("admin_doctors"))

        cur = conn.cursor()
        try:
            import hashlib
            hashed_pass = hashlib.sha256(password.encode()).hexdigest()
            
            # 1. Tạo user bác sĩ
            cur.execute("""
                INSERT INTO nguoidung (username, password, role)
                VALUES (%s, %s, %s)
            """, (username, hashed_pass, "doctor"))
            id_user = cur.lastrowid

            # 2. Tạo bản ghi bác sĩ, lưu chuyên khoa, địa chỉ và ảnh
            cur.execute("""
                INSERT INTO bacsi (ten_bacsi, kinh_nghiem, hocvan, mo_ta, hinhanh, chuyen_khoa, dia_chi, id_user)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (ten_bacsi, kinh_nghiem, hocvan, mo_ta, hinhanh_filename, chuyen_khoa, dia_chi, id_user))

            conn.commit()
            flash("Thêm bác sĩ và tạo tài khoản thành công!", "success")
        except Exception as e:
            conn.rollback()
            flash(f"Lỗi khi thêm bác sĩ: {e}", "danger")
        finally:
            cur.close()
            conn.close()

        return redirect(url_for("admin_doctors"))

    return render_template("admin/doctor_form.html", doctor=None)




@app.route("/admin/doctors/edit/<int:id_bacsi>", methods=["GET", "POST"])
def admin_doctor_edit(id_bacsi):
    if "user" not in session or session["user"]["role"] != "admin":
        return redirect(url_for("login"))

    conn = get_conn_or_abort()
    if conn is None:
        return redirect(url_for("admin_doctors"))

    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM bacsi WHERE id_bacsi=%s", (id_bacsi,))
    doctor = cur.fetchone()

    if not doctor:
        flash("Bác sĩ không tồn tại!", "warning")
        cur.close()
        conn.close()
        return redirect(url_for("admin_doctors"))

    if request.method == "POST":
        ten_bacsi = request.form.get("ten_bacsi", "").strip()
        kinh_nghiem = request.form.get("kinh_nghiem", "").strip()
        hocvan = request.form.get("hocvan", "").strip()
        mo_ta = request.form.get("mo_ta", "").strip()
        hinhanh = request.form.get("hinhanh", "").strip()

        try:
            cur.execute("""
                UPDATE bacsi
                SET ten_bacsi=%s, kinh_nghiem=%s, hocvan=%s, mo_ta=%s, hinhanh=%s
                WHERE id_bacsi=%s
            """, (ten_bacsi, kinh_nghiem, hocvan, mo_ta, hinhanh, id_bacsi))
            conn.commit()
            flash("Cập nhật bác sĩ thành công!", "success")
        except Exception as e:
            conn.rollback()
            flash(f"Lỗi khi cập nhật bác sĩ: {e}", "danger")
        finally:
            cur.close()
            conn.close()
        return redirect(url_for("admin_doctors"))

    cur.close()
    conn.close()
    return render_template("admin/doctor_form.html", doctor=doctor)

@app.route("/admin/doctors/delete/<int:id_bacsi>", methods=["POST"])
def admin_doctor_delete(id_bacsi):
    if "user" not in session or session["user"]["role"] != "admin":
        return redirect(url_for("login"))

    conn = get_conn_or_abort()
    if conn is None:
        return redirect(url_for("admin_doctors"))

    cur = conn.cursor()
    try:
        # Xóa user liên kết trước (nếu cần)
        cur.execute("SELECT id_user FROM bacsi WHERE id_bacsi=%s", (id_bacsi,))
        row = cur.fetchone()
        if row and row[0]:
            cur.execute("DELETE FROM nguoidung WHERE id_nguoidung=%s", (row[0],))

        cur.execute("DELETE FROM bacsi WHERE id_bacsi=%s", (id_bacsi,))
        conn.commit()
        flash("Xóa bác sĩ thành công!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Lỗi khi xóa bác sĩ: {e}", "danger")
    finally:
        cur.close()
        conn.close()
    return redirect(url_for("admin_doctors"))

# ------------------ Admin Patients ------------------
@app.route("/admin/patients")
def admin_patients():
    if "user" not in session or session["user"]["role"] != "admin":
        return redirect(url_for("login"))

    conn = get_conn_or_abort()
    if conn is None:
        return render_template("admin/patients.html", patients=[])

    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM benhnhan ORDER BY id_benhnhan DESC")
    patients = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("admin/patients.html", patients=patients)

# ------------------ Admin Appointments ------------------
@app.route("/admin/appointments")
def admin_appointments():
    if "user" not in session or session["user"]["role"] != "admin":
        return redirect(url_for("login"))

    conn = get_conn_or_abort()
    if conn is None:
        return render_template("admin/appointments.html", appointments=[])

    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT l.id_lichhen, l.ThoiGianHen, l.trang_thai, b.ten_bacsi, bn.ten_benhnhan
        FROM lichhen l
        LEFT JOIN bacsi b ON l.id_bacsi = b.id_bacsi
        LEFT JOIN benhnhan bn ON l.id_benhnhan = bn.id_benhnhan
        ORDER BY l.id_lichhen DESC
    """)
    appointments = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("admin/appointments.html", appointments=appointments)

# ----------------- Admin / Users -----------------
@app.route("/admin/users")
def admin_users():
    if "user" not in session or session["user"]["role"] != "admin":
        return redirect(url_for("login"))

    conn = get_conn_or_abort()
    if conn is None:
        return render_template("admin/users.html", users=[])

    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id_nguoidung, username, role FROM nguoidung ORDER BY id_nguoidung DESC")
    users = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("admin/users.html", users=users)

@app.route("/admin/users/add", methods=["GET", "POST"])
def admin_user_add():
    if "user" not in session or session["user"]["role"] != "admin":
        return redirect(url_for("login"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        role = request.form.get("role", "user")

        if not username or not password:
            flash("Username và mật khẩu không được để trống!", "warning")
            return redirect(url_for("admin_user_add"))

        conn = get_conn_or_abort()
        if conn is None:
            return redirect(url_for("admin_users"))

        cur = conn.cursor()
        try:
            import hashlib
            hashed_pass = hashlib.sha256(password.encode()).hexdigest()
            cur.execute("INSERT INTO nguoidung (username, password, role) VALUES (%s, %s, %s)",
                        (username, hashed_pass, role))
            conn.commit()
            flash("Thêm người dùng thành công!", "success")
        except Exception as e:
            conn.rollback()
            flash(f"Lỗi khi thêm người dùng: {e}", "danger")
        finally:
            cur.close()
            conn.close()

        return redirect(url_for("admin_users"))

    return render_template("admin/user_form.html", user=None)


@app.route("/admin/users/edit/<int:id_nguoidung>", methods=["GET", "POST"])
def admin_user_edit(id_nguoidung):
    if "user" not in session or session["user"]["role"] != "admin":
        return redirect(url_for("login"))

    conn = get_conn_or_abort()
    if conn is None:
        return redirect(url_for("admin_users"))

    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM nguoidung WHERE id_nguoidung=%s", (id_nguoidung,))
    user = cur.fetchone()

    if not user:
        flash("Người dùng không tồn tại!", "warning")
        cur.close()
        conn.close()
        return redirect(url_for("admin_users"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        role = request.form.get("role", user["role"])

        try:
            if password:
                import hashlib
                hashed_pass = hashlib.sha256(password.encode()).hexdigest()
                cur.execute("UPDATE nguoidung SET username=%s, password=%s, role=%s WHERE id_nguoidung=%s",
                            (username, hashed_pass, role, id_nguoidung))
            else:
                cur.execute("UPDATE nguoidung SET username=%s, role=%s WHERE id_nguoidung=%s",
                            (username, role, id_nguoidung))
            conn.commit()
            flash("Cập nhật người dùng thành công!", "success")
        except Exception as e:
            conn.rollback()
            flash(f"Lỗi khi cập nhật người dùng: {e}", "danger")
        finally:
            cur.close()
            conn.close()

        return redirect(url_for("admin_users"))

    cur.close()
    conn.close()
    return render_template("admin/user_form.html", user=user)


@app.route("/admin/users/delete/<int:id_nguoidung>", methods=["POST"])
def admin_user_delete(id_nguoidung):
    if "user" not in session or session["user"]["role"] != "admin":
        return redirect(url_for("login"))

    conn = get_conn_or_abort()
    if conn is None:
        return redirect(url_for("admin_users"))

    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM nguoidung WHERE id_nguoidung=%s", (id_nguoidung,))
        conn.commit()
        flash("Xóa người dùng thành công!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Lỗi khi xóa người dùng: {e}", "danger")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for("admin_users"))

# ---------------------- DASHBOARD BÁC SĨ ----------------------
@app.route("/doctor/dashboard")
def doctor_dashboard():
    if "user" not in session or session["user"]["role"] != "doctor":
        return redirect(url_for("login"))

    conn = get_conn_or_abort()
    if conn is None:
        return render_template("doctor/dashboard.html", lichhen=[], lichlam={}, week_dates=[], hours=range(8,18), week_offset=0)

    cur = conn.cursor(dictionary=True)

    # Lấy id_bacsi
    cur.execute("SELECT id_bacsi FROM bacsi WHERE id_user=%s", (session["user"]["id_nguoidung"],))
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        flash("Bạn chưa có hồ sơ bác sĩ.", "warning")
        return render_template("doctor/dashboard.html", lichhen=[], lichlam={}, week_dates=[], hours=range(8,18), week_offset=0)
    
    id_bacsi = row["id_bacsi"]

    # Lấy lịch hẹn của bác sĩ
    cur.execute("""
        SELECT l.id_lichhen, l.ThoiGianHen, l.trang_thai, l.ghichu,
               bn.ten_benhnhan, u.username AS nguoi_tao
        FROM lichhen l
        LEFT JOIN benhnhan bn ON l.id_benhnhan = bn.id_benhnhan
        LEFT JOIN nguoidung u ON l.id_nguoidung = u.id_nguoidung
        WHERE l.id_bacsi=%s
        ORDER BY l.ThoiGianHen DESC
    """, (id_bacsi,))
    lichhen = cur.fetchall()

    # Tính tuần hiển thị
    week_offset = int(request.args.get("week", 0))
    start_of_week = datetime.today() + timedelta(days=week_offset*7)
    week_dates = [start_of_week + timedelta(days=i) for i in range(7)]
    
    # Tạo lichlam mặc định
    lichlam = {d.strftime("%Y-%m-%d"): {h: "free" for h in range(8,18)} for d in week_dates}

    # Lấy lịch làm việc của bác sĩ
    cur.execute("SELECT lichlam FROM lichlamviec WHERE id_bacsi=%s", (id_bacsi,))
    r = cur.fetchone()
    slots = json.loads(r["lichlam"]) if r and r["lichlam"] else []
    for s in slots:
        ngay = s.get("ngay")
        gio = int(s.get("batdau","0").split(":")[0])
        if ngay in lichlam and gio in lichlam[ngay]:
            lichlam[ngay][gio] = "booked"

    # Đánh dấu các slot đã xác nhận trong lichhen
    for l in lichhen:
        if l["ThoiGianHen"] and l["trang_thai"]=="xac_nhan":
            ngay = l["ThoiGianHen"].strftime("%Y-%m-%d")
            gio = l["ThoiGianHen"].hour
            if ngay in lichlam and gio in lichlam[ngay] and lichlam[ngay][gio]=="free":
                lichlam[ngay][gio] = "reserved"

    cur.close()
    conn.close()

    return render_template("doctor/dashboard.html", lichhen=lichhen, lichlam=lichlam, week_dates=week_dates, hours=range(8,18), week_offset=week_offset)


# ---------------------- CHI TIẾT LỊCH HẸN ----------------------
@app.route("/doctor/lichhen/<int:id_lichhen>")
def doctor_appointment_detail(id_lichhen):
    if "user" not in session or session["user"]["role"]!="doctor":
        return redirect(url_for("login"))

    conn = get_conn_or_abort()
    if conn is None:
        flash("Không kết nối được cơ sở dữ liệu", "danger")
        return redirect(url_for("doctor_dashboard"))

    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT l.id_lichhen, l.ThoiGianHen, l.trang_thai, l.ghichu,
               bn.ten_benhnhan, bn.sodienthoai,
               u.username AS nguoi_tao, u.email
        FROM lichhen l
        LEFT JOIN benhnhan bn ON l.id_benhnhan = bn.id_benhnhan
        LEFT JOIN nguoidung u ON l.id_nguoidung = u.id_nguoidung
        WHERE l.id_lichhen=%s
    """, (id_lichhen,))
    lichhen = cur.fetchone()
    cur.close()
    conn.close()

    if not lichhen:
        flash("Lịch hẹn không tồn tại", "warning")
        return redirect(url_for("doctor_dashboard"))
    
    return render_template("doctor/lichhen_detail.html", lichhen=lichhen)


# ---------------------- CẬP NHẬT GHI CHÚ LỊCH HẸN ----------------------
@app.route("/doctor/lichhen/<int:id_lichhen>/update_note", methods=["POST"])
def doctor_update_appointment_note(id_lichhen):
    if "user" not in session or session["user"]["role"]!="doctor":
        return redirect(url_for("login"))

    ghichu = request.form.get("ghichu","").strip()
    conn = get_conn_or_abort()
    if conn is None:
        flash("Không kết nối cơ sở dữ liệu", "danger")
        return redirect(url_for("doctor_appointment_detail", id_lichhen=id_lichhen))

    cur = conn.cursor()
    try:
        cur.execute("UPDATE lichhen SET ghichu=%s WHERE id_lichhen=%s", (ghichu,id_lichhen))
        conn.commit()
        flash("Cập nhật ghi chú thành công!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Lỗi: {e}", "danger")
    finally:
        cur.close()
        conn.close()
    return redirect(url_for("doctor_appointment_detail", id_lichhen=id_lichhen))


# ---------------------- CẬP NHẬT TRẠNG THÁI LỊCH HẸN ----------------------
@app.route("/doctor/lichhen/<int:id_lichhen>/update", methods=["POST"])
def doctor_update_appointment(id_lichhen):
    if "user" not in session or session["user"]["role"]!="doctor":
        return redirect(url_for("login"))

    trang_thai = request.form.get("trang_thai")  # "xac_nhan" hoặc "da_huy"
    conn = get_conn_or_abort()
    if conn is None:
        return redirect(url_for("doctor_dashboard"))

    cur = conn.cursor(dictionary=True)
    try:
        # Lấy lịch hẹn trước
        cur.execute("SELECT id_bacsi, ThoiGianHen FROM lichhen WHERE id_lichhen=%s", (id_lichhen,))
        row = cur.fetchone()
        if not row:
            flash("Lịch hẹn không tồn tại", "warning")
            return redirect(url_for("doctor_dashboard"))
        id_bacsi = row["id_bacsi"]
        ngay = row["ThoiGianHen"].strftime("%Y-%m-%d")
        gio = row["ThoiGianHen"].strftime("%H:%M")

        # Cập nhật trạng thái lịch hẹn
        cur.execute("UPDATE lichhen SET trang_thai=%s WHERE id_lichhen=%s", (trang_thai, id_lichhen))

        # Lấy lịch làm việc hiện tại
        cur.execute("SELECT lichlam FROM lichlamviec WHERE id_bacsi=%s", (id_bacsi,))
        r = cur.fetchone()
        slots = json.loads(r["lichlam"]) if r and r["lichlam"] else []

        if trang_thai=="xac_nhan":
            # Thêm slot nếu chưa có
            if not any(s["ngay"]==ngay and s["batdau"]==gio for s in slots):
                slots.append({"ngay":ngay,"batdau":gio})
        elif trang_thai=="da_huy":
            # Xóa slot trùng
            slots = [s for s in slots if not (s["ngay"]==ngay and s["batdau"]==gio)]

        # Lưu lại
        if r:
            cur.execute("UPDATE lichlamviec SET lichlam=%s WHERE id_bacsi=%s", (json.dumps(slots), id_bacsi))
        else:
            if trang_thai=="xac_nhan" and slots:
                cur.execute("INSERT INTO lichlamviec (id_bacsi, lichlam) VALUES (%s,%s)", (id_bacsi,json.dumps(slots)))

        conn.commit()
        flash("Cập nhật trạng thái lịch hẹn thành công!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Lỗi: {e}", "danger")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for("doctor_dashboard"))


# ---------------------- LỊCH LÀM VIỆC ----------------------
@app.route("/doctor/lichlamviec", methods=["GET", "POST"])
def doctor_schedule():
    if "user" not in session or session["user"]["role"] != "doctor":
        return redirect(url_for("login"))

    conn = get_conn_or_abort()
    if conn is None:
        return render_template("doctor/lichlamviec.html", slots=[])

    cur = conn.cursor(dictionary=True)
    # Lấy id_bacsi
    cur.execute("SELECT id_bacsi FROM bacsi WHERE id_user=%s", (session["user"]["id_nguoidung"],))
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        flash("Bạn chưa có hồ sơ bác sĩ.", "warning")
        return render_template("doctor/lichlamviec.html", slots=[])

    id_bacsi = row["id_bacsi"]

    if request.method == "POST":
        ngay = request.form.get("ngay", "").strip()
        batdau = request.form.get("batdau", "").strip()
        ketthuc = request.form.get("ketthuc", "").strip()

        if not ngay or not batdau or not ketthuc:
            flash("Ngày, giờ bắt đầu và giờ kết thúc không được để trống.", "warning")
            return redirect(url_for("doctor_schedule"))

        # Thêm :00 nếu browser chỉ gửi HH
        if len(batdau) == 2:
            batdau += ":00"
        if len(ketthuc) == 2:
            ketthuc += ":00"

        # Chuyển sang datetime
        try:
            start_dt = datetime.strptime(f"{ngay} {batdau}", "%Y-%m-%d %H:%M")
            end_dt = datetime.strptime(f"{ngay} {ketthuc}", "%Y-%m-%d %H:%M")
        except ValueError:
            flash("Định dạng giờ không hợp lệ.", "warning")
            return redirect(url_for("doctor_schedule"))

        if start_dt >= end_dt:
            flash("Giờ kết thúc phải lớn hơn giờ bắt đầu.", "warning")
            return redirect(url_for("doctor_schedule"))

        # Kiểm tra giờ nguyên
        if start_dt.minute != 0 or end_dt.minute != 0:
            flash("Giờ bắt đầu và kết thúc phải là giờ nguyên (không có phút).", "warning")
            return redirect(url_for("doctor_schedule"))

        # Lấy lịch hiện tại
        cur.execute("SELECT lichlam FROM lichlamviec WHERE id_bacsi=%s", (id_bacsi,))
        r = cur.fetchone()
        slots = json.loads(r["lichlam"]) if r and r["lichlam"] else []

        # Tạo slot cho từng giờ trong khoảng start_dt -> end_dt
        current = start_dt
        while current < end_dt:
            gio_str = current.strftime("%H:%M")
            # Tránh trùng lặp
            if not any(s["ngay"] == ngay and s["batdau"] == gio_str for s in slots):
                slots.append({"ngay": ngay, "batdau": gio_str})
            current += timedelta(hours=1)

        # Lưu vào DB
        if r:
            cur.execute("UPDATE lichlamviec SET lichlam=%s WHERE id_bacsi=%s", (json.dumps(slots), id_bacsi))
        else:
            cur.execute("INSERT INTO lichlamviec (id_bacsi, lichlam) VALUES (%s, %s)", (id_bacsi, json.dumps(slots)))

        conn.commit()
        flash("Thêm lịch làm việc thành công!", "success")
        return redirect(url_for("doctor_schedule"))

    # GET: lấy danh sách slot hiện tại
    cur.execute("SELECT lichlam FROM lichlamviec WHERE id_bacsi=%s", (id_bacsi,))
    r = cur.fetchone()
    slots = json.loads(r["lichlam"]) if r and r["lichlam"] else []

    cur.close()
    conn.close()
    return render_template("doctor/lichlamviec.html", slots=slots)


# ---------------------- XÓA CA LÀM VIỆC ----------------------
@app.route("/doctor/lichlamviec/delete/<int:index>", methods=["POST"])
def doctor_schedule_delete(index):
    if "user" not in session or session["user"]["role"]!="doctor":
        return redirect(url_for("login"))

    conn = get_conn_or_abort()
    if conn is None:
        return redirect(url_for("doctor_schedule"))

    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id_bacsi FROM bacsi WHERE id_user=%s", (session["user"]["id_nguoidung"],))
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        flash("Bạn chưa có hồ sơ bác sĩ.", "warning")
        return redirect(url_for("doctor_schedule"))

    id_bacsi = row["id_bacsi"]

    cur.execute("SELECT lichlam FROM lichlamviec WHERE id_bacsi=%s", (id_bacsi,))
    r = cur.fetchone()
    slots = json.loads(r["lichlam"]) if r and r["lichlam"] else []
    if 0<=index<len(slots):
        removed = slots.pop(index)
        cur.execute("UPDATE lichlamviec SET lichlam=%s WHERE id_bacsi=%s", (json.dumps(slots), id_bacsi))
        conn.commit()
        flash(f"Xóa ca {removed['ngay']} {removed['batdau']}-{removed.get('ketthuc','')} thành công!", "success")

    cur.close()
    conn.close()
    return redirect(url_for("doctor_schedule"))



if __name__ == "__main__":
    app.run(debug=True)
