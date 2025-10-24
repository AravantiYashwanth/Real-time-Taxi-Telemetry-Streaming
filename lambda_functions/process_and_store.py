import json
import os
import boto3
from decimal import Decimal

# Initialize AWS clients
DYNAMODB = boto3.resource('dynamodb')
FIREHOSE_CLIENT = boto3.client('firehose')

# Get environment variables
DYNAMODB_TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
FIREHOSE_STREAM_NAME = os.environ.get('FIREHOSE_STREAM_NAME')
# REAL-TIME TAXI TELEMETRY STREAMING| YASHWANTH ARAVANTI  <- This line was not valid Python, so I've commented it out.

def calculate_fare(distance_km, zone_name):
    """
    Calculates the fare based on distance and applies a surcharge for specific zones.
    """
    try:
        distance = float(distance_km)
    except (ValueError, TypeError):
        distance = 0.0
    
    base_fare = 50.0
    rate_per_km = 18.5
    fare = base_fare + (distance * rate_per_km)
    
    # Apply a surcharge if the trip is associated with an airport
    if zone_name and 'Airport' in zone_name:
        fare += 100.0
        
    return round(fare, 2)

def floats_to_decimal(data_dict):
    """
    Recursively converts all float values in a dictionary to the Decimal type,
    which is required for DynamoDB.
    """
    for key, value in data_dict.items():
        if isinstance(value, float):
            data_dict[key] = Decimal(str(value))
        elif isinstance(value, dict):
            floats_to_decimal(value)
    return data_dict

def validate_trip_data(trip_data):
    """
    Validate that all required fields are present and in correct format.
    """
    required_fields = ['trip_id', 'taxi_id', 'pickup_datetime', 'pickup_lat', 
                       'pickup_long', 'drop_lat', 'drop_long', 'distance_km']
    
    missing_fields = [field for field in required_fields if field not in trip_data or 
                      trip_data[field] is None]
    
    if missing_fields:
        return False, f"Missing required fields: {missing_fields}"
        
    # Validate numeric fields
    numeric_fields = ['pickup_lat', 'pickup_long', 'drop_lat', 'drop_long', 'distance_km']
    for field in numeric_fields:
        try:
            float(trip_data[field])
        except (ValueError, TypeError):
            return False, f"Invalid numeric value for {field}: {trip_data[field]}"
            
    return True, "Valid"

