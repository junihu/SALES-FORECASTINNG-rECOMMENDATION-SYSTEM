from flask import Flask, render_template, request, redirect, url_for, flash, session, Response, abort
import sqlite3
import os
import random
import string
import smtplib
from email.mime.text import MIMEText
from flask import Flask
from flask_mail import Mail, Message
import csv
from flask import Flask, render_template, request, send_from_directory
import io
from flask import jsonify
from werkzeug.utils import secure_filename
import json
import time
import atexit
from apscheduler.schedulers.background import BackgroundScheduler
import Levenshtein


def task():
    emails = get_emails();
    send_scheduled_email(emails);

scheduler = BackgroundScheduler()
#scheduler.add_job(func=task, trigger="interval", seconds=10)
scheduler.add_job(func=task, trigger="cron", day_of_week="tue", hour=11, minute=27)

scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())


app = Flask(__name__)
DB_NAME = 'users.db'
mail = Mail(app)
app.secret_key = 'yfwc8nyf74wcynr8orynrywi'

# Route to serve files from the "uploads" folder
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)





def get_emails():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT email FROM users")
    emails = c.fetchall()
    conn.close()
    # Extract email addresses from the fetched rows
    email_list = [email[0] for email in emails if email[0] is not None]
    return email_list

def get_name(email):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT first_name, last_name FROM users WHERE email = ?", (email,))
    user = c.fetchone()
    conn.close()
    name = ""
    if user:
        for x in user:
            name += x + " ";
    return name

def generate_otp():
    otp = ''.join(random.choices(string.digits, k=6))
    return otp

def send_otp_email(email, otp):
    smtp_server = 'smtp.gmail.com'  # SMTP server address
    smtp_port = 587  # SMTP port (587 for TLS)
    sender_email = 'f200248@cfd.nu.edu.pk'  # Sender's email address
    sender_password = 'Talha03232469301'  # Sender's email password

    msg = MIMEText(f'Your OTP is: {otp}')
    msg['Subject'] = 'OTP for Registration'
    msg['From'] = sender_email
    msg['To'] = email

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        
def send_scheduled_email(email):
    smtp_server = 'smtp.gmail.com'  # SMTP server address
    smtp_port = 587  # SMTP port (587 for TLS)
    sender_email = 'f200248@cfd.nu.edu.pk'  # Sender's email address
    sender_password = 'Talha03232469301'  # Sender's email password
    
    msg = MIMEText(f'This is an automatic email')
    msg['Subject'] = 'test'
    msg['From'] = sender_email

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        
    
        for one in email:
            msg['To'] = one;
            server.send_message(msg)


