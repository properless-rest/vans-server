# system
import os
import shutil
from datetime import datetime, timedelta
from uuid import uuid4, UUID

# 3rd party flask
from flask import current_app, flash, jsonify, redirect, render_template, request, session
from flask_mailman import EmailMessage
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt_identity, jwt_required

# 3rd party misc
from PIL import Image
from pytz import utc

# project
from config import app, bcrypt, db, executor, serializer, ProdConfig, SERVER_TIMEZONE
from models import User, Van, Transaction, Review


@app.route("/")
def home():
    return render_template("index/index.html")


@app.before_request
def protect_admin():
    # If the user is not logged in and trying to access '/admin', redirect to login
    if request.path.startswith('/admin') and not session.get('is_authorized'):
        return redirect('/authorize')


@app.route('/authorize', methods=['GET', 'POST'])
def authorize():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == app.config['ADMIN_USERNAME'] and password == app.config['ADMIN_PASSWORD']:
            session['is_authorized'] = True  # Store the login state in the session
            return redirect(('/admin'))  # Redirect to Flask-Admin
        flash('Invalid credentials')
    return render_template('auth/authorize.html')  # this is for other methods (incl. 'GET')


@app.route('/unauthorize')
def unauthorize():
    session.pop('is_authorized', None)  # Remove the 'is_logged_in' flag from the session
    return redirect(('/authorize'))


# FLASK AUTOMATICALLY SERVES STATIC FILES, no custom view is needed
# this one is for loading of the static files
# @app.route('/<path:static>')
# def send_static(static):
#     return current_app.send_static_file(f"{static}")


@app.after_request
def add_header(response):
    if request.path.startswith('/static'):
        response.headers['Cache-Control'] = 'public, max-age=604800'  # store static on FrontEnd for 1 week
    return response


# for pw reseting
def __generate_reset_token(email):
    return serializer.dumps(email, salt=app.config['SALT'])


# for pw reseting
def __verify_reset_token(token, expiration=app.config['RESET_PW_TOKEN_EXP']):  # Expires in 15 min.
    try:
        email = serializer.loads(token, salt=app.config['SALT'], max_age=expiration)
        return email
    except Exception as e:
        return None
    

def __validate_email(email):
    # WARNING: do NOT jsonify the dicts;
    # it is done in the view functions

    # no @ in email or no dot (.) after @
    if '@' not in email or \
      "." not in email.split('@')[-1]:
        return {
                "message": "Invalid email",
                "statusText": "Invalid email format",
                "emailErr": True  # highlights the input in red (Frontend)
               }
    registred_emails = list(map(lambda user: user.email, User.query.all()))
    # email already exists
    if email in registred_emails:
        return {
                "message": "This email is taken",
                "statusText": "Email is not unique",
                "emailErr": True  # highlights the input in red (Frontend)
               }
    return None


def __send_email_on_signup(email, name, surname):
    message = EmailMessage(
        subject="VanLife: Successful Registration",
        body=render_template("mail/registration.html", name=name, surname=surname),
        from_email="vanlife@support.com",
        to=[email]
        )
    message.content_subtype = "html"  # this must be set to send html, not plain text
    try:
        message.send()
    except Exception as e:
        return None


def __send_reset_email(email):
    token = __generate_reset_token(email)
    reset_url = f"{app.config['FRONTEND_URL']}/reset-password/{token}"
    message = EmailMessage(
        subject="VanLife: Password Reset Requested",
        body=render_template("mail/change_email.html", reset_url=reset_url),
        from_email="vanlife@support.com",
        to=[email],
    )
    message.content_subtype = "html"
    message.send()


