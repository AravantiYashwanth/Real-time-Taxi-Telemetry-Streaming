import boto3
import csv
import json
import time
import os

# --- Configuration ---
KINESIS_STREAM_NAME = os.environ.get('KINESIS_STREAM_NAME', 'taxi-trip-stream')
AWS_REGION = os.environ.get('AWS_REGION', 'ap-south-1')
CSV_FILE_PATH = os.environ.get('CSV_FILE_PATH', 'taxi_trips_1000.csv')
BATCH_SIZE = int(os.environ.get('BATCH_SIZE', 100))  # Send records in batches

def send_data_in_batches(file_path, stream_name):
    """
    Reads CSV, converts numeric fields, and sends records to Kinesis in batches.
    """
    kinesis_client = boto3.client('kinesis', region_name=AWS_REGION)
    records_batch = []

    print(f"Sending data from '{file_path}' to Kinesis stream '{stream_name}'...")

    try:
        with open(file_path, 'r', encoding='utf-8') as csv_file:
            csv_reader = csv.DictReader(csv_file)

            for row in csv_reader:
                # Ensure pickup_datetime exists
                if 'pickup_datetime' not in row or not row['pickup_datetime'].strip():
                    print(f"Skipping trip_id {row.get('trip_id', 'N/A')}: missing pickup_datetime")
                    continue

                # Convert numeric fields
                for col in ['latitude', 'longitude', 'pickup_lat', 'pickup_long', 'drop_lat', 'drop_long', 'distance_km']:
                    row[col] = float(row.get(col, 0))

                # Optional fields
                row['passenger_count'] = int(row.get('passenger_count', 0))
                row['fare_amount'] = float(row.get('fare_amount', 0))
                row['extra_charges'] = float(row.get('extra_charges', row.get('extra', 0)))
                row['tip_amount'] = float(row.get('tip_amount', 0))
                row['tolls_amount'] = float(row.get('tolls_amount', 0))
                row['total_amount'] = float(row.get('total_amount', 0))
                row['zone_name'] = row.get('zone_name', '').strip('"')

                # Prepare Kinesis record
                record = {
                    'Data': json.dumps(row).encode('utf-8'),
                    'PartitionKey': row['trip_id']
                }
                records_batch.append(record)

                # Send batch if full
                if len(records_batch) >= BATCH_SIZE:
                    _send_batch(kinesis_client, stream_name, records_batch)
                    records_batch = []
                    time.sleep(0.1)  # optional throttle

            # Send remaining records
            if records_batch:
                _send_batch(kinesis_client, stream_name, records_batch)

    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
    except Exception as e:
        print(f"Unexpected error: {e}")

    print("Finished sending all data.")

def _send_batch(client, stream_name, batch):
    """Send a batch of records to Kinesis and handle errors."""
    try:
        response = client.put_records(StreamName=stream_name, Records=batch)
        print(f"Sent batch of {len(batch)} records.")
        if response.get('FailedRecordCount', 0) > 0:
            print(f"WARNING: {response['FailedRecordCount']} records failed.")
    except Exception as e:
        print(f"Error sending batch: {e}")


if __name__ == "__main__":
    send_data_in_batches(CSV_FILE_PATH, KINESIS_STREAM_NAME)