# Initialize database
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  first_name TEXT,
                  last_name TEXT,
                  email TEXT UNIQUE,
                  password TEXT)''')
    conn.commit()
    conn.close()
init_db()
# Modify the save_csv_data function to create a new table for each userdef save_csv_data(email, csv_data):
def save_csv_data(email, csv_data):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Create a new table with the user's email as the table name
    table_name = email.replace('@', '').replace('.', '')  # Replace special characters in email
    c.execute('''CREATE TABLE IF NOT EXISTS {} (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 L1_Category TEXT,
                 L2_Category TEXT,
                 product_name TEXT,
                 sku TEXT,
                 GMV INTEGER,
                 Gross_Items INTEGER,
                 Gross_Orders INTEGER,
                 NMV INTEGER,
                 Net_items INTEGER,
                 NetOrders INTEGER)'''.format(table_name))
    
    # Insert CSV data into the table
    for row in csv_data[1:]:  # Skip header row
        c.execute("INSERT INTO {} (L1_Category, L2_Category, product_name, sku, GMV, Gross_Items, Gross_Orders, NMV, Net_items, NetOrders) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)".format(table_name),
                  (row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9]))
    
    conn.commit()
    conn.close()


"""def clear_search_history():
    try:
        # Connect to the database
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        
        # Execute the DELETE statement
        cursor.execute("DELETE FROM search_history")
        
        # Commit the changes
        conn.commit()
        print("Search history cleared successfully.")
    except sqlite3.Error as e:
        print("Error clearing search history:", e)
    finally:
        # Close the connection
        if conn:
            conn.close()

# Call the function to clear search history
clear_search_history()"""

# Modify the create_products_table function to include the image_path column
def create_products_table():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Define the SQL statement to create the products table
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price REAL NOT NULL,
        description TEXT,
        image_path TEXT  -- New column for storing image path
    );
    """

    # Execute the SQL statement
    cursor.execute(create_table_sql)

    # Commit the changes and close the connection
    conn.commit()
    conn.close()

# Call the function to create the products table
create_products_table()


@app.route('/product/<int:product_id>', methods=['GET', 'POST'])
def product(product_id):
    if request.method == 'POST':
        # Handle review submission
        username = session.get('email')  # Assuming you're storing the logged-in user's email in the session
        stars = int(request.form['stars'])
        review_text = request.form['review']

        # Validate review data
        if not (1 <= stars <= 5):
            flash('Stars must be between 1 and 5.', 'error')
            return redirect(url_for('product', product_id=product_id))
        if not review_text.strip():
            flash('Review text cannot be empty.', 'error')
            return redirect(url_for('product', product_id=product_id))

        # Insert the review data into the 'reviews' table
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO reviews (id, product_id, username, stars, review) VALUES (NULL, ?, ?, ?, ?)",
                       (product_id, username, stars, review_text))
        conn.commit()
        conn.close
        flash('Review submitted successfully!', 'success')
        # Redirect to the same product page to avoid form resubmission on page reload
        return redirect(url_for('product', product_id=product_id))

    # Fetch product details from the database based on the product ID
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    product_data = cursor.fetchone()
    conn.close()

    if product_data is None:
        abort(404)  # Product not found

    # Fetch existing reviews for the product from the 'reviews' table
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, CAST(stars AS INTEGER), review FROM reviews WHERE product_id = ?", (product_id,))
    reviews = cursor.fetchall()
    conn.close()

    return render_template('product.html', product=product_data, reviews=reviews)
# Other routes and functions...


"""def fetch_products_from_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    conn.close()
    return products"""

def create_reviews_table():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Define the SQL statement to create the products table
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        username TEXT NOT NULL,
        stars REAL NOT NULL,
        review TEXT NOT NULL,
        FOREIGN KEY (product_id) REFERENCES products(id)
        );
    """

    # Execute the SQL statement
    cursor.execute(create_table_sql)

    # Commit the changes and close the connection
    conn.commit()
    conn.close()

# Call the function to create the products table
create_reviews_table()

def create_search_history_table():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Define the SQL statement to create the search history table
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS search_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT NOT NULL,
        search_query TEXT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_email) REFERENCES users(email)
    );
    """

    # Execute the SQL statement
    cursor.execute(create_table_sql)

    # Commit the changes and close the connection
    conn.commit()
    conn.close()

create_search_history_table()

"""def delete_user_table(email):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    table_name = email.replace('@', '').replace('.', '')  # Get the table name from the email
    c.execute("DROP TABLE IF EXISTS {}".format(table_name))
    conn.commit()
    conn.close()

delete_user_table('f200248@cfd.nu.edu.pk')"""

def fetch_csv_data(email):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Create a table name based on the user's email
    table_name = email.replace('@', '').replace('.', '')

    # Check if the table exists
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    table_exists = c.fetchone()

    if not table_exists:
        conn.close()
        return None  # Return None if the table doesn't exist for the user

    # Fetch CSV data from the table
    c.execute("SELECT * FROM {}".format(table_name))
    csv_data = c.fetchall()

    conn.close()
    return csv_data



# rank inventory tabel
def import_rank_inventory_from_csv():
    # Open the CSV file and read its contents
    with open('rank_inventory.csv', 'r') as csvfile:
        csv_reader = csv.DictReader(csvfile)

        # Connect to the database
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        # Create the rank_inventory table if it doesn't exist
        c.execute('''CREATE TABLE IF NOT EXISTS rank_inventory (
                     L1_Category TEXT,
                     L2_Category TEXT,
                     product_name TEXT,
                     sku TEXT,
                  	 GMV INTEGER,
                  	 Gross_Items INTEGER,
                     Gross_Orders INTEGER,
                  	 NMV INTEGER,
                     Net_items INTEGER,
                     NetOrders Integer)''')

        # Insert the CSV data into the rank_inventory table
        for row in csv_reader:
            c.execute("INSERT INTO rank_inventory (L1_Category, L2_Category, product_name, sku, GMV, Gross_Items, Gross_Orders, NMV, Net_items, NetOrders) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                      (row['L1_Category'], row['L2_Category'], row['product_name'], row['sku'], row['GMV'], row['Gross_Items'], row['Gross_Orders'], row['NMV'], row['Net_items'], row['NetOrders']))
        # Commit the changes and close the connection
        conn.commit()
        conn.close()
# Call the function to import the CSV data into the database
import_rank_inventory_from_csv()

# Registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    session.clear()
    if request.method == 'POST':
        first_name = request.form['firstName']
        last_name = request.form['lastName']
        email = request.form['email']
        password = request.form['password']
        data = {'fname': first_name, 'lname': last_name, 'email': email, 'password': password}
        #return redirect(url_for('page2', **data))
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        try:
            query = "SELECT * FROM users WHERE email = ?"
            records = c.execute(query, (email,))
            exists = records.fetchone()
            if exists:
                raise FileExistsError
            conn.close()
            otp = generate_otp()  # Generate OTP
            send_otp_email(email, otp)  # Send OTP via email
            # Store the OTP in the session or database for verification later
            #   For simplicity, I'll just store it in a session here
            session['otp'] = otp
            session['fname'] = first_name
            session['lname'] = last_name
            session['email'] = email
            session['password'] = password
            return redirect(url_for('verify'))
        except:
            conn.close()
            return render_template('signup.html', message="User already Exists!")

    return render_template('signup.html')
pass

@app.route('/', methods=['GET'])
@app.route('/index', methods=['GET'])
def index():
    session.clear()
    return render_template('index.html');


# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    session.clear()
    print(session.get("logged"))
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
        user = c.fetchone()
        conn.close()

        if user:
            # Redirect to profile editing page with user's ID
            session['email'] = email
            return redirect(url_for('home', user_id=user[0]))
        else:
            return render_template('login.html', message="Invalid Email or Password")

    return render_template('login.html')
pass

# Edit profile route
@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if not session.get('email'):
        return redirect(url_for('login'))
    
    email = session['email']  # No need to clear the session and set it again
    fname = ""  # Initialize variables
    lname = ""
    
    if request.method == "GET":
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT first_name, last_name FROM users WHERE email = ?", (email,))
        user = c.fetchone()
        conn.close()
        if user:
            fname = user[0]
            lname = user[1]
        
        return render_template('edit_profile.html', first_name=fname, last_name=lname, email=email)
    
    if request.method == "POST":
        first_name = request.form['firstName']
        last_name = request.form['lastName']
        email = request.form['email']
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE users SET first_name = ?, last_name = ? WHERE email = ?",
                  (first_name, last_name, email))
        conn.commit()
        conn.close()
        return redirect(url_for('home'))
pass


if __name__ == '__main__':
    init_db()  # Initialize database
    import_rank_inventory_from_csv()  # Import CSV data
    app.run(debug=True)


@app.route('/verify', methods=['GET', 'POST'])
def verify():
    first_name = session.get('fname')
    last_name = session.get('lname')
    email = session.get('email')
    password = session.get('password')
    if request.method == 'POST':
        k1 = request.form['ab']
        k2 = request.form['cd']
        k3 = request.form['ef']
        k4 = request.form['gh']
        k5 = request.form['ij']
        k6 = request.form['kl']
        entered_otp = k1 + k2 + k3 + k4 + k5 + k6
        stored_otp = session.get('otp')

        if entered_otp == stored_otp:
            # OTP verification successful, complete registration
            # Store user data in the database and redirect to login page
        
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            try:
                c.execute("INSERT INTO users (first_name, last_name, email, password) VALUES (?, ?, ?, ?)",
                          (first_name, last_name, email, password))
                conn.commit()
                conn.close()
                session.clear()
                return render_template('login.html')
            except sqlite3.IntegrityError:
                conn.close()
                return "User already exists!"
        
        else:
            # Incorrect OTP, prompt user to try again
            return render_template('verify.html', message="Incorrect OTP")
    return render_template('verify.html')
pass

@app.route('/resend_verification')
def resend_verification():
    if not session.get('email'):
        #return redirect(url_for('login'))
        print("hello world")
    email = session.get('email')
    otp = generate_otp()  # Generate OTP
    send_otp_email(email, otp)  # Send OTP via email
    # Store the OTP in the session or database for verification later
    #   For simplicity, I'll just store it in a session here
    session['otp'] = otp
    return jsonify({'message': 'Verification code resent successfully'})

@app.route('/home', methods=['GET'])
def home():
    if not session.get('email'):
        return redirect(url_for('login'))
    email = session.get('email')
    session.clear();
    session['email'] = email
    
    path = 'logo1.png';
    name = get_name(email);
    return render_template('home.html', message=name, image=path);
pass

@app.route('/customer', methods=['GET'])
def customer():
    if not session.get('email'):
        return redirect(url_for('login'))
    email = session.get('email')
    session.clear();
    session['email'] = email
    
    name = get_name(email);
    return render_template('customer.html', message=name);


@app.route('/vendor', methods=['GET'])
def vendor():
    if not session.get('email'):
        return redirect(url_for('login'))
    email = session.get('email')
    session.clear();
    session['email'] = email
    
    name = get_name(email);
    return render_template('vendor.html', message=name);

# Define the directory to store uploaded images
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Update the /cpage2 route to handle form submission
@app.route('/cpage2', methods=['GET', 'POST'])
def cpage2():
    if request.method == 'POST':
        # Check if the form submission is for comparing products
        if 'selected_product' in request.form:
            selected_product_ids = request.form.getlist('selected_product')
            if len(selected_product_ids) != 2:
                return "Please select exactly two products to compare."
            # Assuming you have a function to retrieve product details from the database
            selected_products = [get_product_by_id(product_id) for product_id in selected_product_ids]
            return render_template('cpage3.html', products=selected_products)
        else:
            # Retrieve form data for product addition
            name = request.form.get('name')
            price = request.form.get('price')
            description = request.form.get('description')
            image = request.files.get('image')

            # Save image to server
            if image:
                filename = secure_filename(image.filename)
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image.save(image_path)

                # Save product details to database
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO products (name, price, description, image_path) VALUES (?, ?, ?, ?)",
                               (name, price, description, filename))  # Save only filename to the database
                conn.commit()
                conn.close()

                flash('Product added successfully!', 'success')  # Flash message for success
                return redirect(url_for('cpage2'))  # Redirect to the same page after product addition

            # Retrieve search query from form data
            search_query = request.form.get('search_query')

            # Store search history in the database
            if search_query:
                # Get the user's email from the session
                if 'email' in session:
                    user_email = session['email']
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO search_history (user_email, search_query) VALUES (?, ?)",
                                   (user_email, search_query))
                    conn.commit()
                    conn.close()
                    flash('Search query added to history!', 'success')  # Flash message for success
                else:
                    flash('User not logged in!', 'error')  # Flash message for error

    # Fetch relevant products based on search queries and keywords
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Fetch products based on search query
    search_query = request.form.get('search_query')
    if search_query:
        products = search_products_with_error(search_query, 2)
        #cursor.execute("SELECT * FROM products WHERE name LIKE ?", ('%' + search_query + '%',))
        #products = cursor.fetchall()
    else:
        # Fetch all products if no search query is provided
        cursor.execute("SELECT * FROM products")
        products = cursor.fetchall()
    
    # Fetch search queries from the search history
    search_queries = []
    cursor.execute("SELECT search_query FROM search_history")
    rows = cursor.fetchall()
    for row in rows:
        search_queries.append(row[0])
        
    # Fetch user emails from search history
    user_emails = set()
    cursor.execute("SELECT DISTINCT user_email FROM search_history")
    rows = cursor.fetchall()
    for row in rows:
        user_emails.add(row[0])
        
    conn.close()

    return render_template('cpage2.html', products=products, search_queries=search_queries, user_emails=user_emails)


def search_products_with_error(search_query, max_error=2):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Generate variations of the search query with increasing errors
    variations = generate_variations(search_query, max_error)
    
    # Create the SQL query with OR conditions for each variation
    query = "SELECT * FROM products WHERE "
    query += " OR ".join(["name LIKE ?" for _ in variations])
    
    cursor.execute(query, tuple('%' + variation + '%' for variation in variations))
    products = cursor.fetchall()
    
    conn.close()
    return products

def generate_variations(search_query, max_error):
    variations = set()
    variations.add(search_query)  # Add the original query
    alphabet = 'abcdefghijklmnopqrstuvwxyz'  # Define alphabet for character substitution
    
    # Generate variations with substitutions
    for i in range(len(search_query)):
        for char in alphabet:
            variation = search_query[:i] + char + search_query[i+1:]
            variations.add(variation)
    
    # Generate variations with insertions
    for i in range(len(search_query) + 1):
        for char in alphabet:
            for j in range(max_error):
                variation = search_query[:i] + char * j + search_query[i:]
                variations.add(variation)
                
    # Generate variations with character swaps
    for i in range(len(search_query) - 1):
        variation = search_query[:i] + search_query[i+1] + search_query[i] + search_query[i+2:]
        variations.add(variation)
    
    return list(variations)

@app.route('/cpage3', methods=['GET', 'POST'])
def cpage3():
    if not session.get('email'):
        return redirect(url_for('login'))

    email = session.get('email')
    session.clear()
    session['email'] = email

    if request.method == 'POST':
        selected_product_ids = request.form.getlist('selected_product')
        if len(selected_product_ids) != 2:
            return "Please select exactly two products to compare."
        # Assuming you have a function to retrieve product details from the database
        selected_products = [get_product_by_id(product_id) for product_id in selected_product_ids]
        
        # Fetch reviews for the selected products
        product_reviews = [get_reviews_for_product(product_id) for product_id in selected_product_ids]

        return render_template('cpage3.html', products=selected_products, product_reviews=product_reviews)
    else:
        return render_template('cpage3.html')  # Render the page for GET requests
    
def get_reviews_for_product(product_id):
    conn = sqlite3.connect('users.db') 
    cursor = conn.cursor()

    # Fetch reviews for the given product ID
    cursor.execute("SELECT * FROM reviews WHERE product_id = ?", (product_id,))
    reviews = cursor.fetchall()

    conn.close()
    return reviews




@app.route('/cpage4', methods=['GET', 'POST'])
def cpage4():
    if not session.get('email'):
        return redirect(url_for('login'))

    email = session.get('email')
    
    if request.method == 'POST':
        return render_template('cpage4.html')
    else:
        # Fetch user's latest search query from search history
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT search_query FROM search_history WHERE user_email = ? ORDER BY id DESC LIMIT 1", (email,))
        latest_search_row = cursor.fetchone()
        latest_search_query = latest_search_row[0] if latest_search_row else None

        # Fetch products matching latest search query
        latest_query_products = []
        if latest_search_query:
            cursor.execute("SELECT DISTINCT p.* FROM products p INNER JOIN search_history sh ON p.name LIKE '%' || sh.search_query || '%' WHERE sh.user_email = ? AND sh.search_query = ? ", (email, latest_search_query))
            latest_query_products = cursor.fetchall()

        # Fetch all products related to previous search queries
        cursor.execute("SELECT DISTINCT p.* FROM products p INNER JOIN search_history sh ON p.name LIKE '%' || sh.search_query || '%' WHERE sh.user_email = ? AND sh.search_query != ? ", (email, latest_search_query))
        previous_query_products = cursor.fetchall()

        conn.close()

        # Combine latest and previous query products
        all_products = latest_query_products + previous_query_products

        # Sort products based on reviews with stars above 3
        above = [];
        for product in all_products:
            new = get_average(product[0]);
            if new is not None:
                above.append(new);
                
        for i in range(len(above)):
            for j in range(0, len(above)-i-1):
                if above[j][1] < above[j+1][1]:
                    above[j], above[j+1] = above[j+1], above[j]
                
        
        #products_with_reviews_above_3 = [product for product in all_products if has_reviews_above_3(product[0])]
        #products_without_reviews_or_below_3 = [product for product in all_products if product not in products_with_reviews_above_3]
        #sorted_products = products_with_reviews_above_3 + products_without_reviews_or_below_3
        p = []
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        for product in above:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM products WHERE id = ?", (product[0],))
            records = cursor.fetchall()
            p.append(records[0])
        conn.close()
        sorted_list = [];
        for i in range(len(above)):
            for j in range(len(p)):
                if above[i][0] == p[j][0]:
                    sorted_list.append(p[j])     

        return render_template('cpage4.html', products=sorted_list)
    
def get_average(product):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT product_id, stars FROM reviews WHERE product_id = ?", (product,))
    records = cursor.fetchall()
    conn.close()
    if records:
        product = []
        rating = []
        count = 0;
        for record in records:
            count += record[1];
        return (record[0], count/len(records));
    else:
        return None;

def has_reviews_above_3(product_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM reviews WHERE product_id = ? AND stars > 3", (product_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0





if __name__ == '__main__':
    app.run(debug=True)


def get_product_by_id(product_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    product = cursor.fetchone()
    conn.close()
    return product


@app.route('/vpage1', methods=['GET', 'POST'])
def vpage1():
    if not session.get('email'):
        return redirect(url_for('login'))

    email = session.get('email')

    if request.method == 'POST':
        if 'csvFile' not in request.files:
            flash("No file part")
            return redirect(request.url)
        
        file = request.files['csvFile']
        
        if file.filename == '':
            flash("No selected file")
            return "No selected file"
        
        if file:
            try:
                # Read CSV data
                stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
                csv_data = list(csv.reader(stream))
                stream.seek(0)  # Reset stream position to beginning
                next(stream)    # Skip header row
                
                # Save CSV data to the database
                save_csv_data(email, csv_data)
                
                # Fetch CSV data from the database
                flash("CSV data uploaded successfully!")
                
                # Display CSV data on the same page
                return redirect(url_for('vpage1'))
            except Exception as e:
                # Handle exceptions
                flash(f"An error occurred: {str(e)}")
                return redirect(request.url)

    else:  # GET request
        # Fetch CSV data from the database
        fetched_csv_data = fetch_csv_data(email)
        
        # Check if fetched_csv_data exists
    if fetched_csv_data:
        # Adjust fetched_csv_data to remove duplicates from the first row
        fetched_csv_data_no_duplicates = [fetched_csv_data[0]]  # Initialize with the first row
        for row in fetched_csv_data[1:]:
            if row != fetched_csv_data_no_duplicates[-1]:  # Compare with the last row in the list
                fetched_csv_data_no_duplicates.append(row)
        
        column_names = ['Sr', 'L1 Category', 'L2 Category', 'Product Name', 'SKU', 'GMV', 'Gross Items', 'Gross Orders', 'NMV', 'Net Items', 'Net Orders']
        return render_template('vpage1.html', message=email, csv_data=fetched_csv_data_no_duplicates, column_names=column_names)
    else:
        return render_template('vpage1.html', message=email)


# Function to save new row data to the database
def save_new_row_to_database(email, new_row_data):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    table_name = email.replace('@', '').replace('.', '')  # Get the table name from the email

    # Check if the row already exists in the database
    try:
        # Find the current maximum ID in the table
        c.execute(f"SELECT MAX(id) FROM {table_name}")
        max_id = c.fetchone()[0] or 0  # Get the maximum ID, default to 0 if no rows in the table
        
        # Assign the new row ID as one greater than the current maximum
        new_row_id = max_id + 1

        # Insert the new row into the database with the assigned ID
        c.execute("INSERT INTO {} (id, L1_Category, L2_Category, product_name, sku, GMV, Gross_Items, Gross_Orders, NMV, Net_items, NetOrders) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)".format(table_name),
                  (new_row_id, new_row_data[0], new_row_data[1], new_row_data[2], new_row_data[3], new_row_data[4], new_row_data[5], new_row_data[6], new_row_data[7], new_row_data[8], new_row_data[9]))
        conn.commit()
        conn.close()
        return True  # Return True if the row was successfully saved
    except Exception as e:
        print("Error saving new row:", e)
        conn.close()
        return False  # Return False if an error occurred

# Route to save new row data
@app.route('/save_new_row', methods=['POST'])
def save_new_row():
    if not session.get('email'):
        return "User not logged in"
    
    email = session.get('email')
    new_row_data = request.form.getlist('rowData[]')  # Retrieve data from the request

    try:
        if save_new_row_to_database(email, new_row_data):
            return "New row data saved successfully"
        else:
            return "Row already exists"
    except Exception as e:
        return f"An error occurred: {str(e)}"
    

@app.route('/update_data', methods=['POST'])
def update_data():
    if not session.get('email'):
        return "User not logged in"

    email = session.get('email')
    data = request.get_json()
    updated_data = data.get('updatedData', {})  # Extract updatedData from the request
    print(updated_data)  # Print the received data for debugging
    # Process and update the data in the database
    try:
        update_data_in_database(email, updated_data)
        return jsonify(success=True)  # Return success response as JSON
    except Exception as e:
        return jsonify(success=False, error=str(e))  # Return error response as JSON

def update_data_in_database(email, updated_data):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Create a table name based on the user's email
    table_name = email.replace('@', '').replace('.', '')

    try:
        for column_name, row_data in updated_data.items():
            # Extract the updated value and row ID
            updated_value = row_data[0]  # Get the updated value
            row_id = row_data[1]  # Get the row ID

            # Construct the SQL query to update the specific row with the given column
            query = f"UPDATE {table_name} SET {column_name} = ? WHERE id = ?"
            print("SQL Query:", query)  # Print the constructed SQL query for debugging
            print("Updated Value:", updated_value)  # Print the updated value for debugging
            c.execute(query, (updated_value, row_id))

        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        print("Error updating data:", e)
        conn.rollback()
        conn.close()
        return False


@app.route('/delete_row', methods=['POST'])
def delete_row():
    if not session.get('email'):
        return jsonify(success=False, error="User not logged in")

    email = session.get('email')
    data = request.get_json()
    row_id = data.get('rowId')  # Extract the row ID from the request
    table_name = email.replace('@', '').replace('.', '')  # Get the table name from the email

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    try:
        # Delete the row
        query = f"DELETE FROM {table_name} WHERE id = ?"
        c.execute(query, (row_id,))
        
        # Update row IDs for remaining rows
        c.execute(f"UPDATE {table_name} SET id = id - 1 WHERE id > ?", (row_id,))
        
        conn.commit()
        conn.close()
        return jsonify(success=True)  # Return success response as JSON
    except sqlite3.Error as e:
        conn.rollback()
        conn.close()
        return jsonify(success=False, error=str(e))  # Return error response as JSON


@app.route('/download_csv', methods=['GET'])
def download_csv():
    email = session.get('email')
    csv_data = fetch_csv_data(email)  # Fetch CSV data from the database

    # Convert CSV data to a string
    csv_string = ''
    if csv_data:
        for row in csv_data:
            csv_string += ','.join(map(str, row)) + '\n'

    # Return CSV data as a response
    return Response(csv_string, mimetype='text/csv')


if __name__ == '_main_':
    app.run(debug=True)
    
@app.route('/get_data')
def get_data():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM rank_inventory ORDER BY NetOrders DESC")  # Order by NetOrders in descending order
    rank_inventory = c.fetchall()
    conn.close()
    return jsonify(rank_inventory);
    
@app.route('/vpage2', methods=['GET'])
def vpage2():
    if not session.get('email'):
        return redirect(url_for('login'))
    email = session.get('email')
    session.clear();
    session['email'] = email
    name = get_name(email);
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM rank_inventory ORDER BY NetOrders DESC")  # Order by NetOrders in descending order
    rank_inventory = c.fetchall()
    conn.close()

    return render_template('vpage2.html', rank_inventory=rank_inventory, message=name)
pass


import sqlite3

@app.route('/vpage3', methods=['GET'])
def vpage3():
    if not session.get('email'):
        return redirect(url_for('login'))

    email = session.get('email')
    name = get_name(email)

    # Check if the user's inventory table exists
    user_table_name = email.replace('@', '').replace('.', '')
    if not check_user_table_exists(user_table_name):
        return render_template('vpage3.html', message=name, no_data=True)

    # Fetch and rank inventory from user's table
    rank_inventory = fetch_and_rank_inventory(user_table_name)
    
    # Save ranked inventory to new table
    save_ranked_inventory(email, rank_inventory)

    # Display the ranked inventory
    return render_template('vpage3.html', message=name, rank_inventory=rank_inventory)

def check_user_table_exists(table_name):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    result = c.fetchone()[0]
    conn.close()
    return result > 0

def fetch_and_rank_inventory(table_name):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(f"SELECT * FROM {table_name} ORDER BY NetOrders DESC")  # Order by NetOrders in descending order
    rank_inventory = c.fetchall()
    conn.close()
    return rank_inventory

def save_ranked_inventory(email, rank_inventory):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    rank_table_name = f"rank_{email.replace('@', '').replace('.', '')}"
    
    # Create the rank table if it doesn't exist
    c.execute(f'''CREATE TABLE IF NOT EXISTS {rank_table_name} (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 L1_Category TEXT,
                 L2_Category TEXT,
                 product_name TEXT,
                 sku TEXT,
                 GMV INTEGER,
                 Gross_Items INTEGER,
                 Gross_Orders INTEGER,
                 NMV INTEGER,
                 Net_items INTEGER,
                 NetOrders INTEGER)''')
    
    # Fetch existing rows from the rank table
    c.execute(f"SELECT product_name FROM {rank_table_name}")
    existing_rows = [row[0] for row in c.fetchall()]
    
    # Insert or update rows in the rank table
    for row in rank_inventory:
        product_name = row[3]  # Assuming the product name is in the 4th column
        if product_name not in existing_rows:
            # Insert the row if it doesn't exist
            c.execute(f"INSERT INTO {rank_table_name} (L1_Category, L2_Category, product_name, sku, GMV, Gross_Items, Gross_Orders, NMV, Net_items, NetOrders) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                      (row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10]))
        else:
            # Update the row if it exists
            c.execute(f"UPDATE {rank_table_name} SET L1_Category=?, L2_Category=?, sku=?, GMV=?, Gross_Items=?, Gross_Orders=?, NMV=?, Net_items=?, NetOrders=? WHERE product_name=?",
                      (row[1], row[2], row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[3]))
    
    conn.commit()
    conn.close()


@app.route('/download_csvv', methods=['GET'])
def download_csvv():
    email = session.get('email')
    csv_data = fetch_csv_data(email)  # Fetch CSV data from the database

    # Convert CSV data to a string
    csv_string = ''
    if csv_data:
        for row in csv_data:
            csv_string += ','.join(map(str, row)) + '\n'

    # Return CSV data as a response
    return Response(csv_string, mimetype='text/csv')




# Define the route for vpage4
@app.route('/vpage4', methods=['GET', 'POST'])
def vpage4():
    # Redirect to login if user is not logged in
    if not session.get('email'):
        return redirect(url_for('login'))
    
    # Get the user's email from the session
    email = session.get('email')

    # Set the session email again
    session.clear()
    session['email'] = email

    # Get the user's name
    name = get_name(email)
    
    # Fetch products data from the rank_inventory table (overall)
    overall_products = fetch_products_from_rank_inventory()

    # Calculate profit margins for each product (overall)
    overall_products_with_margin = calculate_profit_margins(overall_products)
    
    try:
        # Fetch products data from the user's rank inventory table
        user_products = fetch_products_from_user(email)

        # Calculate profit margins for each product (user)
        user_products_with_margin = calculate_profit_margins(user_products)

        # Calculate combined sum of profit margins for user's products
        user_combined_sum = sum([margin for _, margin in user_products_with_margin])

        # Calculate combined sum of profit margins for overall inventory
        overall_combined_sum = sum([margin for _, margin in overall_products_with_margin])
    except sqlite3.OperationalError:
        # Handle the case where the user's rank inventory table does not exist
        user_products_with_margin = []
        user_combined_sum = 0
        overall_combined_sum = 0

    # Render the vpage4 template with the user's name, products data, and combined sums
    return render_template('vpage4.html', message=name, user_products=user_products_with_margin, overall_products=overall_products_with_margin, user_combined_sum=user_combined_sum, overall_combined_sum=overall_combined_sum)

# Function to fetch products data from the user's rank inventory table
def fetch_products_from_user(email):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute(f"SELECT product_name, GMV, NMV FROM rank_{email.replace('@', '').replace('.', '')}")
    products = cursor.fetchall()
    conn.close()
    return products


# Function to fetch products data from the rank_inventory table
def fetch_products_from_rank_inventory():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT product_name, GMV, NMV FROM rank_inventory")
    products = cursor.fetchall()
    conn.close()
    return products


# Function to calculate profit margins for each product
def calculate_profit_margins(products):
    products_with_margin = []
    for product in products:
        product_name = product[0]
        gmv = product[1]
        nmv = product[2]
        
        # Calculate profit margin using the provided formula
        profit_margin = ((gmv - nmv) / gmv) * 100 if gmv != 0 else 0
        
        products_with_margin.append((product_name, profit_margin))
    
    return products_with_margin 

if __name__ == "__main__":
    app.run(debug=True)