def lambda_handler(event, context):
    """
    This function is triggered by an SQS queue. For each message, it calculates
    the trip fare, stores the result in DynamoDB, and sends the data to Kinesis Firehose.
    """
    if not DYNAMODB_TABLE_NAME or not FIREHOSE_STREAM_NAME:
        # Fixed the broken multi-line string below
        error_msg = ("Error: Environment variables DYNAMODB_TABLE_NAME and "
                     "FIREHOSE_STREAM_NAME must be set.")
        print(error_msg)
        return {
            # REAL-TIME TAXI TELEMETRY STREAMING| YASHWANTH ARAVANTI <- This line was not valid Python, so I've commented it out.
            'statusCode': 500,
            'body': json.dumps(error_msg)
        }

    processed_count = 0
    failed_count = 0
    table = DYNAMODB.Table(DYNAMODB_TABLE_NAME)
    
    print(f"Processing {len(event['Records'])} records from SQS")
    
    # SQS triggers send a batch of records in the 'Records' key
    for record in event['Records']:
        trip_id = 'Unknown'
        try:
            # The actual message from the previous Lambda is a JSON string in the 'body'
            message_body = record['body']
            trip_data = json.loads(message_body)
            trip_id = trip_data.get('trip_id', 'N/A')
            
            print(f"🔧 Processing Trip ID: {trip_id}")
            
            # 1. Validate the incoming data
            is_valid, validation_msg = validate_trip_data(trip_data)
            if not is_valid:
                print(f"❌ Validation failed for Trip ID {trip_id}: {validation_msg}")
                failed_count += 1
                continue
                
            # 2. Calculate the fare
            fare = calculate_fare(trip_data.get('distance_km'), trip_data.get('zone_name'))
            trip_data['fare_amount'] = fare
            print(f"💰 Calculated Fare: {fare} for distance: {trip_data.get('distance_km')}km")
            
            # 3. Set default values for optional fields
            trip_data.setdefault('passenger_count', 0)
            trip_data.setdefault('extra_charges', 0.0)
            trip_data.setdefault('tip_amount', 0.0)
            trip_data.setdefault('tolls_amount', 0.0)
            trip_data.setdefault('payment_type', 'CASH')
            
            # Calculate total amount (fare + extra charges + tip + tolls)
            total_amount = (fare + float(trip_data.get('extra_charges', 0.0)) + 
                            float(trip_data.get('tip_amount', 0.0)) + float(trip_data.get('tolls_amount', 0.0)))
            trip_data['total_amount'] = round(total_amount, 2)
            
            # 4. Prepare DynamoDB item with explicit field mapping
            dynamodb_item = {
                'trip_id': trip_data['trip_id'],
                'taxi_id': trip_data.get('taxi_id', ''),
                'pickup_datetime': trip_data.get('pickup_datetime', ''),
                'pickup_lat': Decimal(str(trip_data.get('pickup_lat', 0.0))),
                'pickup_long': Decimal(str(trip_data.get('pickup_long', 0.0))),
                'drop_lat': Decimal(str(trip_data.get('drop_lat', 0.0))),
                'drop_long': Decimal(str(trip_data.get('drop_long', 0.0))),
                'distance_km': Decimal(str(trip_data.get('distance_km', 0.0))),
                'zone_name': trip_data.get('zone_name', ''),
                'fare_amount': Decimal(str(fare)),
                'passenger_count': int(trip_data.get('passenger_count', 0)),
                'extra_charges': Decimal(str(trip_data.get('extra_charges', 0.0))),
                'tip_amount': Decimal(str(trip_data.get('tip_amount', 0.0))),
                'tolls_amount': Decimal(str(trip_data.get('tolls_amount', 0.0))),
                'total_amount': Decimal(str(trip_data.get('total_amount', 0.0))),
                'payment_type': trip_data.get('payment_type', 'CASH')
                # REAL-TIME TAXI TELEMETRY STREAMING| YASHWANTH ARAVANTI <- This line was not valid Python, so I've commented it out.
            }
            
            # 5. Write the complete record to DynamoDB
            table.put_item(Item=dynamodb_item)
            print(f"✅ Successfully wrote to DynamoDB table: {DYNAMODB_TABLE_NAME}")
            
            # 6. Prepare data for Firehose (ensure all fields for Redshift are present)
            firehose_data = trip_data.copy()
            
            # Add fields expected by Redshift schema
            firehose_data.setdefault('dropoff_datetime', None)
            firehose_data.setdefault('pickup_latitude', trip_data.get('pickup_lat'))
            firehose_data.setdefault('pickup_longitude', trip_data.get('pickup_long'))
            firehose_data.setdefault('dropoff_latitude', trip_data.get('drop_lat'))
            firehose_data.setdefault('dropoff_longitude', trip_data.get('drop_long'))
            
            # 7. Send the complete record to Kinesis Firehose for analytics/S3 storage
            # Firehose expects a newline character for batching into files
            firehose_payload = (json.dumps(firehose_data) + '\n').encode('utf-8')
            
            FIREHOSE_CLIENT.put_record(
                DeliveryStreamName=FIREHOSE_STREAM_NAME,
                Record={'Data': firehose_payload}
            )
            print(f"📤 Successfully sent to Firehose stream: {FIREHOSE_STREAM_NAME}")
            
            processed_count += 1
            print(f"✅ Completed processing Trip ID: {trip_id}")
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error for record {trip_id}: {e}")
            failed_count += 1
        except Exception as e:
            print(f"❌ Error processing record {trip_id}: {e}")
            failed_count += 1
            
    # Final summary
    print(f"\n📊 Processing Summary:")
    print(f"✅ Successfully processed: {processed_count} records")
    print(f"❌ Failed: {failed_count} records")
    print(f"📥 Total received from SQS: {len(event['Records'])} records")
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': f'Successfully processed {processed_count} records from SQS',
            'processed': processed_count,
            'failed': failed_count,
            'total': len(event['Records'])
        })
    }
