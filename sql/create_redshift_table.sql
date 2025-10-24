CREATE TABLE IF NOT EXISTS enriched_trip_data (
    trip_id VARCHAR(50) NOT NULL,
    taxi_id VARCHAR(50),
    pickup_datetime TIMESTAMP,
    dropoff_datetime TIMESTAMP,
    passenger_count INT DEFAULT 0,
    distance_km DOUBLE PRECISION,
    pickup_longitude DOUBLE PRECISION,
    pickup_latitude DOUBLE PRECISION,
    dropoff_longitude DOUBLE PRECISION,
    dropoff_latitude DOUBLE PRECISION,
    zone_name VARCHAR(255),
    payment_type VARCHAR(20),
    fare_amount DOUBLE PRECISION,
    extra_charges DOUBLE PRECISION DEFAULT 0,
    tip_amount DOUBLE PRECISION DEFAULT 0,
    tolls_amount DOUBLE PRECISION DEFAULT 0,
    total_amount DOUBLE PRECISION DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
DISTSTYLE AUTO
SORTKEY(pickup_datetime);
