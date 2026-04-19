"""
BATCH LAYER - Spark Batch Processing
Lambda Architecture - Daily Analytics

This script runs Spark batch jobs to analyze historical data from HDFS
and generate aggregated reports in PostgreSQL.
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, count, avg, max, min, sum, hour, date_format,
    round as spark_round, when, lit
)
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType,
    BooleanType, TimestampType
)
import sys
from datetime import datetime, timedelta,date

# =============================================================================
# CONFIGURATION
# =============================================================================

POSTGRES_CONFIG = {
    'url': 'jdbc:postgresql://localhost:5432/bus_analytics',
    'user': 'admin',
    'password': 'admin123',
    'driver': 'org.postgresql.Driver',
}

HDFS_PATH = 'hdfs://namenode:9000/bus-data'

# =============================================================================
# SPARK SESSION
# =============================================================================

def create_spark_session():
    """Create Spark session with PostgreSQL support"""
    return SparkSession.builder \
        .appName("BusGPS-BatchLayer") \
        .config("spark.jars.packages", "org.postgresql:postgresql:42.6.0") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.shuffle.partitions", "10") \
        .getOrCreate()

# =============================================================================
# DATA SCHEMA
# =============================================================================

BUS_SCHEMA = StructType([
    StructField("datetime", StringType(), True),
    StructField("vehicle", StringType(), True),
    StructField("lng", DoubleType(), True),
    StructField("lat", DoubleType(), True),
    StructField("speed", DoubleType(), True),
    StructField("driver", StringType(), True),
    StructField("door_up", BooleanType(), True),
    StructField("door_down", BooleanType(), True),
])

# =============================================================================
# BATCH PROCESSING FUNCTIONS
# =============================================================================

def load_data(spark, source_path):
    """Load data from CSV or HDFS"""
    print(f"Loading data from: {source_path}")
    
    df = spark.read \
        .option("header", "true") \
        .option("inferSchema", "true") \
        .csv(source_path)
    
    # Convert datetime string to timestamp
    df = df.withColumn("event_time", col("datetime").cast(TimestampType()))
    df = df.withColumn("event_date", date_format("event_time", "yyyy-MM-dd"))
    df = df.withColumn("event_hour", hour("event_time"))
    
    print(f"Loaded {df.count()} records")
    return df


def generate_daily_vehicle_summary(df, report_date):
    """Generate daily summary per vehicle"""
    print(f"Generating daily vehicle summary for {report_date}...")
    
    summary = df.filter(col("event_date") == report_date) \
        .groupBy("vehicle") \
        .agg(
            avg("speed").alias("avg_speed"),
            max("speed").alias("max_speed"),
            count("*").alias("total_events"),
            sum(when(col("door_up") == True, 1).otherwise(0)).alias("total_passengers_up"),
            sum(when(col("door_down") == True, 1).otherwise(0)).alias("total_passengers_down"),
            count(when(col("speed") == 0, True)).alias("total_stops"),
        ) \
        .withColumn("report_date", lit(report_date).cast("date")) \
        .withColumn("total_distance_km", col("total_events") * 0.01) \
        .withColumn("operating_hours", col("total_events") / 3600.0)
    
    return summary.select(
        "report_date",
        col("vehicle").alias("vehicle_id"),
        spark_round("total_distance_km", 2).alias("total_distance_km"),
        spark_round("avg_speed", 2).alias("avg_speed"),
        spark_round("max_speed", 2).alias("max_speed"),
        "total_stops",
        "total_passengers_up",
        "total_passengers_down",
        spark_round("operating_hours", 2).alias("operating_hours"),
    )


def generate_hourly_traffic_analysis(df, report_date):
    """Generate hourly traffic analysis"""
    print(f"Generating hourly traffic analysis for {report_date}...")
    
    hourly = df.filter(col("event_date") == report_date) \
        .groupBy("event_hour") \
        .agg(
            count("vehicle").alias("total_buses_active"),
            avg("speed").alias("avg_speed"),
            sum(when(col("door_up") == True, 1).otherwise(0) +
                when(col("door_down") == True, 1).otherwise(0)).alias("total_door_events"),
        ) \
        .withColumn("report_date", lit(report_date).cast("date"))
    
    return hourly.select(
        "report_date",
        col("event_hour").alias("hour_of_day"),
        "total_buses_active",
        spark_round("avg_speed", 2).alias("avg_speed"),
        "total_door_events",
    )


def generate_driver_performance(df, report_date):
    """Generate driver performance metrics"""
    print(f"Generating driver performance for {report_date}...")
    
    driver_stats = df.filter(col("event_date") == report_date) \
        .filter(col("driver").isNotNull()) \
        .groupBy("driver") \
        .agg(
            count("*").alias("total_events"),
            avg("speed").alias("avg_speed"),
            max("speed").alias("max_speed"),
            count(when(col("speed") > 60, True)).alias("speeding_events"),
        ) \
        .withColumn("report_date", lit(report_date).cast("date")) \
        .withColumn("total_distance_km", col("total_events") * 0.01) \
        .withColumn("safety_score", 
            when(col("speeding_events") == 0, 100)
            .when(col("speeding_events") < 5, 90)
            .when(col("speeding_events") < 10, 80)
            .otherwise(70)
        )
    
    return driver_stats.select(
        "report_date",
        col("driver").alias("driver_id"),
        spark_round("total_distance_km", 2).alias("total_distance_km"),
        spark_round("avg_speed", 2).alias("avg_speed"),
        col("speeding_events").alias("total_hard_brakes"),
        spark_round("safety_score", 1).alias("safety_score"),
    )


def generate_geo_hotspots(df, report_date):
    """Generate geographic hotspots"""
    print(f"Generating geo hotspots for {report_date}...")
    
    # Round lat/lng to create geographic buckets
    hotspots = df.filter(col("event_date") == report_date) \
        .withColumn("lat_bucket", spark_round(col("lat"), 3)) \
        .withColumn("lng_bucket", spark_round(col("lng"), 3)) \
        .groupBy("lat_bucket", "lng_bucket") \
        .agg(
            count("*").alias("total_events"),
            avg("speed").alias("avg_speed"),
        ) \
        .filter(col("total_events") > 10) \
        .withColumn("report_date", lit(report_date).cast("date")) \
        .withColumn("peak_hour", lit(8))  # Placeholder
    
    return hotspots.select(
        "report_date",
        "lat_bucket",
        "lng_bucket",
        "total_events",
        spark_round("avg_speed", 2).alias("avg_speed"),
        "peak_hour",
    )


def save_to_postgres(df, table_name, mode="append"):
    """Save DataFrame to PostgreSQL"""
    print(f"Saving to PostgreSQL table: {table_name}")
    
    df.write \
        .format("jdbc") \
        .option("url", POSTGRES_CONFIG['url']) \
        .option("dbtable", table_name) \
        .option("user", POSTGRES_CONFIG['user']) \
        .option("password", POSTGRES_CONFIG['password']) \
        .option("driver", POSTGRES_CONFIG['driver']) \
        .mode(mode) \
        .save()
    
    print(f"Saved {df.count()} records to {table_name}")


# =============================================================================
# MAIN BATCH JOB
# =============================================================================

def run_batch_job(source_path, report_date=None):
    """Run complete batch processing job"""
    print("=" * 60)
    print("BATCH LAYER - Bus GPS Analytics")
    print("=" * 60)
    
    # Default to yesterday
    if report_date is None:
        report_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    print(f"Report Date: {report_date}")
    print(f"Source: {source_path}")
    print("-" * 60)
    
    # Create Spark session
    spark = create_spark_session()
    
    try:
        # Load data
        df = load_data(spark, source_path)
        df.cache()
        
        # Generate reports
        vehicle_summary = generate_daily_vehicle_summary(df, report_date)
        hourly_traffic = generate_hourly_traffic_analysis(df, report_date)
        driver_perf = generate_driver_performance(df, report_date)
        hotspots = generate_geo_hotspots(df, report_date)
        
        # Save to PostgreSQL
        save_to_postgres(vehicle_summary, "daily_vehicle_summary")
        save_to_postgres(hourly_traffic, "hourly_traffic_analysis")
        save_to_postgres(driver_perf, "driver_performance")
        save_to_postgres(hotspots, "geo_hotspots")
        
        print("-" * 60)
        print("BATCH JOB COMPLETED SUCCESSFULLY")
        print("=" * 60)
        
    except Exception as e:
        print(f"Batch job failed: {e}")
        raise
    
    finally:
        spark.stop()


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    # Default paths
    source_path = "data/raw_2025-04-01.csv"
    report_date = date.today()
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        source_path = sys.argv[1]
    
    if len(sys.argv) > 2:
        report_date = sys.argv[2]
    
    run_batch_job(source_path, report_date)
