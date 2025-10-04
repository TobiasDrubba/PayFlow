# PayFlow
Creates a simple transaction overview from combined sources, WeChat, Alipay, Tsinghua Student Card.

# Setup
Copy the .env files and fill in the values.
```
cp .env.example .env
cp frontend/.env.example frontend/.env
cp frontend/.env.example frontend/.env.docker
```

# Run for development with Docker
```
docker compose up
```
# Run for development
Start DB first.
```
docker compose -f docker-compose.yml -f docker-compose.override.yml up -d db
```
Then start the backend.
```
uvicorn app.main:app --reload
```
Finally, start the frontend.
```
cd frontend
npm start
```

# Run for production
```
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --pull always
```
