FROM apache/airflow:2.10.2

USER root

# Install necessary packages
RUN apt-get update && \
    apt-get install -y gcc g++ make gosu && \
    rm -rf /var/lib/apt/lists/*

USER airflow

# Set the working directory
WORKDIR /opt/airflow

# Copy requirements file
COPY requirements.txt .

# Install the required Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Install Airflow and Docker provider
ARG AIRFLOW_VERSION=2.10.2
RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" apache-airflow-providers-docker==2.1.0

# Copy the entire project directory into the container
COPY --chown=airflow:root . .

# Set the PYTHONPATH environment variable to include the project root
ENV PYTHONPATH="${PYTHONPATH}:/opt/airflow"

# The command to run when the container starts (if needed)
# CMD ["airflow", "webserver"]