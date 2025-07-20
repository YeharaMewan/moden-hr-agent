# Start with an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# Using --no-cache-dir to reduce image size
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code from your host to your container at /app
COPY . .

# Run init_db.py to initialize the database with sample data
# Note: This assumes the MongoDB service is accessible during the build.
# A better approach is to run this from the docker-compose setup.
# We will handle this in the docker-compose file instead.
# RUN python init_db.py

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Define environment variables (can be overridden by docker-compose)
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# Run app.py when the container launches
# Use gunicorn for production or flask run for development
# For this example, we use flask run
CMD ["flask", "run"]