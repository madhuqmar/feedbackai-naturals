import pandas as pd
import os
import boto3
import botocore
import io
import streamlit as st
import re
import numpy as np
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import torch

def load_csv_from_s3(bucket, key, columns=None):

    # Read secrets from Streamlit secrets
    # aws_access_key_id = st.secrets["AWS_ACCESS_KEY_ID"]
    # aws_secret_access_key = st.secrets["AWS_SECRET_ACCESS_KEY"]
    # region_name = st.secrets.get("AWS_DEFAULT_REGION", "us-east-1")

    # s3 = boto3.client(
    #     's3',
    #     aws_access_key_id=aws_access_key_id,
    #     aws_secret_access_key=aws_secret_access_key,
    #     region_name=region_name
    # )

    session = boto3.Session(profile_name="default", region_name="us-east-2")
    s3 = session.client("s3")

    response = s3.get_object(Bucket=bucket, Key=key)
    df = pd.read_csv(response['Body'], usecols=columns)
    return df



def get_last_scraping_date(data_path):
    """
    Retrieves the last scraping date from the 'retrieval_date' column in a CSV file.

    Parameters:
        data_path (str): Path to the CSV file containing the scraping data.

    Returns:
        datetime or None: The latest retrieval_date if found, otherwise None.
    """
    try:
        # Load the data
        df = pd.read_csv(data_path, parse_dates=['retrieval_date'])

        # Check if the retrieval_date column exists
        if 'retrieval_date' not in df.columns:
            print("The 'retrieval_date' column is not present in the dataset.")
            return None

        # Find the most recent retrieval date
        last_date = df['retrieval_date'].max()

        if pd.isnull(last_date):
            print("No valid dates found in the 'retrieval_date' column.")
            return None

        return last_date
    except FileNotFoundError:
        print(f"File not found: {data_path}")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def run_scraper():
    """
    Triggers the scraper script using the `os.system` command.
    """
    try:
        # Run the scraper script
        os.system("googlemaps-scraper/python scraper.py --N 100000")
        print("Scraping completed successfully!")
    except Exception as e:
        print(f"Error running the scraper: {e}")


def load_data(file_path, columns=None):
    """
    Load the CSV file into a DataFrame, selecting specific columns to optimize memory usage.

    Parameters:
        file_path (str): Path to the CSV file.
        columns (list, optional): List of column names to read. Defaults to None (reads all columns).

    Returns:
        pd.DataFrame: Loaded DataFrame or empty DataFrame on failure.
    """
    try:
        if columns:
            df = pd.read_csv(file_path, usecols=columns)
        else:
            df = pd.read_csv(file_path)  # Load all columns if none are specified
        return df
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame()


# Global variable to cache the sentiment analyzer
_sentiment_analyzer = None

def get_sentiment_analyzer():
    """
    Initialize and cache the sentiment analysis model.
    Uses a pre-trained BERT model optimized for sentiment analysis.
    """
    global _sentiment_analyzer
    
    if _sentiment_analyzer is None:
        try:
            # Use a robust sentiment analysis model
            model_name = "cardiffnlp/twitter-roberta-base-sentiment-latest"
            
            # Initialize the pipeline with error handling
            _sentiment_analyzer = pipeline(
                "sentiment-analysis",
                model=model_name,
                tokenizer=model_name,
                device=0 if torch.cuda.is_available() else -1,  # Use GPU if available
                top_k=None  # Return all scores
            )
            
        except Exception as e:
            st.warning(f"Could not load advanced AI model ({str(e)}). Falling back to basic model...")
            try:
                # Fallback to a smaller, more reliable model
                _sentiment_analyzer = pipeline(
                    "sentiment-analysis",
                    model="distilbert-base-uncased-finetuned-sst-2-english",
                    device=-1  # Use CPU
                )
            except Exception as fallback_error:
                st.error(f"Could not load any sentiment analysis model: {str(fallback_error)}")
                return None
    
    return _sentiment_analyzer


def analyze_sentiment_ai(text, rating):
    """
    AI-powered sentiment analysis using transformer models.
    
    Parameters:
        text (str): Review text content
        rating (int): Review rating (1-5)
    
    Returns:
        tuple: (sentiment_category, sentiment_score, sentiment_emoji)
    """
    # Handle missing or empty text
    if pd.isna(text) or text == "No Review Available" or str(text).strip() == "":
        # Base sentiment on rating only
        return _rating_to_sentiment(rating)
    
    # Get the AI sentiment analyzer
    analyzer = get_sentiment_analyzer()
    if analyzer is None:
        # Fallback to rating-based sentiment if AI model fails
        return _rating_to_sentiment(rating)
    
    try:
        # Clean and prepare text
        text = str(text).strip()
        if len(text) > 512:  # Truncate very long reviews for model efficiency
            text = text[:512]
        
        # Get AI sentiment prediction
        result = analyzer(text)
        
        # Handle different model output formats
        if isinstance(result, list) and len(result) > 0:
            prediction = result[0]
        else:
            prediction = result
        
        # Extract sentiment and confidence
        if isinstance(prediction, dict):
            ai_sentiment = prediction.get('label', '').upper()
            confidence = prediction.get('score', 0.5)
        elif isinstance(prediction, list) and len(prediction) > 0:
            # For models that return multiple predictions
            prediction = prediction[0]
            ai_sentiment = prediction.get('label', '').upper()
            confidence = prediction.get('score', 0.5)
        else:
            return _rating_to_sentiment(rating)
        
        # Convert AI prediction to our 5-category system
        sentiment_category, sentiment_score, sentiment_emoji = _convert_ai_sentiment(
            ai_sentiment, confidence, rating
        )
        
        return sentiment_category, sentiment_score, sentiment_emoji
        
    except Exception as e:
        st.warning(f"AI sentiment analysis failed for one review: {str(e)}")
        # Fallback to rating-based sentiment
        return _rating_to_sentiment(rating)


