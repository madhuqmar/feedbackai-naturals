import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import os
from app_utils import get_last_scraping_date, load_data, run_scraper

import psutil



### APP HEADERS ###
st.set_page_config(layout="wide")

logo_path_1 = "images/naturals_logo.png"
logo_path_2 = "images/naturals_signature.png"

def get_memory_usage():
    process = psutil.Process(os.getpid())
    memory_usage = process.memory_info().rss / (1024 ** 2)  # Convert to MB
    return memory_usage

st.sidebar.write(f"Memory usage: {get_memory_usage():.2f} MB")


# Create three columns with ratios (4:1:1 works well for title + two logos)
col1, col2, col3 = st.columns([4, 1, 1])

# Add title to the left column
with col1:
    st.title("Customer FeedbackAI")
    st.write(
        """
        FeedbackAI is a data and AI-driven platform designed to provide actionable insights
        into customer sentiment, ratings, and reviews. By analyzing data extracted from the
        Google Places API, this tool enables businesses to improve customer satisfaction,
        track performance trends, and make informed decisions.
        """
    )

# Add the first logo to the second column
with col2:
    st.image(logo_path_1)

# Add the second logo to the third column
with col3:
    st.image(logo_path_2)

### MAIN APPLICATION ###
def main():

    # Load data from specified location
    file_path_1 = "data/naturals_chennai_locations_metadata.csv"
    columns_to_load_1 = ["Place ID", "Area", "Name", "City", "Rating", "Total Reviews"]  # Replace with actual column names you need
    ratings_df = load_data(file_path_1, columns=columns_to_load_1)
    ratings_df.rename(columns={"Place ID": "place_id"}, inplace=True)

    file_path_2 = "data/data/newest_gm_reviews_2025-01-16.csv"
    columns_to_load_2 = ["id_review", "caption", "review_date", "rating", "username", "place_id"]
    reviews_df = load_data(file_path_2, columns=columns_to_load_2)
    last_date = get_last_scraping_date(file_path_2)

    file_path_3 = "data/naturals_sentiments.csv"
    columns_to_load_3 = ["id_review", "sentiment"]
    sentiments_df = load_data(file_path_3, columns=columns_to_load_3)

    print("Ratings DF Columns:", ratings_df.columns)
    print("Reviews DF Columns:", reviews_df.columns)
    print("Sentiments DF Columns:", sentiments_df.columns)

    df = pd.merge(ratings_df, reviews_df, on="place_id", how="left")
    df = pd.merge(df, sentiments_df, on=["id_review"], how="left")

    df = df[df["caption"].notna()]
    df['full_location'] = df['Area'] + " " + df['Name']

    if not ratings_df.empty and not reviews_df.empty and not sentiments_df.empty:
        st.success("Data loaded successfully!")
    else:
        st.warning("The file is empty or has an unexpected format. Please check the file.")

    # Helper function to get the day suffix (st, nd, rd, th)
    def get_day_suffix(day):
        if 11 <= day <= 13:  # Special case for 11th, 12th, 13th
            return "th"
        last_digit = day % 10
        if last_digit == 1:
            return "st"
        elif last_digit == 2:
            return "nd"
        elif last_digit == 3:
            return "rd"
        else:
            return "th"

    # Helper function to get the day suffix (st, nd, rd, th)
    def get_day_suffix(day):
        if 11 <= day <= 13:  # Special case for 11th, 12th, 13th
            return "th"
        last_digit = day % 10
        if last_digit == 1:
            return "st"
        elif last_digit == 2:
            return "nd"
        elif last_digit == 3:
            return "rd"
        else:
            return "th"

    # Create two columns
    scrape1, scrape2 = st.columns([1, 9])

    # Add a button to trigger the scraper in the first column
    with scrape1:
        if st.button("Run Scraper Now", type="primary"):
            with st.spinner("Scraping in progress..."):
                run_scraper()

    # Display the last scraped date in the second column
    with scrape2:
        if last_date:
            day = last_date.day
            day_suffix = get_day_suffix(day)
            formatted_date = last_date.strftime(f"%B {day}{day_suffix} at %I %p").replace(" 0", " ")  # Remove leading 0
            st.write(f"Data was last scraped on **{formatted_date}**")
        else:
            st.write("Could not retrieve the last scraping date.")

    #### FILTERS ####
    st.sidebar.header("Filters")

    # Define dynamic time ranges
    today = datetime.today().date()
    yesterday = today - timedelta(days=1)
    this_week_start = today - timedelta(days=today.weekday())
    this_month_start = today.replace(day=1)
    last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
    last_month_end = this_month_start - timedelta(days=1)

    # Create dropdown options with labels
    timeline_options = {
        "All": None,
        f"Today, {today.strftime('%d %b')}": (today, today),
        f"Yesterday, {yesterday.strftime('%d %b')}": (yesterday, yesterday),
        f"This week, {this_week_start.strftime('%d %b')} to {today.strftime('%d %b')}": (this_week_start, today),
        f"This month, {this_month_start.strftime('%d %b')} to {today.strftime('%d %b')}": (this_month_start, today),
        f"Previous month, {last_month_start.strftime('%d %b')} to {last_month_end.strftime('%d %b')}": (
        last_month_start, last_month_end),
        "Custom Range": None,
    }

    # Add timeline filter to sidebar
    selected_timeline_label = st.sidebar.selectbox("Select Timeline", options=list(timeline_options.keys()))
    selected_timeline = timeline_options[selected_timeline_label]

    # Rating filter
    rating = st.sidebar.slider(
        "Select Rating",
        min_value=0,  # Minimum value for the slider
        max_value=5,  # Maximum value for the slider
        value=0,  # Default value
        step=1  # Step size for the slider
    )

    # Location filter with "All" option

    # City and City Area Filters
    city = st.sidebar.selectbox("Select City", options=["All"] + list(df['City'].dropna().unique()))

    city_area = st.sidebar.selectbox(
        "Select City Area",
        options=["All"] + list(df['Area'].dropna().unique()),
        key="city_area_selectbox"
    )
    selected_location = st.sidebar.selectbox("Select a Naturals Location",
                                             options=["All"] + list(df['full_location'].unique()))

    # APPLY FILTERS
    filtered_df = df.copy()
    # Ensure 'review_date' is in datetime64[ns]
    filtered_df['review_date'] = pd.to_datetime(filtered_df['review_date'], errors='coerce')

    # Convert 'selected_timeline' to datetime64[ns]
    if selected_timeline:
        selected_timeline = (
            pd.to_datetime(selected_timeline[0]),
            pd.to_datetime(selected_timeline[1])
        )

    # Filtering Logic
    # Apply timeline filter
    if selected_timeline_label == "All":
        filtered_df = df.copy()  # No date filter, show all data
    elif selected_timeline_label == "Custom Range":
        start_date = pd.to_datetime(st.sidebar.date_input("Start Date", value=today))
        end_date = pd.to_datetime(st.sidebar.date_input("End Date", value=today))
        if start_date > end_date:
            st.error("Start Date cannot be after End Date.")
        else:
            # Apply filter using datetime comparison
            filtered_df = filtered_df[
                (filtered_df['review_date'] >= start_date) &
                (filtered_df['review_date'] <= end_date)
                ]
    else:
        if selected_timeline:
            # Apply filter using datetime comparison
            filtered_df = filtered_df[
                (filtered_df['review_date'] >= selected_timeline[0]) &
                (filtered_df['review_date'] <= selected_timeline[1])
                ]

    if rating > 0:
        filtered_df = filtered_df[filtered_df['rating'] == rating]
    if selected_location != "All":
        filtered_df = filtered_df[filtered_df['full_location'] == selected_location]

    # #### Key Metrics ####
    st.header("Key Metrics")
    M1, M2 = st.columns(2)
    m1, m2, m3 = M1.columns(3)
    l1, l2 = M2.columns(2)

    # Total number of locations
    total_locations = len(filtered_df['place_id'].unique())
    m1.metric(label="Total Locations", value=total_locations)

    # Average Rating
    average_rating = filtered_df["rating"].mean() if not filtered_df.empty else 0
    m2.metric(label="Overall Average Rating", value=f"{average_rating:.2f}")

    # Total Reviews
    total_reviews = filtered_df['caption'].notna().sum()
    m3.metric(label="Total Number of Reviews", value=total_reviews)

    if not filtered_df.empty:
        # Ensure 'review_date' is in datetime format
        filtered_df['review_date'] = pd.to_datetime(filtered_df['review_date'], errors='coerce')

        # Group data by location and find start and end dates dynamically for each location
        dynamic_dates = filtered_df.groupby('full_location')['review_date'].agg(['min', 'max']).reset_index()
        dynamic_dates.columns = ['Location', 'Start_Date', 'End_Date']

        # Calculate average ratings for start and end dates dynamically
        def calculate_avg_rating(data, date_column, date_value):
            return data[data[date_column] == date_value]['rating'].mean()

        # Initialize lists to store the calculated values
        avg_rating_start = []
        avg_rating_end = []

        for _, row in dynamic_dates.iterrows():
            location_data = filtered_df[filtered_df['full_location'] == row['Location']]
            avg_rating_start.append(calculate_avg_rating(location_data, 'review_date', row['Start_Date']))
            avg_rating_end.append(calculate_avg_rating(location_data, 'review_date', row['End_Date']))

        # Add the calculated ratings to the dynamic_dates DataFrame
        dynamic_dates['Average_Rating_Start'] = avg_rating_start
        dynamic_dates['Average_Rating_End'] = avg_rating_end

        # Calculate delta
        dynamic_dates['Delta'] = dynamic_dates['Average_Rating_End'] - dynamic_dates['Average_Rating_Start']

        # Identify best-rated and least-rated locations based on end-date ratings
        best_location = dynamic_dates.loc[dynamic_dates['Average_Rating_End'].idxmax()]
        least_location = dynamic_dates.loc[dynamic_dates['Average_Rating_End'].idxmin()]

        # Ensure deltas are positive for best-rated and negative for least-rated
        best_location_delta = abs(best_location['Delta']) if not pd.isna(best_location['Delta']) else None
        least_location_delta = -abs(least_location['Delta']) if not pd.isna(least_location['Delta']) else None

        # Display metrics
        with l1:
            st.metric(
                label="Best Rated Location",
                value=f"{best_location['Location']}",
                delta=f"{best_location_delta:.2f} (Overall Rating: {best_location['Average_Rating_End']:.2f})"
                if best_location_delta is not None else None
            )

        with l2:
            st.metric(
                label="Least Rated Location",
                value=f"{least_location['Location']}",
                delta=f"{least_location_delta:.2f} (Overall Rating: {least_location['Average_Rating_End']:.2f})"
                if least_location_delta is not None else None,
            )

    else:
        st.warning("No data available for the selected timeline.")

    #### Charts ####
    # col1, col2, col3 = st.columns(3)
    #
    # # CHART 1: Salon Rating Distribution
    # category_counts = filtered_df['Rating'].value_counts().reset_index()
    # category_counts.columns = ['rating', 'count']
    # fig = px.pie(category_counts, names='rating', values='count', title='Salon Rating Distribution')
    # col1.plotly_chart(fig, theme="streamlit")
    #
    # # CHART 2: User Rating Distribution
    # category_counts = filtered_df['rating'].value_counts().reset_index()
    # category_counts.columns = ['rating', 'count']
    # fig = px.pie(category_counts, names='rating', values='count', title='User Rating Distribution')
    # col2.plotly_chart(fig, theme="streamlit")
    #
    # # CHART 3: Sentiment Distribution
    # valid_sentiments = ['Positive', 'Negative', 'Neutral', 'Mixed']
    # sentiment_counts = filtered_df[filtered_df['sentiment'].isin(valid_sentiments)][
    #     'sentiment'].value_counts().reset_index()
    # sentiment_counts.columns = ['sentiment', 'count']
    # fig = px.bar(sentiment_counts, x='sentiment', y='count', title='Sentiment Distribution', text='count')
    # col3.plotly_chart(fig, theme="streamlit")

    # Average Rating Trend Line Chart
    st.header("Average Rating Trend")

    if not filtered_df.empty:
        # Ensure 'review_date' is in datetime format
        filtered_df['review_date'] = pd.to_datetime(filtered_df['review_date'], errors='coerce')

        # Group by review date and calculate the average rating
        trend_data = filtered_df.groupby(filtered_df['review_date'].dt.date)['rating'].mean().reset_index()
        trend_data.columns = ['Date', 'Average Rating']

        # Create a line chart
        fig = px.line(
            trend_data,
            x='Date',
            y='Average Rating',
            title='Average Rating Trend Over Time',
            labels={'Date': 'Date', 'Average Rating': 'Average Rating'},
            markers=True
        )

        # Display the chart in Streamlit
        st.plotly_chart(fig, theme="streamlit", use_container_width=True)
    else:
        st.warning("No data available for the selected timeline to display the rating trend.")

    #### Filtered Table ####
    st.header("Customer Google Reviews")
    st.dataframe(filtered_df)
    # st.dataframe(filtered_df["caption"])



# Run the app
if __name__ == "__main__":
    main()
