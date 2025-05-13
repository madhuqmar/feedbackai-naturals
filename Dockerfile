# Use official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy files
COPY . /app

# Install dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Set environment variables
ENV AWS_ACCESS_KEY_ID=AKIAYS2NT2EVWCZ4HWGG
ENV AWS_SECRET_ACCESS_KEY=A9H/cjLkvPuI12OFq/9RYaCfhmSEL00VWCUNJeg
ENV AWS_DEFAULT_REGION=us-east-2

# Expose Streamlit port
EXPOSE 8080

# Streamlit entry command
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