# in each of the methods below using `data = request.get_json()`
# the arguement for data.get must correspond to the <input/ name="...">
# from the FrontEnd side


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    # no exception handling here; str is rarely non-convertable
    # str(None) yields a truthy "None", which is why ternary `if-statements` are used below
    # (in case of empty field or no field in the json)
    name = str(data.get('name')).strip().capitalize() if data.get("name") else None
    surname = str(data.get('surname')).strip().capitalize() if data.get("surname") else None
    email = str(data.get('email')).strip().lower() if data.get("email") else None
    # no second password inside the request; validate on the Front-End side
    password = str(data.get('password')) if data.get("password") else None
    if not (name and surname and email and password):
        return jsonify(message="Required data missing", statusText="Required data missing"), 400
    email_invalid = __validate_email(email)
    # if the validation has failed, it returns a dict; jsonify and send it
    if email_invalid:
        return jsonify(email_invalid), 400
    if len(password) < 8:
        return jsonify(message="Password must be at least 8\u00A0characters", statusText="Improper password", pwErr=True), 401
    try:
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    except Exception as e:
        return jsonify(message="Unhashable password", statusText="Inadmissible password", pwErr=True), 500
    # don't hex the uuid [uuid4().hex]: it breaks the ORM database column's type settings
    new_user = User(uuid=uuid4(), name=name, surname=surname, email=email, password=hashed_password)
    try:
        db.session.add(new_user)
        db.session.commit()
        executor.submit(__send_email_on_signup, email, name, surname)  # EXECUTOR WORKS IN A SEPARATE THREAD
        return jsonify(message="User registered", statusText="Creation successful"), 201
    except Exception as e:
        return jsonify(message="Server Error", statusText="Creation failed"), 500


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    # no exception handling here; str is rarely non-convertable
    # str(None) yields a truthy "None", which is why ternary `if-statements` are used below
    email = str(data.get('email')).lower() if data.get("email") else None
    password = str(data.get('password')) if data.get("password") else None
    if not (email and password):
        return jsonify(message="Required data missing", statusText="Required data missing"), 400
    user = User.query.filter_by(email=email).first()
    if user and bcrypt.check_password_hash(user.password, password):
        JWToken = create_access_token(identity={'email': user.email})
        RFToken = create_refresh_token(identity={'email': user.email})
        return jsonify(JWToken=JWToken, RFToken=RFToken, statusText="Login successful"), 200
    else:
        return jsonify(message="Wrong email or password", statusText="Login failed"), 401


@app.route("/sendReset", methods=["POST"])
def send_reset_email():
    data = request.get_json()
    # no exception handling here; str is rarely non-convertable
    # str(None) yields a truthy "None", which is why ternary `if-statements` are used below
    email = str(data.get('email')).lower() if data.get("email") else None
    if not (email):
        return jsonify(message="Required data missing", statusText="Required data missing"), 400
    registred_emails = list(map(lambda user: user.email, User.query.all()))
    if email not in registred_emails:
        return jsonify(message="Email is not registred", statusText="Wrong email"), 400
    __send_reset_email(email=email)
    return jsonify(message="Email sent", statusText="Email sent"), 200


@app.route('/validateToken', methods=['POST'])
def validate_pw_reset_token():
    data = request.get_json()
    token = data.get('token', None)
    email = __verify_reset_token(token)
    if not email:
        return jsonify(tokenValid=False), 200
    # The token is valid, allow password reset
    return jsonify(tokenValid=True), 200


@app.route('/resetPassword', methods=['POST'])
def reset_password():
    data = request.get_json()
    token = data.get('token', None)
    email = __verify_reset_token(token)
    if not email:
        return jsonify(message="Cannot update password", statusText="Failed to update"), 400
    relevant_user = User.query.filter_by(email=email).first()
    if not relevant_user:
        return jsonify(message="User does not exist", statusText="Failed to update"), 400
    data = request.get_json()
    # no exception handling here; str is rarely non-convertable
    # str(None) yields a truthy "None", which is why ternary `if-statements` are used below
    new_password = str(data.get('newPassword')) if data.get('newPassword') else None
    if not new_password:
        return jsonify(message="Enter your new password", statusText="Required data missing"), 401
    if len(new_password) < 8:
        return jsonify(message="Password must be at least 8\u00A0characters", statusText="Improper password"), 401
    new_hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
    relevant_user.password = new_hashed_password
    try:
        db.session.commit()
        return jsonify(message="User password updated", statusText="Successful update"), 200
    except Exception:
        return jsonify(message="Server Error", statusText="Failed to update"), 500


