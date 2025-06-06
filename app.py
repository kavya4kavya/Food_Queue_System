# app.py - Main Flask Application with MySQL Connector
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import mysql.connector
from mysql.connector import Error
import os
from decimal import Decimal

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'database': 'quickbite_db',
    'user': 'username',
    'password': 'password',
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci'
}

def get_db_connection():
    """Create and return a database connection"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def init_database():
    """Initialize database tables"""
    connection = get_db_connection()
    if connection is None:
        return False
    
    cursor = connection.cursor()
    
    try:
        # Create students table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id VARCHAR(20) UNIQUE NOT NULL,
                full_name VARCHAR(100) NOT NULL,
                email VARCHAR(120) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                cancellation_count INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create menu_items table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS menu_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                price DECIMAL(10, 2) NOT NULL,
                emoji VARCHAR(10),
                available BOOLEAN DEFAULT TRUE
            )
        """)
        
        # Create orders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT NOT NULL,
                total_amount DECIMAL(10, 2) NOT NULL,
                status VARCHAR(20) DEFAULT 'Placed',
                payment_method VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                estimated_time INT DEFAULT 15,
                FOREIGN KEY (student_id) REFERENCES students(id)
            )
        """)
        
        # Create order_items table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                order_id INT NOT NULL,
                menu_item_id INT NOT NULL,
                quantity INT DEFAULT 1,
                price DECIMAL(10, 2) NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (menu_item_id) REFERENCES menu_items(id)
            )
        """)
        
        connection.commit()
        
        # Add sample menu items if they don't exist
        cursor.execute("SELECT COUNT(*) FROM menu_items")
        count = cursor.fetchone()[0]
        
        if count == 0:
            sample_items = [
                ('Classic Burger', 'Juicy beef patty with fresh lettuce, tomato, and special sauce', 8.99, '🍔'),
                ('Margherita Pizza', 'Fresh mozzarella, basil, and tomato sauce on crispy crust', 12.99, '🍕'),
                ('Caesar Salad', 'Crisp romaine lettuce with parmesan and croutons', 6.99, '🥗'),
                ('Chicken Wrap', 'Grilled chicken with vegetables in a soft tortilla', 7.99, '🌯'),
            ]
            
            cursor.executemany("""
                INSERT INTO menu_items (name, description, price, emoji) 
                VALUES (%s, %s, %s, %s)
            """, sample_items)
            
            connection.commit()
        
        return True
        
    except Error as e:
        print(f"Error creating tables: {e}")
        return False
    finally:
        cursor.close()
        connection.close()

# Database helper functions
def get_student_by_email(email):
    """Get student by email"""
    connection = get_db_connection()
    if connection is None:
        return None
    
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM students WHERE email = %s", (email,))
        return cursor.fetchone()
    except Error as e:
        print(f"Error fetching student: {e}")
        return None
    finally:
        cursor.close()
        connection.close()

def get_student_by_id(student_id):
    """Get student by ID"""
    connection = get_db_connection()
    if connection is None:
        return None
    
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM students WHERE id = %s", (student_id,))
        return cursor.fetchone()
    except Error as e:
        print(f"Error fetching student: {e}")
        return None
    finally:
        cursor.close()
        connection.close()

def create_student(student_id, full_name, email, password_hash):
    """Create a new student"""
    connection = get_db_connection()
    if connection is None:
        return False
    
    cursor = connection.cursor()
    try:
        cursor.execute("""
            INSERT INTO students (student_id, full_name, email, password_hash) 
            VALUES (%s, %s, %s, %s)
        """, (student_id, full_name, email, password_hash))
        connection.commit()
        return True
    except Error as e:
        print(f"Error creating student: {e}")
        return False
    finally:
        cursor.close()
        connection.close()

def get_available_menu_items():
    """Get all available menu items"""
    connection = get_db_connection()
    if connection is None:
        return []
    
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM menu_items WHERE available = TRUE")
        return cursor.fetchall()
    except Error as e:
        print(f"Error fetching menu items: {e}")
        return []
    finally:
        cursor.close()
        connection.close()

def get_menu_item_by_id(item_id):
    """Get menu item by ID"""
    connection = get_db_connection()
    if connection is None:
        return None
    
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM menu_items WHERE id = %s", (item_id,))
        return cursor.fetchone()
    except Error as e:
        print(f"Error fetching menu item: {e}")
        return None
    finally:
        cursor.close()
        connection.close()

