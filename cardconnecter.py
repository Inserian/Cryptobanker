import os
import serial
import time
import uuid
import logging
from datetime import datetime
from cryptography.fernet import Fernet
from flask import Flask, jsonify, request, abort
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, CardTransaction  # Assuming models.py contains the ORM classes

# ------------------------ Configuration ------------------------

# Serial Port Configuration
SERIAL_PORT = '/dev/ttyUSB0'  # Update based on your system
BAUDRATE = 9600
TIMEOUT = 1  # seconds

# Encryption
KEY_FILE = 'encryption.key'

# Database
DATABASE_URI = 'postgresql+psycopg2://user:password@localhost/banking_db?sslmode=require'

# Flask App Configuration
APP_HOST = '0.0.0.0'
APP_PORT = 5000
SSL_CERT = '/path/to/cert.pem'
SSL_KEY = '/path/to/key.pem'

# Logging Configuration
LOG_FILE = 'app.log'
LOG_LEVEL = logging.INFO

# ---------------------------------------------------------------

# Initialize Logging
logging.basicConfig(
    filename=LOG_FILE,
    level=LOG_LEVEL,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Load Encryption Key
def load_encryption_key():
    if not os.path.exists(KEY_FILE):
        logging.critical("Encryption key file missing.")
        raise FileNotFoundError("Encryption key file missing.")
    
    with open(KEY_FILE, 'rb') as key_file:
        key = key_file.read()
    
    return Fernet(key)

cipher_suite = load_encryption_key()

# Initialize Database
engine = create_engine(DATABASE_URI)
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(engine)

# Initialize Flask App
app = Flask(__name__)

# ------------------------ Utility Functions ------------------------

def read_card_data():
    try:
        with serial.Serial(SERIAL_PORT, BAUDRATE, timeout=TIMEOUT) as ser:
            logging.info(f"Listening on {SERIAL_PORT} at {BAUDRATE} baudrate.")
            card_data = ''
            start_time = time.time()
            while True:
                if ser.in_waiting:
                    data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                    card_data += data
                    if '\n' in data:
                        break
                if time.time() - start_time > 5:
                    logging.warning("Card read timeout.")
                    break
                time.sleep(0.1)
            if card_data:
                logging.info("Card data received.")
                return card_data.strip()
            else:
                logging.warning("No card data received.")
                return None
    except serial.SerialException as e:
        logging.error(f"Serial exception: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return None

def tokenize_card_data(card_data):
    """
    Tokenize the card data to replace sensitive information.
    """
    token = str(uuid.uuid4())
    encrypted_data = cipher_suite.encrypt(card_data.encode('utf-8'))
    return token, encrypted_data

def store_transaction(token, encrypted_data):
    """
    Store the token and encrypted card data in the database.
    """
    session = SessionLocal()
    try:
        transaction = CardTransaction(
            token=token,
            encrypted_data=encrypted_data,
            timestamp=datetime.utcnow().isoformat()
        )
        session.add(transaction)
        session.commit()
        logging.info(f"Transaction stored with token: {token}")
    except Exception as e:
        session.rollback()
        logging.error(f"Database error: {e}")
        raise
    finally:
        session.close()

def validate_card_data(card_data):
    """
    Perform validation checks on the card data.
    Implement Luhn algorithm and other necessary validations.
    """
    # Placeholder for actual validation logic
    # Implement Luhn check and other validations here
    return True

def process_transaction(token, encrypted_data):
    """
    Integrate with the banking API to process the transaction.
    """
    # Placeholder for API integration
    # Ensure secure API calls with authentication and encryption
    # Example:
    # response = requests.post('https://secure-banking-api/transactions', json=payload, headers=headers, verify=True)
    # Handle response securely
    pass

# ------------------------ Flask Routes ------------------------

@app.route('/read_card', methods=['POST'])
def read_card():
    card_data = read_card_data()
    if card_data:
        if not validate_card_data(card_data):
            logging.warning("Invalid card data.")
            abort(400, description="Invalid card data.")
        
        token, encrypted_data = tokenize_card_data(card_data)
        try:
            store_transaction(token, encrypted_data)
            process_transaction(token, encrypted_data)
            return jsonify({'status': 'success', 'token': token}), 200
        except Exception as e:
            logging.error(f"Transaction processing failed: {e}")
            abort(500, description="Transaction processing failed.")
    else:
        abort(400, description="No card data received.")

@app.route('/transaction/<token>', methods=['GET'])
def get_transaction(token):
    session = SessionLocal()
    try:
        transaction = session.query(CardTransaction).filter_by(token=token).first()
        if not transaction:
            logging.warning(f"Transaction not found for token: {token}")
            abort(404, description="Transaction not found.")
        
        decrypted_data = cipher_suite.decrypt(transaction.encrypted_data).decode('utf-8')
        # Do not expose sensitive data directly; provide necessary information only
        response = {
            'token': transaction.token,
            'timestamp': transaction.timestamp,
            # Include other non-sensitive transaction details here
        }
        return jsonify(response), 200
    except Exception as e:
        logging.error(f"Error retrieving transaction: {e}")
        abort(500, description="Error retrieving transaction.")
    finally:
        session.close()

# ------------------------ Security Enhancements ------------------------

def enforce_https():
    """
    Redirect all HTTP traffic to HTTPS.
    """
    @app.before_request
    def before_request():
        if not request.is_secure and request.headers.get('X-Forwarded-Proto', 'http') != 'https':
            url = request.url.replace('http://', 'https://', 1)
            return redirect(url, code=301)

# Apply HTTPS enforcement
enforce_https()

# ------------------------ Application Entry Point ------------------------

if __name__ == "__main__":
    # Run the Flask app with SSL
    context = (SSL_CERT, SSL_KEY)
    app.run(host=APP_HOST, port=APP_PORT, ssl_context=context, threaded=True)