# for JWT REFRESHING
@app.route("/refreshToken", methods=["POST"])
@jwt_required(refresh=True)  # `refresh=True` allows only refresh tokens to access this route.
def refresh():
    identity = get_jwt_identity()  # NO `EMAIL` key HERE!
    JWToken = create_access_token(identity=identity)
    return jsonify(JWToken=JWToken)


@jwt_required()
def __get_current_user():
    try:
        logged_username = get_jwt_identity()['email']
    except Exception as e:
        return None  # don't query the user if an exception arises; check for truthness inside view functions;
    current_user = User.query.filter_by(email=logged_username).first()
    return current_user


@app.route('/getUser', methods=['GET'])
def get_user():
    # no data in the request body;
    # authentication done with a JWT
    # send in the header of the reuest:: Authentication: `Bearer <JWT>`
    current_user = __get_current_user()
    if not current_user:
        return jsonify(message="Not Authorized", statusText="Failed to read"), 401
    current_user_json = current_user.to_JSON()
    return jsonify(logged_user=current_user_json, statusText="Read succesful"), 200


@app.route('/uploadAvatar', methods=['POST'])
def upload_avatar():
    current_user = __get_current_user()
    if not current_user:
        return jsonify(message="Not Authorized", statusText="Failed to read"), 401
    file = request.files['avatar']
    file_extension = file.filename.rsplit(".")[-1]
    # imgMsg is for FrontEnd Profile Page form hints' differentiation
    if not file:
        return jsonify(message="No file detected", statusText="Invalid file", imgMsg=True), 400
    if file.filename == "":
        return jsonify(message="Inadmissible file name", statusText="Invalid file name", imgMsg=True), 400
    if not file_extension in {"jpg", "jpeg", "png"}:
        return jsonify(message="Extension: .png, .jp(e)g", statusText="Invalid file", imgMsg=True), 400
    
    # Configure the path to the avatar file and make dir if necessary
    secure_filename = f"{uuid4().hex}.{file_extension}"
    user_folder = os.path.join(app.config['STATIC_FOLDER'], "user")
    personal_folder = os.path.join(user_folder, str(current_user.uuid))

    if not os.path.exists(personal_folder):
        os.makedirs(personal_folder)

    # Save the new profile picture inside the user folder
    temp_avatar_path = os.path.join(personal_folder, 'temp_' + secure_filename)
    final_avatar_path = os.path.join(personal_folder, secure_filename)

    try:
        # Save the new file temporarily
        file.save(temp_avatar_path)
        current_avatar = current_user.avatar
        if os.path.exists(current_avatar) and current_avatar != app.config["DEFAULT_USER_IMG"]:
            os.remove(current_avatar)

        # Rename/move the new file to the final destination
        os.rename(temp_avatar_path, final_avatar_path)
        current_user.avatar = final_avatar_path  # update the path to the avatar
        db.session.commit()
        return jsonify(
            message="Profile picture updated", 
            statusText="Update successful", 
            imgMsg=True
        ), 200
    except Exception as e:
        # In case of an error, remove the temporary file if it exists
        if os.path.exists(temp_avatar_path):
            os.remove(temp_avatar_path)
        return jsonify(message="Server Error", statusText="Failed to update", imgMsg=True), 500


@app.route('/updateUser', methods=['PATCH'])
def update_user():
    current_user = __get_current_user()
    if not current_user:
        return jsonify(message="Not Authorized", statusText="Failed to read"), 401
    data = request.get_json()
    # no exception handling here; str is rarely non-convertable
    # str(None) yields a truthy "None", which is why ternary `if-statements` are used below
    name = str(data.get('name')).strip().capitalize() if data.get('name') else None
    surname = str(data.get('surname')).strip().capitalize() if data.get('surname') else None
    if not (name and surname):
        return jsonify(message="Required data missing", statusText="Required data missing"), 400
    if current_user.name == name and current_user.surname == surname:
        return jsonify(message="No modifications detected", statusText="Data not altered", userMsg=True), 400
    current_user.name = name
    current_user.surname = surname
    try:
        db.session.commit()
        return jsonify(message="User data updated", statusText="Update successful", userMsg=True), 200
    except Exception:
        return jsonify(message="Server Error", statusText="Failed to update", userMsg=True), 500


