from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from flask_mail import Mail, Message
from sqlalchemy import Date
import smtplib
import pytz
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///phonesystem.db'
app.config['SECRET_KEY'] = '2007'
#print(generate_password_hash("Barcelon2025"))

# setup for mail
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME='tbagtime.tshirts@gmail.com',
    MAIL_PASSWORD='ooij cmiy sgjn hdiz',
    MAIL_DEFAULT_SENDER='tbagtime.tshirts@gmail.com'
)

db = SQLAlchemy(app)
mail = Mail(app)


#setup for database
def cet_now():
    return datetime.now(pytz.timezone("Europe/Paris"))
class User(db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(30), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False)

class Device(db.Model):
    device_id = db.Column(db.Integer, primary_key=True)
    Phone = db.Column(db.String(50), nullable=False, unique=False)
    abo_number = db.Column(db.Integer, unique=True)
    abo_type = db.Column(db.String(50))
    location = db.Column(db.String(50))
    status = db.Column(db.String(20), default='Available')
    comment = db.Column(db.String(200))
    battery_life = db.Column(db.String(30))
    DataEU_westEU = db.Column(db.Boolean, default=False)
    World1 = db.Column(db.Boolean, default=False)
    World2 = db.Column(db.Boolean, default=False)

class Request(db.Model):
    request_id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('device.device_id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'))
    abo_need = db.Column(db.String(50))
    startdate = db.Column(db.Date, nullable=False)
    enddate = db.Column(db.Date, nullable=False)
    purpose = db.Column(db.String(200))
    status = db.Column(db.String(20), default='pending')
    timestamp = db.Column(db.DateTime, default=cet_now)
    denial_reason = db.Column(db.String(300))

class Usage(db.Model):
    usage_id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('device.device_id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'))
    action = db.Column(db.String(20))
    timestamp = db.Column(db.DateTime, default=cet_now)


@app.route('/')
def welcome():
    return render_template(".html")
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password): #checking if hashed passwork = True
            session['user_id'] = user.user_id
            session['role'] = user.role.lower()
            flash('Login successful')
            if session['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif session['role'] == 'reception':
                return redirect(url_for('reception_dashboard'))
            else:
                return redirect(url_for('request_device'))
        else:
            flash('Invalid credentials')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))
@app.route('/add_device', methods=['GET', 'POST'])
def add_device():
    if request.method == 'POST':
        phone = request.form['phone']
        abo_number = request.form['abo_number']
        battery_life = int(request.form['battery_life'])
        comment = request.form.get('comment', '')
        abo_type = request.form['abo_type']
        location = request.form['location']
        status = request.form['status']
        data_eu = 'data_eu' in request.form
        world1 = 'world1' in request.form
        world2 = 'world2' in request.form

        
        new_device = Device(
            Phone=phone,
            abo_number=abo_number,
            battery_life=battery_life,
            comment=comment,
            abo_type=abo_type,
            location=location,
            status=status,
            DataEU_westEU=data_eu,
            World1=world1,
            World2=world2
        )
        try:
            db.session.add(new_device)
            db.session.commit()
            flash('Device added successfully!', 'success')
            return redirect(url_for('add_device')) 
        
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'error')

    return render_template('add_device.html')
