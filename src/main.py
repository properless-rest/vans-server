from flask import request, jsonify, abort
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required

from config import app, bcrypt, db
from models import User, Van


@app.route("/")
def home():
    return "<h1>SERVER ONLINE</h1>"


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    # request dict keys must correspond to the <input/ name="..."> 
    # from the FrontEnd side
    name = data['name']
    surname = data['surname']
    email = data['email']
    password = data['password']
    print(name, surname, email, password)
    if not (name and surname and email and password):
        return jsonify(
            {
                "message": "Required data is missing. Fill in all the fields", 
                "statusText": "required data missing",
                "statusCode": 400
            }
        )
    users_emails = list(map(lambda user: user.email, User.query.all()))
    if email in users_emails:
                return jsonify(
            {
                "message": "Cannot register this email", 
                "statusText": "emailNotUnique",
                "statusCode": 400
            }
        )
    # hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    # new_user = User(name=name, surname=surname, email=email, password=hashed_password)
    # db.session.add(new_user)
    # db.session.commit()
    return jsonify(message="User registered successfully", statusText="CREATE: success"), 201


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    # request dict keys must correspond to the <input/ name="..."> 
    # from the FrontEnd side
    email = data['email']
    password = data['password']
    user = User.query.filter_by(email=email).first()
    if user and bcrypt.check_password_hash(user.password, password):
        JWToken = create_access_token(identity={'email': user.email})
        return jsonify(JWToken=JWToken, status=200)
    else:
        return jsonify(message="Wrong email or password", statusText="READ: fail", status=401)


@app.route('/getUser', methods=['GET'])
@jwt_required()
def get_user():
    logged_username = get_jwt_identity()['email']
    if not logged_username:
        abort(message="Cannot fetcht the curent user", statusText="Failed to fetch", status=401)
    current_user = User.query.filter_by(email=logged_username).first()
    current_user_json = current_user.to_JSON()
    return jsonify(logged_user=current_user_json, statusText="User fetched successfully", status=200)


@app.route("/vans", methods=["GET"])
def get_vans():
    vans = Van.query.all()
    vans_json_list = list(map(lambda van: van.to_JSON(), vans))
    return jsonify({"vans": vans_json_list}, 200)


@app.route("/vans/<int:van_id>", methods=["GET"])
def get_van(van_id):
    van = Van.query.get(van_id)
    if not van:
        return jsonify({"message": "Van entry not found", "statusText": "record does not exist"}, 404)
    van_json = van.to_JSON()
    return jsonify({"van": van_json}, 200)


@app.route("/maker", methods=["POST"])
def make_model():
    price_per_day = request.json.get("pricePerDay")
    description = request.json.get("description")
    type = request.json.get("type")
    if not (price_per_day and description and type):
        return jsonify({"message": "Fill in all the  required fields", "statusText": "required data missing"}, 400)
    new_van = Van(price_per_day=price_per_day, description=description, type=type)
    try:
        db.session.add(new_van)
        db.session.commit()
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"message": "A new Van has been added"}), 201


if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # spin up a DB if it does not exist already
    app.run(debug=True)
