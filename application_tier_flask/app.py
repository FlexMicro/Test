# Application tier for the FullStack App
from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
import os
import boto3
from uuid import uuid4
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
load_dotenv()


app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)
# Create a file handler
file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
# Set the logging level for the file handler
file_handler.setLevel(logging.DEBUG)
# Add the handler to the Flask app logger
app.logger.addHandler(file_handler)
# Also log to stdout
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
app.logger.addHandler(console_handler)

app.logger.info('Flask app startup')

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = os.environ.get('DYNAMODB_TABLE')
app.logger.info(f'DynamoDB table: {table}')

# Initialize S3 client
s3 = boto3.client('s3')
S3_BUCKET = os.environ.get('S3_BUCKET')
app.logger.info(f'S3 bucket: {S3_BUCKET}')

def init_database():
    try:
        app.logger.info('Initializing database connection')
        connection = mysql.connector.connect(
            host=os.environ.get('DB_HOST'),
            user=os.environ.get('DB_USER'),
            password=os.environ.get('DB_PASSWORD')
        )
        cursor = connection.cursor(dictionary=True)
        
        db_name = os.environ.get('DB_NAME')
        app.logger.info(f'Creating/using database: {db_name}')
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        cursor.execute(f"USE {db_name}")
        
        app.logger.info('Creating todos table if not exists')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS todos (
                id INT AUTO_INCREMENT PRIMARY KEY,
                task VARCHAR(255) NOT NULL,
                description TEXT,
                status ENUM('pending', 'in_progress', 'completed') DEFAULT 'pending',
                due_date DATE,
                priority ENUM('low', 'medium', 'high') DEFAULT 'medium',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        ''')
        connection.commit()
        app.logger.info('Database initialization successful')
        return connection, cursor
    
    except Exception as e:
        app.logger.error(f'Database initialization failed: {str(e)}', exc_info=True)
        raise e

try:
    db, cursor = init_database()
except Exception as e:
    app.logger.error(f'Failed to initialize database: {str(e)}', exc_info=True)
    raise e

# Get all todos with optional filters
@app.route('/api/todos', methods=['GET'])
def get_todos():
    try:
        # Get query parameters
        status = request.args.get('status')
        priority = request.args.get('priority')
        search = request.args.get('search')

        # Start building the query
        query = 'SELECT * FROM todos WHERE 1=1'
        params = []

        # Add filters if they exist
        if status:
            query += ' AND status = %s'
            params.append(status)
        if priority:
            query += ' AND priority = %s'
            params.append(priority)
        if search:
            query += ' AND (task LIKE %s OR description LIKE %s)'
            search_term = f'%{search}%'
            params.extend([search_term, search_term])

        # Add ordering
        query += ' ORDER BY created_at DESC'

        app.logger.debug(f'Executing query: {query} with params: {params}')
        cursor.execute(query, params)
        todos = cursor.fetchall()
        return jsonify(todos)
    except Exception as e:
        app.logger.error(f'Error getting todos: {str(e)}', exc_info=True)
        return jsonify({'error': str(e)}), 500

# Get a single todo by ID
@app.route('/api/todos/<int:id>', methods=['GET'])
def get_todo(id):
    try:
        cursor.execute('SELECT * FROM todos WHERE id = %s', (id,))
        todo = cursor.fetchone()
        if todo:
            return jsonify(todo)
        return jsonify({'error': 'Todo not found'}), 404
    except Exception as e:
        app.logger.error(f'Error getting todo {id}: {str(e)}', exc_info=True)
        return jsonify({'error': str(e)}), 500

# Add a new todo
@app.route('/api/todos', methods=['POST'])
def add_todo():
    try:
        data = request.json
        required_fields = ['task']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400

        # Prepare the query dynamically based on provided fields
        fields = []
        values = []
        placeholders = []
        
        # Handle all possible fields
        field_mapping = {
            'task': str,
            'description': str,
            'status': str,
            'due_date': str,
            'priority': str
        }

        for field, field_type in field_mapping.items():
            if field in data and data[field] is not None:
                fields.append(field)
                values.append(data[field])
                placeholders.append('%s')

        query = f'''
            INSERT INTO todos ({', '.join(fields)})
            VALUES ({', '.join(placeholders)})
        '''

        app.logger.debug(f'Executing insert query: {query} with values: {values}')
        cursor.execute(query, values)
        db.commit()

        # Fetch the newly created todo
        cursor.execute('SELECT * FROM todos WHERE id = %s', (cursor.lastrowid,))
        new_todo = cursor.fetchone()
        
        return jsonify(new_todo), 201
    except Exception as e:
        app.logger.error(f'Error adding todo: {str(e)}', exc_info=True)
        return jsonify({'error': str(e)}), 500

# Update a todo
@app.route('/api/todos/<int:id>', methods=['PUT', 'PATCH'])
def update_todo(id):
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No update data provided'}), 400

        # Verify todo exists
        cursor.execute('SELECT * FROM todos WHERE id = %s', (id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Todo not found'}), 404

        # Prepare the update query dynamically
        update_fields = []
        values = []
        
        # Handle all possible fields
        field_mapping = {
            'task': str,
            'description': str,
            'status': str,
            'due_date': str,
            'priority': str
        }

        for field, field_type in field_mapping.items():
            if field in data and data[field] is not None:
                update_fields.append(f'{field} = %s')
                values.append(data[field])

        if not update_fields:
            return jsonify({'error': 'No valid fields to update'}), 400

        values.append(id)  # Add id for WHERE clause
        query = f'''
            UPDATE todos 
            SET {', '.join(update_fields)}
            WHERE id = %s
        '''

        app.logger.debug(f'Executing update query: {query} with values: {values}')
        cursor.execute(query, values)
        db.commit()

        # Fetch and return the updated todo
        cursor.execute('SELECT * FROM todos WHERE id = %s', (id,))
        updated_todo = cursor.fetchone()
        return jsonify(updated_todo)
    except Exception as e:
        app.logger.error(f'Error updating todo {id}: {str(e)}', exc_info=True)
        return jsonify({'error': str(e)}), 500

# Delete a todo
@app.route('/api/todos/<int:id>', methods=['DELETE'])
def delete_todo(id):
    try:
        # Verify todo exists
        cursor.execute('SELECT * FROM todos WHERE id = %s', (id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Todo not found'}), 404

        cursor.execute('DELETE FROM todos WHERE id = %s', (id,))
        db.commit()
        return jsonify({'message': 'Todo deleted successfully'})
    except Exception as e:
        app.logger.error(f'Error deleting todo {id}: {str(e)}', exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload_file():
    app.logger.info('Starting file upload process')
    
    # Log request details
    app.logger.debug(f'Request files: {request.files}')
    app.logger.debug(f'Request form: {request.form}')
    
    if 'file' not in request.files:
        app.logger.error('No file part in request')
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    app.logger.info(f'Received file: {file.filename}')

    if file.filename == '':
        app.logger.error('Empty filename received')
        return jsonify({'error': 'No selected file'}), 400

    # Generate a unique filename
    filename = str(uuid4()) + os.path.splitext(file.filename)[1]
    app.logger.info(f'Generated unique filename: {filename}')

    try:
        app.logger.info(f'Attempting to upload file to S3 bucket: {S3_BUCKET}')
        # Log S3 client configuration
        app.logger.debug(f'S3 client config: region={s3.meta.region_name}')
        
        # Upload file to S3
        s3.upload_fileobj(file, S3_BUCKET, filename)
        file_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{filename}"
        app.logger.info(f'File successfully uploaded. URL: {file_url}')
        return jsonify({'file_url': file_url}), 201
    
    except Exception as e:
        app.logger.error(f'Error uploading file to S3: {str(e)}', exc_info=True)
        # Log additional S3 details that might help debugging
        app.logger.error(f'S3 bucket: {S3_BUCKET}')
        app.logger.error(f'File details - name: {file.filename}, size: {file.content_length if hasattr(file, "content_length") else "unknown"}')
        return jsonify({'error': str(e)}), 500

@app.route('/api/health')
def health_check():
    app.logger.debug('Health check endpoint called')
    return "Healthy!"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    app.logger.info(f'Starting Flask app on port {port}')
    app.run(host='0.0.0.0', port=port)