@app.route('/request_device', methods=['GET', 'POST'])  # request device page
def request_device():
    #checking if user in session has the right access
    if 'user_id' not in session:
        flash('Please log in to make a request.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        abo_need = request.form.get('abo_need')
        purpose = request.form.get('purpose')

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            today = datetime.today().date()
        except Exception:
            flash('Invalid date format.', 'error')
            return redirect(url_for('request_device'))

        # date logic so that they don't select the date before + 2 day min buffer
        if end_date < start_date:
            flash('End date cannot be before start date.', 'error')
            return redirect(url_for('request_device'))

        elif start_date < today + timedelta(days=2):
            flash('Requests must be made at least 2 days in advance.', 'error')
            return redirect(url_for('request_device'))

        new_request = Request(
            user_id=session['user_id'],
            abo_need=abo_need,
            startdate=start_date,
            enddate=end_date,
            purpose=purpose,
            status='pending'
        )

        try:
            return request_notification(new_request)
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while submitting your request.', 'error')
            return redirect(url_for('request_device'))

    return render_template('request_device.html')

@app.route('/admin/auto_approve_request/<int:request_id>')
def auto_approve_request(request_id):
    req = Request.query.get_or_404(request_id)
    if req.status != 'pending':
        flash('Request already processed.')
        return redirect(url_for('admin_dashboard'))

    device = Device.query.filter_by(abo_type=req.abo_need, status='Available').first()
    if not device:
        flash('No available device of that type.', 'warning')
        return redirect(url_for('admin_dashboard'))

    device.status = 'approved'
    req.status = 'approved'
    req.device_id = device.device_id

    usage = Usage(device_id=device.device_id, user_id=req.user_id, action='approved')
    db.session.add_all([device, req, usage])

    print("Before commit:", device.status, req.status, req.device_id)

    try:
        db.session.commit()
        approved_notification(req)
        print("Commit successful.")
    except Exception as e:
        db.session.rollback()
        print("Commit failed:", str(e))
        flash('Error approving request. Please try again.', 'danger')
        return redirect(url_for('admin_dashboard'))

    approved_notification(req)
    flash('Request approved and device checked out.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/approve', methods=['POST'])
def approve_request():
    #checking if user in session has the right access
    if 'user_id' not in session or session.get('role').lower() != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('login'))

    request_id = request.form.get('request_id')
    device_id = request.form.get('device_id')

    print(f"Approve request called with request_id={request_id}, device_id={device_id}")

    if not request_id or not device_id:
        flash('Missing request or device ID.', 'danger')
        return redirect(url_for('all_requests'))

    req = Request.query.get(request_id)
    device = Device.query.get(device_id)

    if not req or not device:
        flash('Request or Device not found.', 'danger')
        return redirect(url_for('all_requests'))

    device.status = 'approved'
    req.status = 'approved'
    req.device_id = device.device_id

    # Creates usage record
    usage = Usage(device_id=device.device_id, user_id=req.user_id, action='approved')

    # Add everything to session
    db.session.add(device)
    db.session.add(req)
    db.session.add(usage)

    try:
        #committing
        db.session.commit()

        #approved email
        approved_notification(req)
        flash('Request approved.', 'success')
    except Exception as e:
        db.session.rollback()
        print("Commit error:", e)
        flash('Error approving request. Please try again.', 'danger')

    return redirect(url_for('all_requests'))


@app.route('/deny/<int:request_id>', methods=['GET', 'POST'])
def deny_request(request_id):
    req = Request.query.get_or_404(request_id)
    user = User.query.get(req.user_id)

    if request.method == 'POST':
        reason = request.form['reason']
        req.status = 'Denied'
        req.denial_reason = reason
        db.session.commit()

        msg = Message(
            subject="Device Request Denied",
            recipients=[user.email], 
            body=f"Your request for a device was denied.\nReason: {reason} \nIf you would like to make another request you can use this link http://127.0.0.1:5001/login"
        )
        mail.send(msg)

        flash('Request denied and reason sent to user.', 'info')
        return redirect(url_for('admin_dashboard'))

    return render_template('reason.html', request_id=request_id)


@app.route('/check_in/<int:device_id>', methods=['POST'])
def check_in(device_id):
    admins = User.query.filter_by(role='Admin').all() #for email
    admin_emails = [admin.email for admin in admins] #for email
    sender1 = "tbagtime.tshirts@gmail.com" #for email
    #checking if user in session has the right access
    if 'user_id' not in session or session.get('role') not in ('reception', 'admin'):
        flash('Unauthorized access', 'danger')
        return redirect(url_for('login'))

    location = request.form.get('location')
    if not location:
        flash('Please select a campus.', 'warning')
        return redirect(request.referrer)

    device = Device.query.get_or_404(device_id)
    device.status = 'Available'
    device.location = location 

    usage = Usage(device_id=device.device_id, user_id=session['user_id'], action='check-in')
    db.session.add(usage)

    try:
        #commit to database
        db.session.commit()
        flash(f'Device checked in at {location}.', 'success')
        
        # Message to admin
        msg = Message(
            subject= f"Device ({device.id}) Checked In",
            sender= sender1,
            recipients=admin_emails,
            body=(
                f"Device {device.Phone} (ABO {device.abo_number}) was checked in at {device.location}).\n"
                f"Time: {usage.timestamp.strftime('%Y-%m-%d %H:%M')}"
            )
        )
        mail.send(msg)

        flash(f"{device.Phone} is checked in", "success")
        return redirect(url_for('check_in_out'))
        
    except Exception as e:
        db.session.rollback()
        flash('Error checking in device.', 'danger')
        print("Check-in error:", e)
        return redirect(url_for('check_in_out'))

