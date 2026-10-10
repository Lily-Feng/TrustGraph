from pyspark.sql import SparkSession


def session(name):
    return SparkSession.builder.appName(name).getOrCreate()