@app.route('/updatePassword', methods=['PATCH'])
def update_password():
    current_user = __get_current_user()
    if not current_user:
        return jsonify(message="Not Authorized", statusText="Failed to read"), 401
    data = request.get_json()
    # no exception handling here; str is rarely non-convertable
    # str(None) yields a truthy "None", which is why ternary `if-statements` are used below
    current_password = str(data.get('currentPassword')) if data.get('currentPassword') else None
    if not bcrypt.check_password_hash(current_user.password, current_password):
        return jsonify(message="Curent password does not match", statusText="Password mismatch", passMsg=True), 401
    new_password = str(data.get('newPassword')) if data.get('newPassword') else None
    if not new_password:
        return jsonify(message="Enter the new password", statusText="Failed to read", passMsg=True), 401
    if len(new_password) < 8:
        return jsonify(message="Password must be at least 8\u00A0characters", statusText="Improper password", passMsg=True), 401
    new_hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
    current_user.password = new_hashed_password
    try:
        db.session.commit()
        return jsonify(message="User password updated", statusText="Successful update", passMsg=True), 200
    except Exception:
        return jsonify(message="Server Error", statusText="Failed to update", passMsg=True), 500


@app.route("/vans", methods=["GET"])
def get_vans():
    vans = Van.query.all()
    vans_json_list = list(map(lambda van: van.to_JSON(), vans))
    return jsonify(vans=vans_json_list, statusText="Read successful"), 200


@app.route("/vans/<uuid:van_uuid>", methods=["GET"])
def get_van(van_uuid):
    van = Van.query.filter_by(uuid=van_uuid).first()
    if not van:
        return jsonify(message="Van does not exist", statusText="Failed to read"), 200
    van_json = van.to_JSON()
    return jsonify(van=van_json, statusText="Read successful"), 200


@app.route("/addVan", methods=["POST"])
def add_van():
    current_user = __get_current_user()  # JWT protection is here
    if not current_user:
        return jsonify(message="Not Authorized", statusText="Failed to read"), 401
    data = request.get_json()
    # no exception handling here; str is rarely non-convertable
    # str(None) yields a truthy "None", which is why ternary `if-statements` are used below
    name = str(data.get('name')).strip() if data.get('name') else None
    description = str(data.get('description')).strip() if data.get('description') else None
    type = str(data.get('type')) if data.get('type') else None
    price_per_day = data.get('pricePerDay')
    if not (name and description and type and price_per_day):
        return jsonify(message="Required data missing", statusText="Required data missing"), 400
    if type not in ["Simple", "Rugged", "Luxury"]:
        return jsonify(message="Invalid Van type", statusText="Invalid input", dataMsg=True), 400
    try:
        price_per_day = int(price_per_day)
    except (ValueError, TypeError):
        return jsonify(message="Inadmissible price", statusText="Wrong input", dataMsg=True), 400
    if price_per_day < 1:
        return jsonify(message="Price must be positive", statusText="Wrong input", dataMsg=True), 400
    if price_per_day > 2_000_000:
        # SQL INTEGER HAS A RENGE: -2,147,483,648 to 2,147,483,647; floor to 2 millions;
        return jsonify(message="Price too large", statusText="Invalid price"), 400
    van = Van(
        uuid=uuid4(), 
        name=name, 
        description=description, 
        type=type, 
        price_per_day=price_per_day,
        host_id=current_user.id
    )
    try:
        db.session.add(van)
        db.session.commit()
        # NOTE: 'success' field is needed for redirecting inside AddVanPage's loader
        return jsonify(message="Van created", statusText="Create successful", dataMsg=True, success=True), 201
    except Exception:
        return jsonify(message="Server Error", statusText="Failed to create", dataMsg=True), 500


