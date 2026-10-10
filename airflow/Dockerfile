FROM apache/airflow:2.10.5-python3.12

USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends openjdk-17-jre-headless procps \
 && ln -s "$(dirname "$(dirname "$(readlink -f "$(which java)")")")" /opt/java \
 && rm -rf /var/lib/apt/lists/*

USER airflow
# One image for Airflow AND the Spark master/worker, so driver and executors
# always run the same Python + PySpark version.
RUN pip install --no-cache-dir \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.10.5/constraints-3.12.txt" \
    apache-airflow-providers-apache-spark requests

ENV JAVA_HOME=/opt/java \
    SPARK_HOME=/home/airflow/.local/lib/python3.12/site-packages/pyspark \
    PYTHONPATH=/opt/airflow
ENV PATH="${SPARK_HOME}/bin:${PATH}"
