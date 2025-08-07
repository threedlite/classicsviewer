FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install --omit=dev

# Copy application files
COPY . .

# Create mount point for database
RUN mkdir -p /data

# Expose port
EXPOSE 3000

# Set environment variable for database path
ENV DB_PATH=/data/perseus_texts.db

# Start the application
CMD ["node", "server.js"]