# app.py - Main Flask Application
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://username:password@localhost/quickbite_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    cancellation_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    orders = db.relationship('Order', backref='student', lazy=True)

class MenuItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Decimal(10, 2), nullable=False)
    emoji = db.Column(db.String(10))
    available = db.Column(db.Boolean, default=True)
    
    order_items = db.relationship('OrderItem', backref='menu_item', lazy=True)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    total_amount = db.Column(db.Decimal(10, 2), nullable=False)
    status = db.Column(db.String(20), default='Placed')  # Placed, In Progress, Ready, Completed, Cancelled
    payment_method = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    estimated_time = db.Column(db.Integer, default=15)  # minutes
    
    items = db.relationship('OrderItem', backref='order', lazy=True)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_item.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    price = db.Column(db.Decimal(10, 2), nullable=False)

# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        student = Student.query.filter_by(email=email).first()
        
        if student and check_password_hash(student.password_hash, password):
            session['student_id'] = student.id
            session['student_name'] = student.full_name
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
        if Student.query.filter_by(email=email).first():
            flash('Email already registered!', 'error')
            return render_template('login.html')
        
        if Student.query.filter_by(student_id=student_id).first():
            flash('Student ID already registered!', 'error')
            return render_template('login.html')
        
        # Create new student
        password_hash = generate_password_hash(password)
        new_student = Student(
            student_id=student_id,
            full_name=full_name,
            email=email,
            password_hash=password_hash
        )
        
        db.session.add(new_student)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/menu')
def menu():
    if 'student_id' not in session:
        return redirect(url_for('login'))
    
    menu_items = MenuItem.query.filter_by(available=True).all()
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
        menu_item = MenuItem.query.get(item_id)
        cart.append({
            'item_id': item_id,
            'name': menu_item.name,
            'price': float(menu_item.price),
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
    new_order = Order(
        student_id=session['student_id'],
        total_amount=total,
        payment_method='Credit Card'
    )
    
    db.session.add(new_order)
    db.session.flush()  # Get the order ID
    
    # Add order items
    for item in cart:
        order_item = OrderItem(
            order_id=new_order.id,
            menu_item_id=item['item_id'],
            quantity=item['quantity'],
            price=item['price']
        )
        db.session.add(order_item)
    
    db.session.commit()
    
    # Clear cart
    session.pop('cart', None)
    
    return render_template('payment_success.html', order=new_order)

@app.route('/orders')
def orders():
    if 'student_id' not in session:
        return redirect(url_for('login'))
    
    student_orders = Order.query.filter_by(student_id=session['student_id']).order_by(Order.created_at.desc()).all()
    return render_template('orders.html', orders=student_orders)

@app.route('/order_status/<int:order_id>')
def order_status(order_id):
    if 'student_id' not in session:
        return redirect(url_for('login'))
    
    order = Order.query.filter_by(id=order_id, student_id=session['student_id']).first_or_404()
    return render_template('order_status.html', order=order)

@app.route('/cancel_order/<int:order_id>', methods=['GET', 'POST'])
def cancel_order(order_id):
    if 'student_id' not in session:
        return redirect(url_for('login'))
    
    order = Order.query.filter_by(id=order_id, student_id=session['student_id']).first_or_404()
    student = Student.query.get(session['student_id'])
    
    if request.method == 'POST':
        if student.cancellation_count >= 2:
            flash('Maximum cancellations reached!', 'error')
            return redirect(url_for('orders'))
        
        if order.status not in ['Placed', 'In Progress']:
            flash('Cannot cancel this order!', 'error')
            return redirect(url_for('orders'))
        
        order.status = 'Cancelled'
        student.cancellation_count += 1
        db.session.commit()
        
        flash('Order cancelled successfully!', 'success')
        return redirect(url_for('orders'))
    
    return render_template('cancel_order.html', order=order, student=student)

@app.route('/profile')
def profile():
    if 'student_id' not in session:
        return redirect(url_for('login'))
    
    student = Student.query.get(session['student_id'])
    orders = Order.query.filter_by(student_id=session['student_id']).all()
    
    # Calculate statistics
    total_orders = len(orders)
    completed_orders = len([o for o in orders if o.status == 'Completed'])
    total_spent = sum(float(o.total_amount) for o in orders if o.status != 'Cancelled')
    
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
    
    order = Order.query.filter_by(id=order_id, student_id=session['student_id']).first()
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    
    return jsonify({
        'status': order.status,
        'estimated_time': order.estimated_time,
        'created_at': order.created_at.isoformat()
    })

# Initialize database and sample data
@app.before_first_request
def create_tables():
    db.create_all()
    
    # Add sample menu items if they don't exist
    if MenuItem.query.count() == 0:
        sample_items = [
            MenuItem(name='Classic Burger', description='Juicy beef patty with fresh lettuce, tomato, and special sauce', price=8.99, emoji='🍔'),
            MenuItem(name='Margherita Pizza', description='Fresh mozzarella, basil, and tomato sauce on crispy crust', price=12.99, emoji='🍕'),
            MenuItem(name='Caesar Salad', description='Crisp romaine lettuce with parmesan and croutons', price=6.99, emoji='🥗'),
            MenuItem(name='Chicken Wrap', description='Grilled chicken with vegetables in a soft tortilla', price=7.99, emoji='🌯'),
        ]
        
        for item in sample_items:
            db.session.add(item)
        
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)
