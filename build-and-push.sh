docker build -t tobiasdrubba/payflow-backend:latest . && \
docker push tobiasdrubba/payflow-backend:latest

docker build -t tobiasdrubba/payflow-frontend:latest ./frontend/ && \
docker push tobiasdrubba/payflow-frontend:latest