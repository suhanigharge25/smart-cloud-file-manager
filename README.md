# ☁️ Smart Cloud File Manager

Smart Cloud File Manager is a cloud-based file management and analytics application built using AWS and Streamlit.

The application allows users to upload files directly from the dashboard, store them in Amazon S3, process file metadata using AWS Lambda, store metadata in DynamoDB, analyze the data using Amazon Athena, and visualize everything through an interactive Streamlit dashboard.

---

## 🚀 Features

### ☁️ Cloud File Upload

- Upload files directly from the dashboard
- Files are uploaded to Amazon S3
- Files are stored in the `raw/` folder
- Supports multiple file types
- Maximum upload size: 200 MB per file

### 📊 Interactive Dashboard

The dashboard provides:

- Total Files
- Documents
- Images
- Videos
- Old Files
- Total Storage
- Recent Files
- File Health
- Files by Category
- Files by Type
- Upload activity
- System information

### 🔍 Files & Analytics

The application provides:

- Complete file metadata table
- Filename search
- Category filtering
- File type filtering
- Status filtering
- Age filtering
- Size filtering
- File sorting
- File analytics

### ⚡ Automated File Processing

AWS Lambda processes uploaded files and:

- Detects file type
- Determines file category
- Calculates file size
- Calculates file age
- Detects old files
- Detects large files
- Creates metadata
- Stores metadata in DynamoDB
- Creates analytics JSON data
- Sends alerts when required

### 📧 File Alerts

Amazon SNS can be used to send notifications when files meet configured conditions such as:

- Old files
- Large files

### 🔄 Data Refresh

The dashboard includes a refresh mechanism that:

- Reloads metadata
- Recalculates KPIs
- Updates charts
- Refreshes recent files
- Displays the latest available information

---

# 🏗️ Architecture

```text
                    ┌─────────────────────┐
                    │   Streamlit Web UI  │
                    │   Cloud Dashboard   │
                    └──────────┬──────────┘
                               │
                               │ Upload
                               ▼
                    ┌─────────────────────┐
                    │      Amazon S3      │
                    │       raw/          │
                    └──────────┬──────────┘
                               │
                               │ S3 Event
                               ▼
                    ┌─────────────────────┐
                    │    AWS Lambda       │
                    │  File Processing     │
                    └──────┬───────┬──────┘
                           │       │
              Metadata     │       │ Alerts
                           │       ▼
                           │   ┌───────────┐
                           │   │    SNS    │
                           │   └───────────┘
                           │
                           ▼
                    ┌─────────────────────┐
                    │      DynamoDB       │
                    │   File Metadata     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    Amazon Athena    │
                    │     Analytics       │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Streamlit         │
                    │   Dashboard         │
                    └─────────────────────┘
