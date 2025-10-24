import base64
import json
import os
import boto3

# Initialize AWS clients outside the handler for better performance
# Boto3 will reuse these clients across multiple invocations
LOCATION_CLIENT = boto3.client('location')
SQS_CLIENT = boto3.client('sqs')

# Get environment variables
# These must be set in your Lambda function's configuration
PLACE_INDEX_NAME = os.environ.get('PLACE_INDEX_NAME')
SQS_QUEUE_URL = os.environ.get('SQS_QUEUE_URL')

def lambda_handler(event, context):
    """
    This function is triggered by a Kinesis Data Stream.
    It enriches the trip data with a zone name from AWS Location Service
    and then sends the enriched data to an SQS queue.
    """
    if not PLACE_INDEX_NAME or not SQS_QUEUE_URL:
        print("Error: Environment variables PLACE_INDEX_NAME and SQS_QUEUE_URL must be set.")
        return {'statusCode': 500}

    # Kinesis events contain a list of records
    for record in event['Records']:
        try:
            # 1. Decode the Kinesis data record
            # The data is Base64 encoded, so we must decode it first
            payload_data = base64.b64decode(record['kinesis']['data']).decode('utf-8')
            trip_data = json.loads(payload_data)

            print(f"Processing Trip ID: {trip_data.get('trip_id', 'N/A')}")
            
            # 2. Call AWS Location Service for zone mapping (Reverse Geocoding)
            longitude = float(trip_data['longitude'])
            latitude = float(trip_data['latitude'])

            response = LOCATION_CLIENT.search_place_index_for_position(
                IndexName=PLACE_INDEX_NAME,
                Position=[longitude, latitude],
                MaxResults=1
            )

            # 3. Enrich the data with the zone name
            if response.get('Results'):
                # The 'Label' contains the full address/zone info
                zone_name = response['Results'][0]['Place']['Label']
                trip_data['zone_name'] = zone_name
                print(f"Found Zone: {zone_name}")
            else:
                trip_data['zone_name'] = 'Unknown'
                # The following line was present in your original code but is not valid Python.
                # I have commented it out to make the script functional.
                # REAL-TIME TAXI TELEMETRY STREAMING| YASHWANTH ARAVANTI
                print("Could not find a zone for the given coordinates.")
                
            # 4. Send the enriched data to the SQS queue
            # The message body must be a string
            message_body = json.dumps(trip_data)

            SQS_CLIENT.send_message(
                QueueUrl=SQS_QUEUE_URL,
                MessageBody=message_body
            )
            print(f"Successfully sent message to SQS for Trip ID: {trip_data.get('trip_id', 'N/A')}")
            
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from Kinesis record: {e}")
            continue  # Move to the next record
        except Exception as e:
            print(f"An error occurred processing a record: {e}")
            continue  # Move to the next record

    return {
        'statusCode': 200,
        'body': json.dumps(f"Successfully processed {len(event['Records'])} records and sent to SQS.")
    }