@app.route('/uploadVanImage', methods=['POST'])
def upload_van_image():
    current_user = __get_current_user()  # jwt-protection is here
    if not current_user:
        return jsonify(message="Not Authorized", statusText="Failed to read"), 401
    vanUUID = request.form.get("vanUUID", None)  # vanUUID is a string
    try:
        van = Van.query.filter_by(uuid=UUID(vanUUID)).first()  # UUID(vanUUID) is a UUID
    except Exception:
        return jsonify(message="Invalid UUID", statusText="Invalid UUID format"), 400
    if not isinstance(vanUUID, str):
        return jsonify(message="Invalid UUID", statusText="Invalid UUID"), 400
    van = Van.query.filter_by(uuid=UUID(vanUUID)).first()  # UUID(vanUUID) is a UUID
    if not van:
        return jsonify(message="The Van does not exist", statusText="Failed to read", imgMsg=True), 400
    file = request.files.get('image')
    file_extension = file.filename.rsplit(".")[-1]
    if not file:
        return jsonify(message="No file detected", statusText="Invalid file", imgMsg=True), 400
    if file.filename == "":
        return jsonify(message="Inadmissible file name", statusText="Invalid file name", imgMsg=True), 400
    if not file_extension in {"jpg", "jpeg", "png"}:
        return jsonify(message="Extension: .png, .jp(e)g", statusText="Invalid file", imgMsg=True), 400
    
    # Configure the path to the avatar file and make dir if necessary
    #
    # NOTE: dynamic names is also the only way to make React images Update without F5
    secure_filename = f"{uuid4().hex}.{file_extension}"
    vans_folder = os.path.join(app.config['STATIC_FOLDER'], "vans")
    personal_folder = os.path.join(vans_folder, str(van.uuid))

    if not os.path.exists(personal_folder):
        os.makedirs(personal_folder)

    # preliminary and final names of the file (to delete an old image first, but only on success)
    temp_image_path = os.path.join(personal_folder, 'temp_' + secure_filename)
    final_image_path = os.path.join(personal_folder, secure_filename)
    current_image = van.image
    try:
        # Save the new file temporarily
        file.save(temp_image_path)
        # don't delete the default image from the folder
        if os.path.exists(current_image) and current_image != app.config["DEFAULT_VANS_IMG"]:
            os.remove(current_image)

        # Rename/move the new file to the final destination
        os.rename(temp_image_path, final_image_path)
        van.image = final_image_path  # update the path to the van image
        db.session.commit()
        return jsonify(message="Image updated", statusText="Update successful", imgMsg=True), 200
    except Exception as e:
        # In case of an error, remove the temporary file if it exists
        if os.path.exists(temp_image_path):
            os.remove(temp_image_path)
            van.image = current_image
            db.session.commit()
        return jsonify(message="Server Error", statusText="Failed to update", imgMsg=True), 500


@app.route('/updateVan', methods=['PATCH'])
def update_van():
    current_user = __get_current_user()  # JWT protection is here
    if not current_user:
        return jsonify(message="Not Authorized", statusText="Failed to read"), 401
    data = request.get_json()
    vanUUID = data.get("vanUUID", None)  # vanUUID is a string
    try:
        van = Van.query.filter_by(uuid=UUID(vanUUID)).first()  # UUID(vanUUID) is a UUID
    except Exception:
        return jsonify(message="Invalid UUID", statusText="Invalid UUID format"), 400
    if not van:
        return jsonify(message="The Van does not exist", statusText="Failed to read", dataMsg=True), 400
    # no exception handling here; str is rarely non-convertable
    # str(None) yields a truthy "None", which is why ternary `if-statements` are used below
    # NOTE: don't capitalize(): van and description may have several capital words in them;
    name = str(data.get('name')).strip() if data.get('name') else None
    description = data.get('description').strip() if data.get('description') else None
    price_per_day = data.get('pricePerDay', None)
    type = data.get('type', None)
    if not (name and description and type and price_per_day):
        return jsonify(message="Required data missing", statusText="Data is missing", dataMsg=True), 400
    if type not in ["Simple", "Rugged", "Luxury"]:
        return jsonify(message="Invalid Van type", statusText="Wrong input", dataMsg=True), 400
    try:
        price_per_day = int(price_per_day)
    except (ValueError, TypeError):
        return jsonify(message="Inadmissible price", statusText="Wrong input", dataMsg=True), 400
    if price_per_day < 1:
        return jsonify(message="Price must be positive", statusText="Wrong input", dataMsg=True), 400
    if price_per_day > 2_000_000:
        # SQL INTEGER HAS A RENGE: -2,147,483,648 to 2,147,483,647; floor to 2 millions;
        return jsonify(message="Price too large", statusText="Invalid price"), 400
    if van.name == name \
        and van.description == description \
        and van.type == type \
        and van.price_per_day == price_per_day:
        return jsonify(message="No modifications detected", statusText="Data not altered", dataMsg=True), 400
    # if the name of the van changes, make sure the reviews will correspond to the new name of the van;
    if van.name != name:
        for review in van.reviews:
            review.van_name = name
    van.name = name
    van.description = description
    van.price_per_day = price_per_day
    van.type = type
    try:
        db.session.commit()
        return jsonify(message="Van data updated", statusText="Update successful", dataMsg=True), 200
    except Exception:
        return jsonify(message="Server Error", statusText="Failed to update", dataMsg=True), 500


