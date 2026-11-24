# Use Python
FROM python:3.13-slim

# Set the working directory
WORKDIR /app

# Install Python packages
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy the project files
COPY app.py db.py models.py ./

# Expose Flask port
EXPOSE 5000

# Run the Flask application
CMD ["python", "app.py"]
