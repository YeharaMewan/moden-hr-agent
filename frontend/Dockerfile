# Simple Frontend Dockerfile
FROM node:20-alpine

WORKDIR ./

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --network-timeout=600000 --only=production

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

# Start the application
CMD ["npm", "start"]