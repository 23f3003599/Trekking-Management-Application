from flask import Flask, render_template, request, redirect, session
from datetime import datetime
from config import Config
from models import db, User, Trek, Booking

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)


#home

@app.route("/")
def home():
    return render_template("base.html")




@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        role = request.form.get("role")

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            return render_template("register.html", error="Email already registered!")

        new_user = User(
            name=name,
            email=email,
            password=password,
            role=role
        )

        db.session.add(new_user)
        db.session.commit()

        return redirect("/login")

    return render_template("register.html")




@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()

        if user is None:
            return "User not found!"

        if user.password != password:
            return render_template("login.html", error="Incorrect password!")
        
        if user.is_blacklisted:
            return render_template("login.html", error="Your account has been blacklisted by Admin.")

        
        if user.role == "Staff" and not user.is_approved:
            return render_template("login.html", error="Waiting for Admin Approval!")

        
        session["user_id"] = user.id
        session["user_name"] = user.name
        session["role"] = user.role

        if user.role == "Admin":
            return redirect("/admin")

        elif user.role == "Staff":
            return redirect("/staff")

        else:
            return redirect("/user")

    return render_template("login.html")




@app.route("/admin")
def admin_dashboard():

    if session.get("role") != "Admin":
        return redirect("/login")

    total_treks = Trek.query.count()
    total_users = User.query.filter_by(role="User").count()
    total_staff = User.query.filter_by(role="Staff").count()
    total_bookings = Booking.query.count()
    recent_bookings = Booking.query.order_by(
        Booking.id.desc()
    ).limit(5).all()

    return render_template(
        "admin_dashboard.html",
        total_treks=total_treks,
        total_users=total_users,
        total_staff=total_staff,
        total_bookings=total_bookings,
        recent_bookings=recent_bookings
    )



@app.route("/staff")
def staff_dashboard():

    if session.get("role") != "Staff":
        return redirect("/login")

    assigned_treks = Trek.query.filter_by(
        staff_id=session["user_id"]
    ).all()

    total_assigned = len(assigned_treks)

    open_treks = Trek.query.filter_by(
        staff_id=session["user_id"],
        status="Open"
    ).count()

    total_participants = Booking.query.join(Trek).filter(
        Trek.staff_id == session["user_id"],
        Booking.status == "Booked"
    ).count()

    return render_template(
        "staff_dashboard.html",
        assigned_treks=assigned_treks,
        total_assigned=total_assigned,
        total_participants=total_participants,
        open_treks=open_treks
    ) 

@app.route("/assigned_treks")
def assigned_treks():

    if session.get("role") != "Staff":
        return redirect("/login")

    treks = Trek.query.filter_by(
        staff_id=session["user_id"]
    ).all()

    return render_template(
        "assigned_treks.html",
        treks=treks
    )



@app.route("/update_trek/<int:trek_id>", methods=["GET", "POST"])
def update_trek(trek_id):

    if session.get("role") != "Staff":
        return redirect("/login")

    trek = Trek.query.get_or_404(trek_id)

    
    if trek.status == "Completed":
        return redirect("/assigned_treks")

    if request.method == "POST":

        trek.slots = int(request.form.get("slots"))
        trek.status = request.form.get("status")

        db.session.commit()

        return redirect("/assigned_treks")

    return render_template(
        "update_trek.html",
        trek=trek
    )



@app.route("/view_participants/<int:trek_id>")
def view_participants(trek_id):

    if session.get("role") != "Staff":
        return redirect("/login")

    trek = Trek.query.get_or_404(trek_id)

    bookings = Booking.query.filter_by(
        trek_id=trek.id,
        status="Booked"
    ).all()

    return render_template(
        "view_participants.html",
        trek=trek,
        bookings=bookings
    )




@app.route("/user")
def user_dashboard():

    if session.get("role") != "User":
        return redirect("/login")

    
    treks = Trek.query.filter_by(status="Open").all()

    
    bookings = Booking.query.filter_by(
        user_id=session["user_id"]
    ).all()

    return render_template(
        "user_dashboard.html",
        treks=treks,
        bookings=bookings
    )