def _convert_ai_sentiment(ai_sentiment, confidence, rating):
    """
    Convert AI model predictions to our 5-category sentiment system.
    
    Parameters:
        ai_sentiment (str): AI model prediction label
        confidence (float): Confidence score from AI model
        rating (int): Star rating (1-5)
    
    Returns:
        tuple: (sentiment_category, sentiment_score, sentiment_emoji)
    """
    # Normalize AI sentiment labels
    ai_sentiment = ai_sentiment.upper()
    
    # Map common AI sentiment labels
    if ai_sentiment in ['POSITIVE', 'POS', 'LABEL_2']:
        base_positive = True
    elif ai_sentiment in ['NEGATIVE', 'NEG', 'LABEL_0']:
        base_positive = False
    elif ai_sentiment in ['NEUTRAL', 'NEU', 'LABEL_1']:
        # For neutral, use rating to determine direction
        base_positive = rating >= 3
        confidence = 0.5  # Lower confidence for neutral
    else:
        # Unknown label, fallback to rating
        return _rating_to_sentiment(rating)
    
    # Combine AI prediction with rating and confidence
    if base_positive:
        if confidence > 0.8 and rating >= 4:
            return "Very Positive", 5, "😍"
        elif confidence > 0.6 or rating >= 4:
            return "Positive", 4, "😊"
        else:
            return "Neutral", 3, "😐"
    else:
        if confidence > 0.8 and rating <= 2:
            return "Very Negative", 1, "😡"
        elif confidence > 0.6 or rating <= 2:
            return "Negative", 2, "😞"
        else:
            return "Neutral", 3, "😐"


def _rating_to_sentiment(rating):
    """
    Fallback function to determine sentiment based on rating only.
    
    Parameters:
        rating (int): Star rating (1-5)
    
    Returns:
        tuple: (sentiment_category, sentiment_score, sentiment_emoji)
    """
    if rating >= 5:
        return "Very Positive", 5, "😍"
    elif rating >= 4:
        return "Positive", 4, "😊"
    elif rating >= 3:
        return "Neutral", 3, "😐"
    elif rating >= 2:
        return "Negative", 2, "�"
    else:
        return "Very Negative", 1, "�"


def analyze_sentiment(text, rating):
    """
    Main sentiment analysis function that uses AI models.
    This replaces the old keyword-based approach.
    
    Parameters:
        text (str): Review text content
        rating (int): Review rating (1-5)
    
    Returns:
        tuple: (sentiment_category, sentiment_score, sentiment_emoji)
    """
    return analyze_sentiment_ai(text, rating)


def analyze_sentiments_batch(df, text_column='caption', rating_column='rating', batch_size=32):
    """
    Batch process sentiment analysis for better performance.
    
    Parameters:
        df (pd.DataFrame): DataFrame containing reviews
        text_column (str): Name of text column
        rating_column (str): Name of rating column
        batch_size (int): Number of reviews to process at once
    
    Returns:
        tuple: (sentiment_categories, sentiment_scores, sentiment_emojis)
    """
    analyzer = get_sentiment_analyzer()
    
    sentiment_categories = []
    sentiment_scores = []
    sentiment_emojis = []
    
    # Process in batches for efficiency
    total_rows = len(df)
    
    for i in range(0, total_rows, batch_size):
        batch_end = min(i + batch_size, total_rows)
        batch_df = df.iloc[i:batch_end]
        
        # Process batch
        for _, row in batch_df.iterrows():
            result = analyze_sentiment_ai(row[text_column], row[rating_column])
            sentiment_categories.append(result[0])
            sentiment_scores.append(result[1])
            sentiment_emojis.append(result[2])
    
    return sentiment_categories, sentiment_scores, sentiment_emojis


def calculate_overall_sentiment_score(df):
    """
    Calculate overall sentiment score for the dataset.
    
    Parameters:
        df (pd.DataFrame): DataFrame with sentiment_score column
    
    Returns:
        float: Overall sentiment score (1-5)
    """
    if 'sentiment_score' not in df.columns or df.empty:
        return 3.0  # Neutral default
    
    return round(df['sentiment_score'].mean(), 2)


def get_sentiment_distribution(df):
    """
    Get sentiment distribution for visualization.
    
    Parameters:
        df (pd.DataFrame): DataFrame with sentiment_category column
    
    Returns:
        pd.DataFrame: Sentiment distribution
    """
    if 'sentiment_category' not in df.columns or df.empty:
        return pd.DataFrame()
    
    sentiment_counts = df['sentiment_category'].value_counts().reset_index()
    sentiment_counts.columns = ['Sentiment', 'Count']
    
    # Ensure all categories are present
    all_sentiments = ['Very Positive', 'Positive', 'Neutral', 'Negative', 'Very Negative']
    for sentiment in all_sentiments:
        if sentiment not in sentiment_counts['Sentiment'].values:
            new_row = pd.DataFrame({'Sentiment': [sentiment], 'Count': [0]})
            sentiment_counts = pd.concat([sentiment_counts, new_row], ignore_index=True)
    
    # Sort by sentiment score order
    sentiment_order = {'Very Positive': 5, 'Positive': 4, 'Neutral': 3, 'Negative': 2, 'Very Negative': 1}
    sentiment_counts['Order'] = sentiment_counts['Sentiment'].map(sentiment_order)
    sentiment_counts = sentiment_counts.sort_values('Order', ascending=False).drop('Order', axis=1)
    
    return sentiment_counts

