**README.md**

## Local Setup

### Clone the Repository
```bash
git clone <repository-url>
cd interview-evaluation-system
```

### Install Dependencies
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Configure Environment Variables
Copy the `.env` example below and update it with your credentials:
```
OPENAI_API_KEY=sk-...
POSTGRES_USER=postgres
POSTGRES_PASSWORD=analytics123
POSTGRES_HOST=34.132.249.54
POSTGRES_PORT=5432
POSTGRES_DB=postgres
```
Save it as `.env` in the project root.

### Run the Application
```bash
python main.py
```
The Flask server will start on `http://0.0.0.0:5000`.

### Test with providing endpoint details

#### Run the following commands one-by one in powershell:
```bash
$headers = @{ "Content-Type" = "application/json" }
$body = '{"user_id": "621", "job_post_id": "14"}'
Invoke-WebRequest -Uri "http://127.0.0.1:5000/evaluate" -Method Post -Headers $headers -Body $body
```
You would see the logs of the whole process in your environment terminal and evaluation table uploaded in SQL database

## Docker Setup

### Build the Docker Image
```bash
docker build -t interview-eval-system .
```

### Run the Container
```bash
docker run -p 5000:5000 --env-file .env interview-eval-system
```
Ensure the `.env` file is present in the directory where you run the command.

To test it's working, you can run the same powershell commands. Also you can do it for any other transcript. Try below for body:
```bash
$body = '{"user_id": "632", "job_post_id": "14"}' 
```