@app.route("/add_trek", methods=["GET", "POST"])
def add_trek():

    
    staff_members = User.query.filter_by(
        role="Staff",
        is_approved=True
    ).all()

    if request.method == "POST":

        name = request.form.get("name")
        location = request.form.get("location")
        difficulty = request.form.get("difficulty")
        duration = int(request.form.get("duration"))
        slots = int(request.form.get("slots"))

        start_date = datetime.strptime(
            request.form.get("start_date"),
            "%Y-%m-%d"
        ).date()

        end_date = datetime.strptime(
            request.form.get("end_date"),
            "%Y-%m-%d"
        ).date()

        staff_id = int(request.form.get("staff_id"))

        new_trek = Trek(
            name=name,
            location=location,
            difficulty=difficulty,
            duration=duration,
            slots=slots,
            start_date=start_date,
            end_date=end_date,
            status="Open",
            staff_id=staff_id
        )

        db.session.add(new_trek)
        db.session.commit()

        return redirect("/view_treks")

    return render_template(
        "add_trek.html",
        staff_members=staff_members
    )



@app.route("/view_treks")
def view_treks():

    if session.get("role") == "User":

        treks = Trek.query.filter_by(status="Open")

        search = request.args.get("search")
        difficulty = request.args.get("difficulty")
        location = request.args.get("location")

        if search:
            treks = treks.filter(Trek.name.contains(search))

        if difficulty:
            treks = treks.filter(Trek.difficulty == difficulty)

        if location:
            treks = treks.filter(Trek.location.contains(location))

        treks = treks.all()

    else:

        treks = Trek.query.all()

    return render_template(
        "view_treks.html",
        treks=treks
    )


@app.route("/book_trek/<int:trek_id>")
def book_trek(trek_id):

    
    if session.get("role") != "User":
        return redirect("/login")

    trek = Trek.query.get_or_404(trek_id)

    
    if trek.status != "Open":

        treks = Trek.query.filter_by(status="Open").all()

        return render_template(
            "view_treks.html",
            treks=treks,
            error="This trek is not open."
        )

    
    if trek.slots <= 0:

        treks = Trek.query.filter_by(status="Open").all()

        return render_template(
            "view_treks.html",
            treks=treks,
            error="No slots available."
        )

    
    existing_booking = Booking.query.filter_by(
        user_id=session["user_id"],
        trek_id=trek.id,
        status="Booked"
    ).first()

    if existing_booking:

        treks = Trek.query.filter_by(status="Open").all()

        return render_template(
            "view_treks.html",
            treks=treks,
            error="You have already booked this trek."
        )

    
    booking = Booking(
        user_id=session["user_id"],
        trek_id=trek.id,
        booking_date=datetime.today().date(),
        status="Booked"
    )

    
    trek.slots -= 1

    db.session.add(booking)
    db.session.commit()

    return redirect("/my_bookings")

@app.route("/my_bookings")
def my_bookings():

    bookings = Booking.query.filter_by(
        user_id=session["user_id"]
    ).all()

    return render_template(
        "my_bookings.html",
        bookings=bookings
    )


@app.route("/cancel_booking/<int:booking_id>")
def cancel_booking(booking_id):

    booking = Booking.query.get_or_404(booking_id)

    
    trek = Trek.query.get(booking.trek_id)
    trek.slots += 1

    
    booking.status = "Cancelled"

    db.session.commit()

    return redirect("/my_bookings")



@app.route("/delete_trek/<int:trek_id>")
def delete_trek(trek_id):

    trek = Trek.query.get_or_404(trek_id)

    db.session.delete(trek)
    db.session.commit()

    return redirect("/view_treks")


@app.route("/edit_trek/<int:trek_id>", methods=["GET", "POST"])
def edit_trek(trek_id):

    if session.get("role") != "Admin":
        return redirect("/login")

    trek = Trek.query.get_or_404(trek_id)

    staff_members = User.query.filter_by(
        role="Staff",
        is_approved=True
    ).all()

    if request.method == "POST":

        trek.name = request.form.get("name")
        trek.location = request.form.get("location")
        trek.difficulty = request.form.get("difficulty")
        trek.duration = int(request.form.get("duration"))
        trek.slots = int(request.form.get("slots"))

        trek.start_date = datetime.strptime(
            request.form.get("start_date"),
            "%Y-%m-%d"
        ).date()

        trek.end_date = datetime.strptime(
            request.form.get("end_date"),
            "%Y-%m-%d"
        ).date()

        trek.staff_id = int(request.form.get("staff_id"))

        
        trek.status = request.form.get("status")

        db.session.commit()

        return redirect("/view_treks")

    return render_template(
        "edit_trek.html",
        trek=trek,
        staff_members=staff_members
    )



