
Create a virtual environment:
python3 -m venv myenv

Activate the virtual environment:
Mac
source myenv/bin/activate 
Windows
myenv\Scripts\activate


Install the requirements:
pip install -r requirements.txt



Additional Code for adding S3 Uploads
# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = os.environ.get('DYNAMODB_TABLE')
# table = dynamodb.Table('mytest')

# Initialize S3 client
s3 = boto3.client('s3')
S3_BUCKET = os.environ.get('S3_BUCKET')
# S3_BUCKET = 'bymyckei3283'  # Replace with your S3 bucket name



@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # Generate a unique filename
    filename = str(uuid4()) + os.path.splitext(file.filename)[1]

    try:
        # Upload file to S3
        s3.upload_fileobj(file, S3_BUCKET, filename)
        file_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{filename}"
        return jsonify({'file_url': file_url}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500