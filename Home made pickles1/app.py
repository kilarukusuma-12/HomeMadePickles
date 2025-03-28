from flask import Flask, render_template, request, redirect, url_for, session, json
from werkzeug.security import generate_password_hash, check_password_hash
import boto3
from datetime import datetime
from werkzeug.security import check_password_hash
import json,uuid

app = Flask(__name__)
app.secret_key = 'your_very_secret_key_12345'  # Change for production!

dynamodb = boto3.resource('dynamodb', region_name='ap-south-1')  # e.g., 'us-east-1'
users_table = dynamodb.Table('Users')
orders_table = dynamodb.Table('Orders')

# # ================== TEMPORARY DATA STORES ==================
users = {
    'testuser': generate_password_hash('testpass')
}

products = {
    'non_veg_pickles': [
        {'id': 1, 'name': 'Chicken Pickle', 'weights': {'250': 600, '500': 1200, '1000': 1800}},
        {'id': 2, 'name': 'Fish Pickle', 'weights': {'250': 200, '500': 400, '1000': 800}},
        {'id': 3, 'name': 'Gongura Mutton', 'weights': {'250': 400, '500': 800, '1000': 1600}},
        {'id': 4, 'name': 'Mutton Pickle', 'weights': {'250': 400, '500': 800, '1000': 1600}},
        {'id': 5, 'name': 'Gongura Prawns', 'weights': {'250': 600, '500': 1200, '1000': 1800}},
        {'id': 6, 'name': 'Chicken Pickle (Gongura)', 'weights': {'250': 350, '500': 700, '1000': 1050}}
    ],
    'veg_pickles': [],  # Add your veg pickle products here
    'snacks': []        # Add your snack products here
}

# ================== AUTHENTICATION ROUTES ==================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        try:
            # Get user from DynamoDB
            response = users_table.get_item(
                Key={'username': username}
            )
            
            if 'Item' not in response:
                return render_template('login.html', error='User not found')
                
            user = response['Item']
            
            if check_password_hash(user['password'], password):
                session['logged_in'] = True
                session['username'] = username
                session.setdefault('cart', [])
                return redirect(url_for('home'))
                
            return render_template('login.html', error='Invalid password')
            
        except Exception as e:
            print(f"Database error: {str(e)}")
            return render_template('login.html', error='Login failed. Try again later')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        try:
            # Check if username exists
            response = users_table.get_item(
                Key={'username': username}
            )
            
            if 'Item' in response:
                return render_template('signup.html', error='Username already exists')
            
            # Create new user
            users_table.put_item(
                Item={
                    'username': username,
                    'email': email,
                    'password': generate_password_hash(password)
                }
            )
            
            return redirect(url_for('login'))
            
        except Exception as e:
            print(f"Signup error: {str(e)}")
            return render_template('signup.html', error='Registration failed. Please try again.')
    
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ================== PRODUCT PAGE ROUTES ==================
@app.route('/home')
def home():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('home.html')

@app.route('/non_veg_pickles')
def non_veg_pickles():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    search_query = request.args.get('search', '').lower()
    filtered_products = [p for p in products['non_veg_pickles'] 
                       if search_query in p['name'].lower()]
    
    return render_template('non_veg_pickles.html', 
                          products=filtered_products,
                          search_query=search_query)

@app.route('/veg_pickles')
def veg_pickles():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    search_query = request.args.get('search', '').lower()
    filtered_products = [p for p in products['veg_pickles'] 
                       if search_query in p['name'].lower()]
    
    return render_template('veg_pickles.html',
                          products=filtered_products,
                          search_query=search_query)

@app.route('/snacks')
def snacks():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    search_query = request.args.get('search', '').lower()
    filtered_products = [p for p in products['snacks'] 
                       if search_query in p['name'].lower()]
    
    return render_template('snacks.html',
                          products=filtered_products,
                          search_query=search_query)

# ================== CART FUNCTIONALITY ==================
@app.route('/cart')
def cart():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('cart.html')

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form['name']
            address = request.form['address']
            phone = request.form['phone']
            payment_method = request.form['payment']
            
            # Get cart data from hidden inputs
            cart_data = json.loads(request.form['cart_data'])
            total_amount = float(request.form['total_amount'])
            
            # Validate cart not empty
            if not cart_data:
                return render_template('checkout.html', error='Your cart is empty')
            
            # Create order record
            orders_table.put_item(
                Item={
                    'order_id': str(uuid.uuid4()),
                    'username': session['username'],
                    'name': name,
                    'address': address,
                    'phone': int(phone),  # Convert to number
                    'items': cart_data,
                    'total_amount': total_amount,
                    'payment_method': payment_method,
                    'timestamp': datetime.now().isoformat()
                }
            )
            
            # Clear client-side cart via JavaScript
            return redirect(url_for('sucess'))
            
        except json.JSONDecodeError:
            return render_template('checkout.html', error='Invalid cart data')
        except ValueError as e:
            return render_template('checkout.html', error='Invalid phone number format')
        except Exception as e:
            print(f"Checkout error: {str(e)}")
            return render_template('checkout.html', error='Failed to process order')
    
    return render_template('checkout.html')

@app.route('/sucess')
def success():
    return render_template('sucess.html')

if __name__ == '__main__':
    app.run(debug=True)
