-- =============================================================================
-- LAMBDA ARCHITECTURE DATABASE SCHEMA
-- Bus GPS Streaming Project
-- =============================================================================

-- ===== SPEED LAYER TABLES (Real-time) =====

-- Real-time bus locations (latest position)
CREATE TABLE IF NOT EXISTS bus_realtime_location (
    vehicle_id VARCHAR(100) PRIMARY KEY,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    speed DOUBLE PRECISION,
    driver_id VARCHAR(100),
    door_up BOOLEAN DEFAULT FALSE,
    door_down BOOLEAN DEFAULT FALSE,
    last_updated TIMESTAMP DEFAULT NOW()
);

-- Real-time tracking history (recent 24h)
CREATE TABLE IF NOT EXISTS bus_tracking_stream (
    id SERIAL PRIMARY KEY,
    vehicle_id VARCHAR(100) NOT NULL,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    speed DOUBLE PRECISION,
    driver_id VARCHAR(100),
    door_up BOOLEAN DEFAULT FALSE,
    door_down BOOLEAN DEFAULT FALSE,
    event_time TIMESTAMP NOT NULL,
    ingested_at TIMESTAMP DEFAULT NOW()
);

-- Create index for fast queries
CREATE INDEX IF NOT EXISTS idx_stream_vehicle ON bus_tracking_stream(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_stream_time ON bus_tracking_stream(event_time DESC);

-- ===== BATCH LAYER TABLES (Analytics) =====

-- Daily vehicle summary
CREATE TABLE IF NOT EXISTS daily_vehicle_summary (
    id SERIAL PRIMARY KEY,
    report_date DATE NOT NULL,
    vehicle_id VARCHAR(100) NOT NULL,
    total_distance_km DOUBLE PRECISION,
    avg_speed DOUBLE PRECISION,
    max_speed DOUBLE PRECISION,
    total_stops INTEGER,
    total_passengers_up INTEGER,
    total_passengers_down INTEGER,
    operating_hours DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(report_date, vehicle_id)
);

-- Hourly traffic analysis
CREATE TABLE IF NOT EXISTS hourly_traffic_analysis (
    id SERIAL PRIMARY KEY,
    report_date DATE NOT NULL,
    hour_of_day INTEGER NOT NULL,
    total_buses_active INTEGER,
    avg_speed DOUBLE PRECISION,
    total_door_events INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(report_date, hour_of_day)
);

-- Route performance metrics
CREATE TABLE IF NOT EXISTS route_performance (
    id SERIAL PRIMARY KEY,
    report_date DATE NOT NULL,
    route_id VARCHAR(100),
    total_trips INTEGER,
    avg_trip_duration DOUBLE PRECISION,
    on_time_percentage DOUBLE PRECISION,
    total_passengers INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Driver performance metrics
CREATE TABLE IF NOT EXISTS driver_performance (
    id SERIAL PRIMARY KEY,
    report_date DATE NOT NULL,
    driver_id VARCHAR(100) NOT NULL,
    total_distance_km DOUBLE PRECISION,
    avg_speed DOUBLE PRECISION,
    total_hard_brakes INTEGER DEFAULT 0,
    safety_score DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(report_date, driver_id)
);

-- Geospatial hotspots (areas with high activity)
CREATE TABLE IF NOT EXISTS geo_hotspots (
    id SERIAL PRIMARY KEY,
    report_date DATE NOT NULL,
    lat_bucket DOUBLE PRECISION,
    lng_bucket DOUBLE PRECISION,
    total_events INTEGER,
    avg_speed DOUBLE PRECISION,
    peak_hour INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ===== SERVING LAYER VIEWS =====

-- View: Current fleet status
CREATE OR REPLACE VIEW v_fleet_status AS
SELECT 
    vehicle_id,
    latitude,
    longitude,
    speed,
    driver_id,
    door_up,
    door_down,
    last_updated,
    CASE 
        WHEN last_updated > NOW() - INTERVAL '5 minutes' THEN 'ACTIVE'
        WHEN last_updated > NOW() - INTERVAL '30 minutes' THEN 'IDLE'
        ELSE 'OFFLINE'
    END AS status
FROM bus_realtime_location;

-- View: Today's summary
CREATE OR REPLACE VIEW v_today_summary AS
SELECT 
    COUNT(DISTINCT vehicle_id) AS total_vehicles,
    ROUND(AVG(speed)::numeric, 2) AS avg_speed,
    MAX(speed) AS max_speed,
    COUNT(*) AS total_events
FROM bus_tracking_stream
WHERE event_time::date = CURRENT_DATE;

-- ===== FUNCTIONS =====

-- Function to update realtime location (upsert)
CREATE OR REPLACE FUNCTION upsert_bus_location(
    p_vehicle_id VARCHAR(100),
    p_latitude DOUBLE PRECISION,
    p_longitude DOUBLE PRECISION,
    p_speed DOUBLE PRECISION,
    p_driver_id VARCHAR(100),
    p_door_up BOOLEAN,
    p_door_down BOOLEAN
) RETURNS VOID AS $$
BEGIN
    INSERT INTO bus_realtime_location (vehicle_id, latitude, longitude, speed, driver_id, door_up, door_down, last_updated)
    VALUES (p_vehicle_id, p_latitude, p_longitude, p_speed, p_driver_id, p_door_up, p_door_down, NOW())
    ON CONFLICT (vehicle_id) 
    DO UPDATE SET 
        latitude = EXCLUDED.latitude,
        longitude = EXCLUDED.longitude,
        speed = EXCLUDED.speed,
        driver_id = EXCLUDED.driver_id,
        door_up = EXCLUDED.door_up,
        door_down = EXCLUDED.door_down,
        last_updated = NOW();
END;
$$ LANGUAGE plpgsql;

-- Function to cleanup old stream data (keep 24h)
CREATE OR REPLACE FUNCTION cleanup_old_stream_data() RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM bus_tracking_stream
    WHERE event_time < NOW() - INTERVAL '24 hours';
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO admin;
