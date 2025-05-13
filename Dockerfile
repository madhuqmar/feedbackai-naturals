# Use official Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy files
COPY . /app

# Install dependencies
RUN pip3 install --no-cache-dir streamlit pandas boto3 plotly

# Expose Streamlit port
EXPOSE 8501

# Streamlit entry command
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
