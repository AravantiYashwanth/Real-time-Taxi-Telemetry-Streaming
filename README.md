# 🚕 Real-time Taxi Telemetry Streaming

### 📘 Overview
**Real-time Taxi Telemetry Streaming** is an **end-to-end, serverless streaming data pipeline** built on **AWS**.  
It is designed to ingest, process, enrich, and analyze high-velocity taxi trip data in real time.

The pipeline captures simulated taxi GPS and trip events, enriches them with geographical context, and then **fans out** the processed data to multiple destinations:

1. 🟢 **Low-Latency Operational Store** — Powers a **DynamoDB** table for real-time micro-billing lookups (e.g., “fetch fare for Trip ID `T0001`”).  
2. 🔵 **Analytical Data Warehouse** — Feeds **Amazon Redshift** for BI dashboards in **QuickSight** (analyzing trends, zones, and revenue).  
3. 🟣 **Raw Data Lake** — Archives unaltered streaming events in **Amazon S3** for long-term storage, auditing, and reprocessing.

---

## 🏗️ Solution Architecture

Taxi Fleet (producer.py)  
│   
▼   
Amazon Kinesis Data Stream (taxi-trip-stream)    
│    
├──▶ Kinesis Data Firehose (taxi-raw-firehose)    
│ │    
│ └─▶ Amazon S3 (Raw Data Lake)    
│ └─▶ (Lifecycle Policy → S3 Glacier)    
│    
▼   
AWS Lambda (EnrichTripDataFunction)   
│    
│ └─▶ Amazon Location Service (Reverse Geocoding)   
│    
▼    
Amazon SQS (taxi-trip-processing-queue) ◀── (DLQ for failed messages)    
│    
▼    
AWS Lambda (ProcessAndStoreFunction)    
│    
│ └─▶ Fare Calculation Logic    
│      
├──▶ Amazon DynamoDB (TaxiBilling Table)      
│ └─▶ Real-time micro-billing lookups         
│        
└──▶ Kinesis Data Firehose (Lambda-Redshift-Firehouse)      
▼      
Amazon Redshift (Data Warehouse)      
▼    
Amazon QuickSight (BI Dashboards)



---

## ⚙️ Technologies Used

| Category | Technologies |
|-----------|--------------|
| **Data Ingestion** | Amazon Kinesis Data Streams |
| **Streaming & Buffering** | Kinesis Data Firehose, Amazon SQS |
| **Data Processing** | AWS Lambda (Python 3.12) |
| **Data Enrichment** | Amazon Location Service |
| **Operational Storage (NoSQL)** | Amazon DynamoDB |
| **Analytical Storage (DWH)** | Amazon Redshift Serverless |
| **Data Lake Storage** | Amazon S3 (Standard + Glacier) |
| **Data Visualization (BI)** | Amazon QuickSight |
| **Simulation & Testing** | Python, Boto3 |

---

## 🔄 Pipeline Breakdown

### 🔹 Step 1: Data Ingestion (Kinesis Data Stream)
A **Python producer script (`producer.py`)** simulates a fleet of taxis, generating JSON trip events in real time.  
These are streamed to **Kinesis Data Stream (`taxi-trip-stream`)**, acting as the durable ingestion point for all telemetry data.

---

### 🔹 Step 2: Raw Data Archiving (Firehose → S3)
A **Kinesis Data Firehose** (`taxi-raw-firehose`) continuously reads from the Kinesis stream, batching and compressing records before archiving them in **Amazon S3**.  
An **S3 Lifecycle Policy** automatically transitions old data to **Glacier**, ensuring low-cost archival.

---

### 🔹 Step 3: Real-Time Enrichment (Lambda + Location Service)
The **EnrichTripDataFunction** Lambda is triggered by Kinesis.  
For each event:
1. Parses and validates JSON input.  
2. Calls **Amazon Location Service** for reverse geocoding — converting GPS coordinates into a human-readable pickup zone (e.g., *“Nampally, Hyderabad”*).  
3. Publishes the enriched event to an **SQS queue (`taxi-trip-processing-queue`)**.

---

### 🔹 Step 4: Decoupling with SQS
Using **Amazon SQS** introduces a buffer between Lambdas, preventing message loss during downstream failures.  
A **Dead-Letter Queue (DLQ)** captures problematic messages for debugging without halting the main pipeline.

---

### 🔹 Step 5: Processing & Fan-Out (Lambda)
The **ProcessAndStoreFunction** Lambda is triggered by the SQS queue.  
It performs:
- **Fare calculation logic** based on distance, extra charges, and trip zone.  
- **Fan-out distribution** — sending final enriched trip data to both:
  - **DynamoDB (TaxiBilling Table)** for operational analytics.  
  - **Kinesis Firehose (Lambda-Redshift-Firehouse)** for warehousing in Redshift.

