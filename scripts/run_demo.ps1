# =============================================================================
# LAMBDA ARCHITECTURE DEMO SCRIPT (Windows PowerShell)
# Bus GPS Streaming Project
# =============================================================================

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  BUS GPS LAMBDA ARCHITECTURE DEMO" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Start Docker services
Write-Host "Step 1: Starting Docker services..." -ForegroundColor Yellow
docker-compose up -d
Start-Sleep -Seconds 15

# Step 2: Check services
Write-Host "Step 2: Checking services..." -ForegroundColor Yellow
docker-compose ps

# Step 3: Create Kafka topic
Write-Host "Step 3: Creating Kafka topic..." -ForegroundColor Yellow
docker exec kafka kafka-topics --create `
    --bootstrap-server localhost:9092 `
    --topic bus-gps-tracking `
    --partitions 3 `
    --replication-factor 1 `
    --if-not-exists

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "  SERVICES READY!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Access points:"
Write-Host "  - Grafana Dashboard: http://localhost:3000 (admin/admin123)" -ForegroundColor White
Write-Host "  - Spark Master UI:   http://localhost:8082" -ForegroundColor White
Write-Host "  - Hadoop HDFS UI:    http://localhost:9870" -ForegroundColor White
Write-Host "  - pgAdmin:           http://localhost:5050" -ForegroundColor White
Write-Host ""
Write-Host "To run the pipeline:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  1. Producer (Terminal 1):" -ForegroundColor White
Write-Host "     python src/kafka/producer.py data/samples/sample_quick_test.csv 1000" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. Speed Layer Consumer (Terminal 2):" -ForegroundColor White
Write-Host "     python src/streaming/speed_layer_consumer.py" -ForegroundColor Gray
Write-Host ""
Write-Host "  3. Batch Processing (Terminal 3):" -ForegroundColor White
Write-Host "     python src/spark/batch_layer.py data/raw_2025-04-01.csv 2025-04-01" -ForegroundColor Gray
Write-Host ""
Write-Host "To stop all services:" -ForegroundColor Yellow
Write-Host "  docker-compose down" -ForegroundColor Gray
Write-Host ""