def create_order(student_id, total_amount, payment_method='Credit Card'):
    """Create a new order and return the order ID"""
    connection = get_db_connection()
    if connection is None:
        return None
    
    cursor = connection.cursor()
    try:
        cursor.execute("""
            INSERT INTO orders (student_id, total_amount, payment_method) 
            VALUES (%s, %s, %s)
        """, (student_id, total_amount, payment_method))
        connection.commit()
        return cursor.lastrowid
    except Error as e:
        print(f"Error creating order: {e}")
        return None
    finally:
        cursor.close()
        connection.close()

def create_order_item(order_id, menu_item_id, quantity, price):
    """Create an order item"""
    connection = get_db_connection()
    if connection is None:
        return False
    
    cursor = connection.cursor()
    try:
        cursor.execute("""
            INSERT INTO order_items (order_id, menu_item_id, quantity, price) 
            VALUES (%s, %s, %s, %s)
        """, (order_id, menu_item_id, quantity, price))
        connection.commit()
        return True
    except Error as e:
        print(f"Error creating order item: {e}")
        return False
    finally:
        cursor.close()
        connection.close()

def get_student_orders(student_id):
    """Get all orders for a student"""
    connection = get_db_connection()
    if connection is None:
        return []
    
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT o.*, 
                   GROUP_CONCAT(CONCAT(mi.name, ' (', oi.quantity, ')') SEPARATOR ', ') as items
            FROM orders o
            LEFT JOIN order_items oi ON o.id = oi.order_id
            LEFT JOIN menu_items mi ON oi.menu_item_id = mi.id
            WHERE o.student_id = %s
            GROUP BY o.id
            ORDER BY o.created_at DESC
        """, (student_id,))
        return cursor.fetchall()
    except Error as e:
        print(f"Error fetching orders: {e}")
        return []
    finally:
        cursor.close()
        connection.close()

def get_order_by_id(order_id, student_id=None):
    """Get order by ID, optionally filtered by student"""
    connection = get_db_connection()
    if connection is None:
        return None
    
    cursor = connection.cursor(dictionary=True)
    try:
        if student_id:
            cursor.execute("""
                SELECT o.*, 
                       GROUP_CONCAT(CONCAT(mi.name, ' (', oi.quantity, ')') SEPARATOR ', ') as items
                FROM orders o
                LEFT JOIN order_items oi ON o.id = oi.order_id
                LEFT JOIN menu_items mi ON oi.menu_item_id = mi.id
                WHERE o.id = %s AND o.student_id = %s
                GROUP BY o.id
            """, (order_id, student_id))
        else:
            cursor.execute("""
                SELECT o.*, 
                       GROUP_CONCAT(CONCAT(mi.name, ' (', oi.quantity, ')') SEPARATOR ', ') as items
                FROM orders o
                LEFT JOIN order_items oi ON o.id = oi.order_id
                LEFT JOIN menu_items mi ON oi.menu_item_id = mi.id
                WHERE o.id = %s
                GROUP BY o.id
            """, (order_id,))
        return cursor.fetchone()
    except Error as e:
        print(f"Error fetching order: {e}")
        return None
    finally:
        cursor.close()
        connection.close()

def update_order_status(order_id, status):
    """Update order status"""
    connection = get_db_connection()
    if connection is None:
        return False
    
    cursor = connection.cursor()
    try:
        cursor.execute("UPDATE orders SET status = %s WHERE id = %s", (status, order_id))
        connection.commit()
        return True
    except Error as e:
        print(f"Error updating order status: {e}")
        return False
    finally:
        cursor.close()
        connection.close()

def update_student_cancellation_count(student_id):
    """Increment student's cancellation count"""
    connection = get_db_connection()
    if connection is None:
        return False
    
    cursor = connection.cursor()
    try:
        cursor.execute("""
            UPDATE students SET cancellation_count = cancellation_count + 1 
            WHERE id = %s
        """, (student_id,))
        connection.commit()
        return True
    except Error as e:
        print(f"Error updating cancellation count: {e}")
        return False
    finally:
        cursor.close()
        connection.close()

# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        student = get_student_by_email(email)
        
        if student and check_password_hash(student['password_hash'], password):
            session['student_id'] = student['id']
            session['student_name'] = student['full_name']
            flash('Login successful!', 'success')
            return redirect(url_for('menu'))
        else:
            flash('Invalid email or password!', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        student_id = request.form['student_id']
        email = request.form['email']
        password = request.form['password']
        
        # Check if student already exists
        if get_student_by_email(email):
            flash('Email already registered!', 'error')
            return render_template('login.html')
        
        # Check if student ID already exists
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()
            cursor.execute("SELECT id FROM students WHERE student_id = %s", (student_id,))
            if cursor.fetchone():
                flash('Student ID already registered!', 'error')
                cursor.close()
                connection.close()
                return render_template('login.html')
            cursor.close()
            connection.close()
        
        # Create new student
        password_hash = generate_password_hash(password)
        if create_student(student_id, full_name, email, password_hash):
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Registration failed! Please try again.', 'error')
    
    return render_template('login.html')

@app.route('/menu')
def menu():
    if 'student_id' not in session:
        return redirect(url_for('login'))
    
    menu_items = get_available_menu_items()
    return render_template('menu.html', menu_items=menu_items)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'student_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    item_id = request.json['item_id']
    quantity = request.json.get('quantity', 1)
    
    # Get or create cart in session
    if 'cart' not in session:
        session['cart'] = []
    
    # Add item to cart
    cart = session['cart']
    item_found = False
    
    for item in cart:
        if item['item_id'] == item_id:
            item['quantity'] += quantity
            item_found = True
            break
    
    if not item_found:
        menu_item = get_menu_item_by_id(item_id)
        if menu_item:
            cart.append({
                'item_id': item_id,
                'name': menu_item['name'],
                'price': float(menu_item['price']),
                'quantity': quantity
            })
    
    session['cart'] = cart
    return jsonify({'success': True, 'cart_count': len(cart)})

@app.route('/checkout', methods=['POST'])
def checkout():
    if 'student_id' not in session or 'cart' not in session:
        return redirect(url_for('login'))
    
    cart = session['cart']
    if not cart:
        flash('Cart is empty!', 'error')
        return redirect(url_for('menu'))
    
    # Calculate total
    total = sum(item['price'] * item['quantity'] for item in cart)
    
    # Create order
    order_id = create_order(session['student_id'], total)
    
    if order_id:
        # Add order items
        for item in cart:
            create_order_item(order_id, item['item_id'], item['quantity'], item['price'])
        
        # Clear cart
        session.pop('cart', None)
        
        # Get the created order for display
        order = get_order_by_id(order_id)
        return render_template('payment_success.html', order=order)
    else:
        flash('Order creation failed!', 'error')
        return redirect(url_for('menu'))

@app.route('/orders')
def orders():
    if 'student_id' not in session:
        return redirect(url_for('login'))
    
    student_orders = get_student_orders(session['student_id'])
    return render_template('orders.html', orders=student_orders)

@app.route('/order_status/<int:order_id>')
def order_status(order_id):
    if 'student_id' not in session:
        return redirect(url_for('login'))
    
    order = get_order_by_id(order_id, session['student_id'])
    if not order:
        flash('Order not found!', 'error')
        return redirect(url_for('orders'))
    
    return render_template('order_status.html', order=order)

@app.route('/cancel_order/<int:order_id>', methods=['GET', 'POST'])
def cancel_order(order_id):
    if 'student_id' not in session:
        return redirect(url_for('login'))
    
    order = get_order_by_id(order_id, session['student_id'])
    student = get_student_by_id(session['student_id'])
    
    if not order or not student:
        flash('Order or student not found!', 'error')
        return redirect(url_for('orders'))
    
    if request.method == 'POST':
        if student['cancellation_count'] >= 2:
            flash('Maximum cancellations reached!', 'error')
            return redirect(url_for('orders'))
        
        if order['status'] not in ['Placed', 'In Progress']:
            flash('Cannot cancel this order!', 'error')
            return redirect(url_for('orders'))
        
        if (update_order_status(order_id, 'Cancelled') and 
            update_student_cancellation_count(session['student_id'])):
            flash('Order cancelled successfully!', 'success')
        else:
            flash('Failed to cancel order!', 'error')
        
        return redirect(url_for('orders'))
    
    return render_template('cancel_order.html', order=order, student=student)

@app.route('/profile')
def profile():
    if 'student_id' not in session:
        return redirect(url_for('login'))
    
    student = get_student_by_id(session['student_id'])
    orders = get_student_orders(session['student_id'])
    
    # Calculate statistics
    total_orders = len(orders)
    completed_orders = len([o for o in orders if o['status'] == 'Completed'])
    total_spent = sum(float(o['total_amount']) for o in orders if o['status'] != 'Cancelled')
    
    return render_template('profile.html', student=student, orders=orders, 
                         total_orders=total_orders, completed_orders=completed_orders, 
                         total_spent=total_spent)

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('home'))

# API endpoint for live order tracking
@app.route('/api/order_status/<int:order_id>')
def api_order_status(order_id):
    if 'student_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    order = get_order_by_id(order_id, session['student_id'])
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    
    return jsonify({
        'status': order['status'],
        'estimated_time': order['estimated_time'],
        'created_at': order['created_at'].isoformat()
    })

# Initialize database
@app.before_first_request
def create_tables():
    init_database()

if __name__ == '__main__':
    app.run(debug=True)