@app.route('/check_out/<int:device_id>', methods=['POST'])
def check_out(device_id):
    admins = User.query.filter_by(role='Admin').all()
    admin_emails = [admin.email for admin in admins]
    sender1 = "tbagtime.tshirts@gmail.com"
    #checking if user in session has the right access
    if 'user_id' not in session or session.get('role') not in ('admin', 'reception'):
        return redirect(url_for('login'))

    device = Device.query.get(device_id)
    if device:
        device.status = 'checked_out'
        db.session.add(device)

        usage = Usage(
            device_id=device.device_id,
            user_id=session['user_id'],
            action='checked_out',
            timestamp=cet_now()
        )
    db.session.add(usage)
    try:
        db.session.commit()
    
        # Message to admin
        msg = Message(
            subject="Device Checked Out",
            sender= sender1,
            recipients=admin_emails,
            body=(
                f"Device {device.Phone} (ABO {device.abo_number}) was checked out).\n"
                f"Time: {usage.timestamp.strftime('%Y-%m-%d %H:%M')}"
            )
        )
        mail.send(msg)

        flash(f"{device.Phone} is checked out", "success")
        return redirect(url_for('check_in_out'))

    except Exception as e:
        db.session.rollback()
        print("Check-out error:", e)
        flash("An error occurred during check-out. Please try again.", "danger")
        return redirect(url_for('check_in_out'))
@app.route('/admin/requests')
def all_requests():
    #checking if user in session has the right access
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('login'))

    all_pending = Request.query.filter_by(status='pending').order_by(Request.timestamp.desc()).all()
    all_devices = Device.query.all()
    users = User.query.all()
    available_devices = Device.query.filter_by(status='Available').all()
    usage_history = Usage.query.order_by(Usage.timestamp.desc()).limit(20).all()

    return render_template(
    'all_requests.html',
    pending_requests=all_pending,
    devices=all_devices,
    users=users,
    available_devices=available_devices,
    usage_history=usage_history
)
@app.route('/admin')
def admin_dashboard():
    #checking if user in session has the right access
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('login'))

    users = User.query.all()
    devices = Device.query.all()
    available_devices = Device.query.filter_by(status='Available').all()
    pending_requests = Request.query.filter_by(status='pending').order_by(Request.timestamp.desc()).all()
    usage_history = Usage.query.order_by(Usage.timestamp.desc()).limit(20).all()

    return render_template(
        'admin.html',
        users=users,
        devices=devices,
        available_devices=available_devices,
        pending_requests=pending_requests,
        usage_history=usage_history
    )
@app.route('/back')
def back_to_dashboard():
    if  session.get('role') == 'admin': #if admin then they go back to admin dashboard
        return redirect(url_for('admin_dashboard'))
    elif session.get('role') == 'reception': #if reception then they go back to admin dashboard
        return redirect(url_for('reception_dashboard'))

@app.route('/reception')
def reception_dashboard():
    #checking if user in session has the right access
    if 'user_id' not in session or session.get('role') not in ('reception', 'admin'): 
        flash('Unauthorized access', 'danger')
        return redirect(url_for('login'))
    

    users = User.query.all()
    devices = Device.query.all()
    available_devices = Device.query.filter_by(status='Available').all()
    usage_history = Usage.query.order_by(Usage.timestamp.desc()).limit(20).all()

    return render_template(
        'reception.html',
        users=users,
        devices=devices,
        available_devices=available_devices,
        usage_history=usage_history
    )
@app.route('/admin/all_devices')
def all_devices():
    #checking if user in session has the right access
    if 'user_id' not in session or session.get('role') not in ('reception', 'admin'):
        flash('Unauthorized access', 'danger')
        print('Session role:', session.get('role'))
        return redirect(url_for('login'))
        

    devices = Device.query.all()
    return render_template('all_devices.html', devices=devices)

@app.route('/admin/all_users')
def all_users():
    #checking if user in session has the right access
    if 'user_id' not in session or session.get('role') not in ('reception', 'admin'):
        flash('Unauthorized access', 'danger')
        print('Session role:', session.get('role'))
        return redirect(url_for('login'))

    users = User.query.order_by(User.name).all()
    return render_template('all_users.html', users=users)

