#!/bin/bash
# =============================================================================
# LAMBDA ARCHITECTURE DEMO SCRIPT
# Bus GPS Streaming Project
# =============================================================================

echo "=========================================="
echo "  BUS GPS LAMBDA ARCHITECTURE DEMO"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Start Docker services
echo -e "${YELLOW}Step 1: Starting Docker services...${NC}"
docker-compose up -d
sleep 10

# Step 2: Check services
echo -e "${YELLOW}Step 2: Checking services...${NC}"
docker-compose ps

# Step 3: Create Kafka topic
echo -e "${YELLOW}Step 3: Creating Kafka topic...${NC}"
docker exec kafka kafka-topics --create \
    --bootstrap-server localhost:9092 \
    --topic bus-gps-tracking \
    --partitions 3 \
    --replication-factor 1 \
    --if-not-exists

# Step 4: Instructions
echo ""
echo -e "${GREEN}=========================================="
echo "  SERVICES READY!"
echo "==========================================${NC}"
echo ""
echo "Access points:"
echo "  - Grafana Dashboard: http://localhost:3000 (admin/admin123)"
echo "  - Spark Master UI:   http://localhost:8082"
echo "  - Hadoop HDFS UI:    http://localhost:9870"
echo "  - pgAdmin:           http://localhost:5050 (admin@busgps.com/admin123)"
echo ""
echo "To run the pipeline:"
echo "  1. Producer (Terminal 1):"
echo "     python src/kafka/producer.py data/samples/sample_quick_test.csv 1000"
echo ""
echo "  2. Speed Layer Consumer (Terminal 2):"
echo "     python src/streaming/speed_layer_consumer.py"
echo ""
echo "  3. Batch Processing (Terminal 3):"
echo "     python src/spark/batch_layer.py data/raw_2025-04-01.csv 2025-04-01"
echo ""
echo "To stop all services:"
echo "  docker-compose down"
echo ""
