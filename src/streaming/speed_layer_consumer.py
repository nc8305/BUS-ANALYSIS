"""
SPEED LAYER - Kafka to PostgreSQL Consumer
Lambda Architecture - Real-time Processing

This consumer reads from Kafka and writes to PostgreSQL for real-time visualization.
"""

import json
import sys
import signal
from datetime import datetime
from confluent_kafka import Consumer, KafkaError, KafkaException
import psycopg2
from psycopg2 import pool
import time

# =============================================================================
# CONFIGURATION
# =============================================================================

KAFKA_CONFIG = {
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'speed-layer-consumer',
    'auto.offset.reset': 'latest',
    'enable.auto.commit': True,
    'auto.commit.interval.ms': 1000,
    'session.timeout.ms': 30000,
    'heartbeat.interval.ms': 10000,
}

POSTGRES_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'bus_analytics',
    'user': 'admin',
    'password': 'admin123',
}

TOPICS = ['bus-gps-tracking']

# =============================================================================
# DATABASE CONNECTION POOL
# =============================================================================

class DatabasePool:
    def __init__(self, config, min_conn=2, max_conn=10):
        self.pool = psycopg2.pool.ThreadedConnectionPool(
            min_conn, max_conn, **config
        )
    
    def get_connection(self):
        return self.pool.getconn()
    
    def return_connection(self, conn):
        self.pool.putconn(conn)
    
    def close_all(self):
        self.pool.closeall()

# =============================================================================
# SPEED LAYER PROCESSOR
# =============================================================================

class SpeedLayerProcessor:
    def __init__(self, kafka_config, postgres_config, topics):
        self.consumer = Consumer(kafka_config)
        self.db_pool = DatabasePool(postgres_config)
        self.topics = topics
        self.running = True
        self.processed_count = 0
        self.failed_count = 0
        self.batch = []
        self.batch_size = 100
        self.last_flush = time.time()
        self.flush_interval = 1.0  # seconds
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        print("\nReceived shutdown signal...")
        self.running = False
    
    def start(self):
        """Start consuming messages"""
        print(f"Speed Layer Consumer Starting...")
        print(f"Topics: {self.topics}")
        print(f"Kafka: {KAFKA_CONFIG['bootstrap.servers']}")
        print(f"PostgreSQL: {POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}")
        print("-" * 50)
        
        self.consumer.subscribe(self.topics)
        
        try:
            while self.running:
                msg = self.consumer.poll(timeout=0.1)
                
                if msg is None:
                    # Check if we need to flush batch
                    if self.batch and (time.time() - self.last_flush) > self.flush_interval:
                        self._flush_batch()
                    continue
                
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        raise KafkaException(msg.error())
                
                # Process message
                self._process_message(msg)
                
                # Flush if batch is full
                if len(self.batch) >= self.batch_size:
                    self._flush_batch()
        
        except Exception as e:
            print(f"Error: {e}")
        
        finally:
            self._shutdown()
    
    def _process_message(self, msg):
        """Process a single Kafka message"""
        try:
            value = json.loads(msg.value().decode('utf-8'))
            
            # Parse and validate
            record = {
                'vehicle_id': value.get('vehicle'),
                'latitude': value.get('lat'),
                'longitude': value.get('lng'),
                'speed': value.get('speed'),
                'driver_id': str(value.get('driver', '')),
                'door_up': value.get('door_up', False),
                'door_down': value.get('door_down', False),
                'event_time': value.get('datetime'),
            }
            
            # Validate required fields
            if not record['vehicle_id'] or record['latitude'] is None or record['longitude'] is None:
                self.failed_count += 1
                return
            
            self.batch.append(record)
            self.processed_count += 1
            
        except Exception as e:
            self.failed_count += 1
    
    def _flush_batch(self):
        """Flush batch to PostgreSQL"""
        if not self.batch:
            return
        
        conn = None
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            # Insert into stream table
            stream_sql = """
                INSERT INTO bus_tracking_stream 
                (vehicle_id, latitude, longitude, speed, driver_id, door_up, door_down, event_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            # Update realtime location table
            realtime_sql = """
                INSERT INTO bus_realtime_location 
                (vehicle_id, latitude, longitude, speed, driver_id, door_up, door_down, last_updated)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (vehicle_id) DO UPDATE SET
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    speed = EXCLUDED.speed,
                    driver_id = EXCLUDED.driver_id,
                    door_up = EXCLUDED.door_up,
                    door_down = EXCLUDED.door_down,
                    last_updated = NOW()
            """
            
            for record in self.batch:
                # Insert to stream
                cursor.execute(stream_sql, (
                    record['vehicle_id'],
                    record['latitude'],
                    record['longitude'],
                    record['speed'],
                    record['driver_id'],
                    record['door_up'],
                    record['door_down'],
                    record['event_time'],
                ))
                
                # Update realtime
                cursor.execute(realtime_sql, (
                    record['vehicle_id'],
                    record['latitude'],
                    record['longitude'],
                    record['speed'],
                    record['driver_id'],
                    record['door_up'],
                    record['door_down'],
                ))
            
            conn.commit()
            print(f"Flushed {len(self.batch)} records | Total: {self.processed_count} | Failed: {self.failed_count}")
            
            self.batch = []
            self.last_flush = time.time()
            
        except Exception as e:
            print(f"Database error: {e}")
            if conn:
                conn.rollback()
        
        finally:
            if conn:
                self.db_pool.return_connection(conn)
    
    def _shutdown(self):
        """Graceful shutdown"""
        print("\nShutting down...")
        
        # Flush remaining batch
        if self.batch:
            self._flush_batch()
        
        # Close consumer
        self.consumer.close()
        
        # Close database connections
        self.db_pool.close_all()
        
        print(f"\nFinal Statistics:")
        print(f"  Processed: {self.processed_count}")
        print(f"  Failed: {self.failed_count}")
        print("Speed Layer Consumer stopped.")

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    processor = SpeedLayerProcessor(
        kafka_config=KAFKA_CONFIG,
        postgres_config=POSTGRES_CONFIG,
        topics=TOPICS
    )
    processor.start()
