# Spark Processing Jobs

This directory will contain Spark applications for batch processing bus data.

## Planned Components:

### 1. **Batch Processing**

- `daily_summary.py`: Daily aggregation of bus metrics
- `route_analysis.py`: Route optimization analysis
- `driver_performance.py`: Driver behavior analytics

### 2. **Stream Processing**

- `real_time_alerts.py`: Real-time anomaly detection
- `live_dashboard.py`: Live metrics calculation
- `geo_fencing.py`: Zone-based alerts

### 3. **Data Quality**

- `data_validation.py`: GPS coordinate validation
- `duplicate_detection.py`: Remove duplicate records
- `data_enrichment.py`: Add weather/traffic data

## Usage:

```bash
# Submit Spark job to cluster
docker exec spark-master spark-submit \
  --master spark://spark-master:7077 \
  /app/spark/daily_summary.py

# Or run locally
python src/spark/daily_summary.py
```

## Architecture:

```
Kafka → Spark Streaming → Processed Data → PostgreSQL
   ↓
HDFS ← Spark Batch Jobs ← Historical Analysis
```
