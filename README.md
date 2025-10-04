# PayFlow
Creates a simple transaction overview from combined sources, WeChat, Alipay, Tsinghua Student Card.

# Setup
Copy the .env*_template files and rename them to .env*. Fill in the values.

# Run for development
`docker compose up`

# Run for production
`docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`

# Database
To only run the DB:
`docker compose -f docker-compose.yml -f docker-compose.override.yml up -d db`