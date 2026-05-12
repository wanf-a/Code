# Backend

## Setup

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

## Run

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Default admin account: `admin` / `admin123`