@app.route('/deleteVan', methods=['POST'])
def delete_van():
    current_user = __get_current_user()  # JWT protection is here
    if not current_user:
        return jsonify(message="Not Authorized", statusText="Failed to read"), 401
    data = request.get_json()
    vanUUID = data.get("vanUUID", None)  # vanUUID is a string
    try:
        van = Van.query.filter_by(uuid=UUID(vanUUID)).first()  # UUID(vanUUID) is a UUID
    except Exception:
        return jsonify(message="Invalid UUID", statusText="Invalid UUID format"), 400
    if not van:
        return jsonify(message="The Van does not exist", statusText="Failed to read"), 400
    van_static_folder = os.path.join(app.config['STATIC_FOLDER'], "vans", vanUUID)
    try:
        if os.path.exists(van_static_folder):
            shutil.rmtree(van_static_folder)  # delete everything inside the folder & the folder
        db.session.delete(van)
        db.session.commit()
        # NOTE: 'success' field is needed for redirecting inside VanDeletePage's loader
        return jsonify(message="Van deleted", statusText="Delete successful", success=True), 200
    except Exception:
        return jsonify(message="Server Error", statusText="Failed to delete"), 500


@app.route('/makeTransaction', methods=['POST'])
def make_transaction():
    # no authorization required
    data = request.get_json()
    vanUUID = data.get("vanUUID", None)  # vanUUID is a string
    try:
        van = Van.query.filter_by(uuid=UUID(vanUUID)).first()  # UUID(vanUUID) is a UUID
    except Exception:
        return jsonify(message="Invalid UUID", statusText="Invalid UUID format"), 400
    if not van:
        return jsonify(message="The Van does not exist", statusText="Failed to read"), 400
    #
    # no exception handling here; str is rarely non-convertable
    # str(None) yields a truthy "None", which is why ternary `if-statements` are used below
    lessee_name = str(data.get("lesseeName")).strip().capitalize() if data.get("lesseeName") else None
    lessee_surname = str(data.get("lesseeSurname")).strip().capitalize() if data.get("lesseeSurname") else None
    lessee_email = str(data.get("lesseeEmail")).strip().lower() if data.get("lesseeEmail") else None
    rent_commencement = data.get("rentCommencement", None)
    rent_expiration = data.get("rentExpiration", None)
    if not (lessee_name and lessee_surname and lessee_email and rent_commencement and rent_expiration):
        return jsonify(message="Required data missing", statusText="Missing Data"), 400
    if '@' not in lessee_email or \
      "." not in lessee_email.split('@')[-1]:
        return jsonify(message="Invalid email"), 400
    #
    try:
        # conversion to objects of type datetime.date
        # this will prevent both inadmissible data types and wrong date formats (like 33/13/2024)
        naive_rent_commencement = datetime.strptime(rent_commencement, '%Y-%m-%d')
        naive_rent_expiration = datetime.strptime(rent_expiration, '%Y-%m-%d')
        UTC_rent_commencement = utc.localize(naive_rent_commencement)
        UTC_rent_expiration = utc.localize(naive_rent_expiration)
        # convert the date to the Server's locale
        rent_commencement = UTC_rent_commencement.astimezone(SERVER_TIMEZONE).date()
        rent_expiration = UTC_rent_expiration.astimezone(SERVER_TIMEZONE).date()
    except Exception:
        return jsonify(message="Invalid date format", statusText="Inadmissible date"), 400
    tomorrow = datetime.now(SERVER_TIMEZONE).date() + timedelta(days=1)
    print(rent_commencement, tomorrow)
    if rent_commencement < tomorrow:
        return jsonify(message="Inadmissible commencement date", statusText="Inadmissible date"), 400
    if rent_commencement >= rent_expiration:
        return jsonify(message="Inadmissible date order", statusText="Inadmissible date"), 400
    price = data.get("price", None)
    try:
        price = int(price)
    except (ValueError, TypeError):
        return jsonify(message="Invalid price", statusText="Invalid price"), 400
    if price < van.price_per_day or price < 1:
        return jsonify(message="Wrong price", statusText="Invalid price"), 400
    if price > 2_000_000:
        # SQL INTEGER HAS A RENGE: -2,147,483,648 to 2,147,483,647; floor to 2 millions;
        return jsonify(message="Price too large", statusText="Invalid price"), 400
    # check if the total price was calculated correctly on the request side
    correct_price = (rent_expiration - rent_commencement).days * van.price_per_day
    if price != correct_price:
        return jsonify(message="Price miscalculated", statusText="Wrong price"), 400
    try:
        transaction = Transaction(
            uuid=uuid4(), 
            lessee_name=lessee_name,
            lessee_surname=lessee_surname,
            lessee_email=lessee_email,
            price=price,
            rent_commencement=rent_commencement,
            rent_expiration=rent_expiration,
            lessor_id=van.host_id,
            van_id=van.id
        )
        db.session.add(transaction)
        db.session.commit()
        # NOTE: 'success' field is needed for redirecting inside MakeTransaction's loader
        return jsonify(message="Transaction created", statusText="Create successful", success=True), 200
    except Exception:
        return jsonify(message="Server Error", statusText="Failed to delete"), 500


