# Use the official Python image from the Docker Hub
FROM python:3.12-slim

# Create a new user
RUN adduser --disabled-password --gecos '' myuser

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container at /app
COPY . .

# Change ownership of the app directory to the new user
RUN chown -R myuser:myuser /app

# Switch to the new user
USER myuser

# Expose the port that the app runs on
EXPOSE 8000

# Command to run the Uvicorn server
CMD ["uvicorn", "cvscreening.main:app", "--host", "0.0.0.0", "--port", "8000"]