@app.route('/admin/check_in_out.html')
def check_in_out():
    #checking if user in session has the right access
    if 'user_id' not in session or session.get('role') not in ('reception', 'admin'):
        flash('Unauthorized access', 'danger')
        print('Session role:', session.get('role'))
        return redirect(url_for('login'))
    
    devices = Device.query.order_by(Device.device_id.desc()).all()
    device_user_pairs = []
    for device in devices:
        # Find latest approval for this device (if any)
        usage = Usage.query.filter_by(device_id=device.device_id, action='approved').order_by(Usage.timestamp.desc()).first()
        user = User.query.get(usage.user_id) if usage else None
        device_user_pairs.append((device, user))

    return render_template('check_in_out.html', devices=device_user_pairs)

#emails
def approved_notification(request_obj):
    try:
        admins = User.query.filter_by(role='Admin').all()
        admin_email = [admin.email for admin in admins]
        user = db.session.get(User, request_obj.user_id)
        sender1 = "tbagtime.tshirts@gmail.com"

        device = db.session.get(Device, request_obj.device_id)
        device_location = device.location
        librarians = User.query.filter_by(role='reception').all()
        librarian_emails = [lib.email for lib in librarians]
        pickup_date = request_obj.startdate - timedelta(days=2)

        # Message to admin
        msg = Message(
            subject="Device approved confirmation",
            sender= sender1,
            recipients= admin_email
        )
        msg.body = (
            f"Device approved for {user.name}.\n"
            f"Device Type/Zone: {request_obj.abo_need}\n"
            f"From: {request_obj.startdate}\n"
            f"To: {request_obj.enddate}\n"
            f"Purpose: {request_obj.purpose}\n"
        )
        mail.send(msg)

        # Message to user
        msg = Message(
            subject="Device request approved",
            sender= sender1,
            recipients=[user.email]
        )
        msg.body = (
            f"Your request has been confirmed.\n"
            f"You will receive a phone from {request_obj.startdate} to {request_obj.enddate} for the purpose of: {request_obj.purpose}.\n"
            f"Device Type/Zone: {request_obj.abo_need}\n"
            f"Please come pick the phone up at {device_location}. on {pickup_date}"
        )
        mail.send(msg)
        
        # Message to Librarian
        msg = Message(
            subject="New device has be approved",
            sender= sender1,
            recipients= librarian_emails
        )
        msg.body = (
            "A new request has been confirmed.\n"
            f"{device_location} will need to prepare this device\n"
            f"{user.name} will come and pick it up between {pickup_date} and {request_obj.startdate}\n"
            
        )
        mail.send(msg)

    except Exception as e:
        print(f"[ERROR] Failed to send approval notifications: {e}")
def request_notification(request_obj):
    if not request_obj:
        flash('Invalid request object.', 'error')
        return redirect(url_for('request_device'))

    try:
        db.session.add(request_obj)
        db.session.commit()

        user_id = session.get('user_id')
        user = db.session.get(User, user_id)

        if not user:
            flash('User not found for notification.', 'error')
            return redirect(url_for('request_device'))

        # Notification to Admin
        admin_msg = Message(
            subject="New Device Request Submitted",
            recipients=['tbagtime.tshirts@gmail.com'],
            body=(
                f"A new device request has been submitted by {user.name}.\n\n"
                f"Device Type/Zone: {request_obj.abo_need}\n"
                f"From: {request_obj.startdate}\n"
                f"To: {request_obj.enddate}\n"
                f"Purpose: {request_obj.purpose}\n\n"
                f"Admin Dashboard: http://127.0.0.1:5001/admin"
            )
        )
        mail.send(admin_msg)

        # Confirmation to user
        user_msg = Message(
            subject="Device Request Submitted",
            recipients=[user.email],
            body=(
                f"Hello {user.name},\n\n"
                f"Your device request has been successfully submitted.\n"
                f"Request Details:\n"
                f"Device Type/Zone: {request_obj.abo_need}\n"
                f"From: {request_obj.startdate}\n"
                f"To: {request_obj.enddate}\n"
                f"Purpose: {request_obj.purpose}\n\n"
                f"You may make another request here: http://127.0.0.1:5001/login"
            )
        )
        mail.send(user_msg)

        flash('Your device request has been submitted successfully.', 'success')
        return redirect(url_for('request_device'))

    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Failed to send request notification: {e}")
        flash('An error occurred while submitting your request.', 'error')
        return redirect(url_for('request_device'))

#running app
if __name__ == '__main__':
    app.run(port=5001, debug=True)

# todo list
    
"""
Create a way to log history of past checked outs
"""