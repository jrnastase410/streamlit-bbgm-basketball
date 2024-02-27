import boto3
import pandas as pd
import streamlit as st

# Create a session using your AWS credentials
session = boto3.Session(
    aws_access_key_id=st.secrets.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=st.secrets.AWS_SECRET_ACCESS_KEY,
    region_name='us-east-1'  # or any other region you want
)

# Create an S3 resource object using the session
s3 = session.resource('s3')

## Set bucket info
s3_file_path = 'df.csv'
bucket_name = st.secrets.S3_BUCKET

## Get object from S3
obj = s3.Object(bucket_name, s3_file_path)
df = pd.read_csv(obj.get()['Body'])

r_json = st.file_uploader("Upload a JSON file", type=["json"])

st.write(df.head())