---

### 🔹 Step 6: Operational Store (DynamoDB)
Stores finalized trip data with **millisecond latency** lookups.  
Each record is partitioned by `trip_id` and sorted by `pickup_datetime`, enabling applications to instantly retrieve fare summaries or payment details.

---

### 🔹 Step 7: Analytical Warehouse (Redshift)
The same Lambda streams enriched trip data via Firehose to **Amazon Redshift**.  
This serves as a **schema-on-write** data warehouse, enabling advanced analytics and SQL-based reporting.

---

### 🔹 Step 8: Visualization (QuickSight)
**Amazon QuickSight** connects directly to Redshift to create dashboards showing:
- Total revenue by pickup zone  
- Average fare vs. distance  
- Cash vs. Card payment breakdown  
- Heatmaps of popular pickup locations  
- Hourly ride distribution across the city  

---

## 🧠 Key Features

✅ **Fully Serverless Architecture** — No servers to manage; scales automatically.  
✅ **Dual Data Paths** — Low-latency operational and high-throughput analytical.  
✅ **Real-Time Enrichment** — Converts GPS data into contextual location data.  
✅ **Resilient Design** — SQS + DLQ ensure fault tolerance and zero data loss.  
✅ **Multi-Destination Delivery** — Single stream drives DynamoDB, Redshift, and S3.  
✅ **Lifecycle Management** — S3 Glacier reduces long-term storage costs.  

---

## ⚔️ Challenges & Solutions

| Challenge | Solution |
|------------|-----------|
| **Data Loss Risk (Lambda → Lambda)** | Introduced **Amazon SQS** as a durable buffer between enrichment and processing. |
| **Poison Pill Messages** | Added a **Dead-Letter Queue (DLQ)** to automatically isolate bad records. |
| **Conflicting Data Needs (Latency vs. Throughput)** | Used **Fan-Out Pattern** — DynamoDB for fast key-value reads, Redshift for deep analytics. |
| **Dynamic Scaling During Spikes** | Leveraged **Kinesis auto-scaling** and **Lambda concurrency controls** for elasticity. |

---

## 📂 Project Structure
Real-time-Taxi-Streaming/    
│    
├── producer.py # Simulates taxi fleet, streams data to Kinesis    
│    
├── lambda_functions/    
│ ├── enrich_trip_data.py # Lambda 1: Kinesis → Enrichment (Location) → SQS    
│ └── process_and_store.py # Lambda 2: SQS → Fare Calc → DynamoDB & Firehose    
│    
├── sql/    
│ └── create_redshift_table.sql # DDL for Redshift table (enriched_trip_data)    
│    
└── README.md    

---

## 📊 Sample Redshift Query

```sql
-- Top 10 Most Profitable Pickup Zones
SELECT
  zone_name,
  COUNT(trip_id) AS total_trips,
  SUM(total_amount) AS total_revenue,
  AVG(fare_amount) AS average_fare
FROM enriched_trip_data
WHERE zone_name != 'Unknown'
GROUP BY zone_name
ORDER BY total_revenue DESC
LIMIT 10;
```

## 💡 Learnings

- Building **event-driven, serverless streaming pipelines** on AWS.  
- Leveraging **Kinesis Data Streams** for high-throughput ingestion.  
- Applying the **Fan-Out Pattern** to serve both operational and analytical systems.  
- Implementing **decoupled microservice design** using **SQS** and **DLQs**.  
- Performing **real-time enrichment** via **AWS Lambda + Amazon Location Service**.  
- Understanding differences between **Schema-on-Write (Redshift)** and **Schema-on-Read (S3)**.  

---

## 🧰 Tools & Services

AWS Kinesis Data Streams • AWS Kinesis Data Firehose • AWS Lambda • Amazon SQS •  
Amazon DynamoDB • Amazon Redshift Serverless • Amazon S3 • Amazon QuickSight •  
Amazon Location Service • Python (Boto3)

---

## 🏁 Conclusion

This project demonstrates how to build a **real-time, resilient, and scalable data streaming system** using **AWS serverless technologies**.  
It transforms raw taxi telemetry into **two distinct, high-value data products**:

- ⚡ **An operational DynamoDB store** for instant fare retrievals.  
- 📊 **An analytical Redshift warehouse** for trend and performance insights.  

Together, they enable **end-to-end visibility** — from live operations to strategic decision-making — with **zero data loss** and **minimal latency**.  

---

## 👨‍💻 Author

**A. Yashwanth**  
Aspiring Data Engineer | Python & AWS Enthusiast  
📧 [www.linkedin.com/in/yashwantharavanti](https://www.linkedin.com/in/yashwantharavanti)
