# WeAliPaymentOverview
Creates a simple transaction overview from combined sources, WeChat and Alipay

# Database
Create a database from postgres image, for instance:
`docker run --name my-postgres -e POSTGRES_USER=user -e POSTGRES_PASSWORD=secret -e POSTGRES_DB=weali_db -p 5432:5432 -d postgres:15
`