@app.route('/makeReview', methods=['POST'])
def make_review():
    # no authorization required
    data = request.get_json()
    vanUUID = data.get("vanUUID", None)  # vanUUID is a string
    try:
        van = Van.query.filter_by(uuid=UUID(vanUUID)).first()  # UUID(vanUUID) is a UUID
    except Exception:
        return jsonify(message="Invalid UUID", statusText="Invalid UUID format"), 400
    if not van:
        return jsonify(message="The Van does not exist", statusText="Failed to read"), 400
    author = str(data.get("author")).strip() if data.get("author") else None # no capitalization here
    review = str(data.get("review")).strip() if data.get("review") else None
    rating = data.get("rating", None)  # the conversion is below
    if not (rating and author and review):
        return jsonify(message="Required data missing", statusText="Data missing"), 400
    try:
        rating = int(rating)
    except (ValueError, TypeError):
        return jsonify(message="Invalid rating format", statusText="Inadmissible rating"), 400
    if rating not in range(1, 6):
        return jsonify(message="Rating must be 1 to 5", statusText="Inadmissible rating"), 400
    try:
        review = Review(
            uuid=uuid4(),
            author=author,
            text=review,
            rate=rating,
            owner_id=van.host_id,
            van_id=van.id,
            van_name=van.name,
            van_uuid=van.uuid
        )
        db.session.add(review)
        db.session.commit()
        # NOTE: 'success' field is needed for redirecting inside MakeReview's loader
        return jsonify(message="Review created", statusText="Create successful", success=True), 200
    except Exception as e:
        print(e)
        return jsonify(message="Server Error", statusText="Failed to create"), 500


if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # spin up a DB if it does not exist already
    app.run(debug=True)