@app.route("/view_staff")
def view_staff():

    staff_members = User.query.filter_by(
        role="Staff"
    ).all()

    return render_template(
        "view_staff.html",
        staff_members=staff_members
    )


@app.route("/view_users")
def view_users():

    users = User.query.filter_by(role="User").all()

    return render_template(
        "view_users.html",
        users=users
    )

@app.route("/view_bookings")
def view_bookings():

    if session.get("role") != "Admin":
        return redirect("/login")

    bookings = Booking.query.all()

    return render_template(
        "view_bookings.html",
        bookings=bookings
    )

@app.route("/blacklist_user/<int:user_id>")
def blacklist_user(user_id):

    user = User.query.get_or_404(user_id)

    user.is_blacklisted = True

    db.session.commit()

    return redirect("/view_users")

@app.route("/unblacklist_user/<int:user_id>")
def unblacklist_user(user_id):

    if session.get("role") != "Admin":
        return redirect("/login")

    user = User.query.get_or_404(user_id)

    user.is_blacklisted = False

    db.session.commit()

    return redirect("/view_users")


@app.route("/approve_staff/<int:staff_id>")
def approve_staff(staff_id):

    staff = User.query.get_or_404(staff_id)

    staff.is_approved = True

    db.session.commit()

    return redirect("/view_staff")



@app.route("/blacklist_staff/<int:staff_id>")
def blacklist_staff(staff_id):

    staff = User.query.get_or_404(staff_id)

    staff.is_blacklisted = True

    db.session.commit()

    return redirect("/view_staff")


@app.route("/unblacklist_staff/<int:staff_id>")
def unblacklist_staff(staff_id):

    if session.get("role") != "Admin":
        return redirect("/login")

    staff = User.query.get_or_404(staff_id)

    staff.is_blacklisted = False

    db.session.commit()

    return redirect("/view_staff")



@app.route("/search", methods=["GET", "POST"])
def search():

    users = []
    staff_members = []
    treks = []

    if request.method == "POST":

        keyword = request.form.get("search")

        users = User.query.filter(
            User.role == "User",
            User.name.contains(keyword)
        ).all()

        staff_members = User.query.filter(
            User.role == "Staff",
            User.name.contains(keyword)
        ).all()

        treks = Trek.query.filter(
            Trek.name.contains(keyword)
        ).all()

    return render_template(
        "search.html",
        users=users,
        staff_members=staff_members,
        treks=treks
    )

@app.route("/profile", methods=["GET", "POST"])
def profile():

    if "user_id" not in session:
        return redirect("/login")

    user = User.query.get_or_404(session["user_id"])

    if request.method == "POST":

        user.name = request.form.get("name")
        user.email = request.form.get("email")

        password = request.form.get("password")

        if password != "":
            user.password = password

        db.session.commit()

        session["user_name"] = user.name

        return redirect("/profile")

    return render_template(
        "profile.html",
        user=user
    )

@app.route("/reports")
def reports():

    if session.get("role") != "Admin":
        return redirect("/login")

    total_treks = Trek.query.count()

    open_treks = Trek.query.filter_by(status="Open").count()

    closed_treks = Trek.query.filter_by(status="Closed").count()

    completed_treks = Trek.query.filter_by(status="Completed").count()

    total_users = User.query.filter_by(role="User").count()

    total_staff = User.query.filter_by(role="Staff").count()

    total_bookings = Booking.query.count()

    cancelled_bookings = Booking.query.filter_by(
        status="Cancelled"
    ).count()

    treks = Trek.query.all()

    bookings = Booking.query.order_by(
        Booking.booking_date.desc()
    ).all()

    return render_template(
        "reports.html",

        total_treks=total_treks,

        open_treks=open_treks,

        closed_treks=closed_treks,

        completed_treks=completed_treks,

        total_users=total_users,

        total_staff=total_staff,

        total_bookings=total_bookings,

        cancelled_bookings=cancelled_bookings,

        treks=treks,

        bookings=bookings
    ) 


@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)