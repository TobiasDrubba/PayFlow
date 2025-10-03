# 1️⃣ Use an official Node image to build the frontend
FROM node:18-alpine AS build

# Set working directory inside container
WORKDIR /app

# Copy package.json & package-lock.json first (better caching)
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the source code
COPY . .

COPY .env.docker .env

# Build the React app for production
RUN npm run build

# 2️⃣ Use an official Nginx image to serve the production build
FROM nginx:alpine

# Copy built frontend from previous stage
COPY --from=build /app/build /usr/share/nginx/html

# Expose port 80
EXPOSE 80

# Nginx runs automatically when the container starts
CMD ["nginx", "-g", "daemon off;"]
