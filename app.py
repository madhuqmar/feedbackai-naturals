import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import os
from app_utils import get_last_scraping_date, load_data, run_scraper, load_csv_from_s3, analyze_sentiment, calculate_overall_sentiment_score, get_sentiment_distribution, analyze_sentiments_batch
from utils.st_paywall.aggregate_auth import add_auth
import psutil


### APP HEADERS ###
st.set_page_config(layout="wide")

logo_path_1 = "images/gt_logo.png"

def get_memory_usage():
    process = psutil.Process(os.getpid())
    memory_usage = process.memory_info().rss / (1024 ** 2)  # Convert to MB
    return memory_usage

def show_access_gate():
    """Show the access gate with Stripe payment or secret password options."""
    st.markdown("""
        <div style='text-align: center; padding: 2rem 0;'>
            <h1 style='color: #8A2BE2; margin-bottom: 0.5rem;'>Welcome to FeedbackAI!</h1>
            <p style='font-size: 1.2rem; color: #666; margin-bottom: 2rem;'>
                A real-time data and AI-driven platform for customer sentiment analysis from Google Reviews
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    
    # Center the tabs
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        # Create tabs for different access methods
        tab1, tab2 = st.tabs(["🔐 Subscribe to Access", "👤 Subscriber Login"])
        
        with tab1:
            st.markdown("""
                <div style='text-align: center; padding: 1rem;'>
                    <h3>Get Full Access to FeedbackAI</h3>
                    <p>Subscribe to unlock powerful analytics and insights for your business</p>
                </div>
            """, unsafe_allow_html=True)
            
            # Import redirect_button directly to show subscription button
            from utils.st_paywall.stripe_auth import redirect_button
            
            # Center the subscription button with better proportions
            subcol1, subcol2, subcol3 = st.columns([2, 1, 2])
            with subcol2:
                redirect_button(
                    text="Subscribe Now",
                    customer_email="",  # Empty email for new users
                    color="#34D57A",
                    payment_provider=st.secrets.get("payment_provider", "stripe"),
                    use_sidebar=False
                )
        
        with tab2:
            st.markdown("""
                <div style='text-align: center; padding: 1rem;'>
                    <h3>Subscriber Login</h3>
                    <p>Already subscribed? Enter your email to access the app</p>
                </div>
            """, unsafe_allow_html=True)
            
            # Center the login form
            subcol1, subcol2, subcol3 = st.columns([1, 2, 1])
            with subcol2:
                # Email input for login
                user_email = st.text_input("Email Address", key="subscriber_email", placeholder="Enter the email used for subscription")
                
                if st.button("Login & Verify Subscription", type="primary", use_container_width=True):
                    if user_email:
                        with st.spinner("Searching Stripe customers and verifying subscription..."):
                            try:
                                from utils.st_paywall.stripe_auth import is_active_subscriber, get_customer_subscription_info
                                
                                # Get detailed subscription info
                                sub_info = get_customer_subscription_info(user_email)
                                
                                if sub_info["status"] == "no_customer":
                                    st.error("❌ No customer found with this email address in Stripe.")
                                    st.info("💡 Please use the exact email address you used for payment, or subscribe first.")
                                    
                                elif sub_info["status"] == "error":
                                    st.error(f"❌ Error checking subscription: {sub_info['message']}")
                                    
                                elif sub_info["status"] == "found":
                                    if sub_info["has_active_subscription"]:
                                        # Set up session for logged in subscriber
                                        st.session_state.user_email = user_email
                                        st.session_state.user_subscribed = True
                                        st.session_state.access_granted = True
                                        st.session_state.subscription_info = sub_info
                                        
                                        st.success("✅ Active subscription found! Loading app...")
                                        
                                        # Show subscription details
                                        for customer in sub_info["customers"]:
                                            if customer["active_subscriptions"] > 0:
                                                st.info(f"👤 Customer: {customer['name']} | Active Subscriptions: {customer['active_subscriptions']}")
                                        
                                        st.rerun()
                                    else:
                                        st.error("❌ Customer found, but no active subscriptions.")
                                        st.info("💡 Your subscription may have expired or been cancelled. Please renew your subscription.")
                                        
                                        # Show customer details for debugging
                                        with st.expander("🔍 Customer Details"):
                                            for customer in sub_info["customers"]:
                                                st.write(f"**Customer:** {customer['name']}")
                                                st.write(f"**Email:** {customer['email']}")
                                                st.write(f"**Total Subscriptions:** {customer['all_subscriptions']}")
                                                st.write(f"**Active Subscriptions:** {customer['active_subscriptions']}")
                                        
                                        # Temporary access for customers who have paid but subscription setup issues
                                        st.markdown("---")
                                        st.write("**🔧 Paid Customer Access:**")
                                        st.info("Since you're a verified customer who has made payments, you can get temporary access while we resolve the subscription status.")
                                        
                                        if st.button("🚀 Grant Temporary Access", type="primary"):
                                            st.session_state.user_email = user_email
                                            st.session_state.user_subscribed = True
                                            st.session_state.access_granted = True
                                            st.session_state.temp_access = True
                                            st.success("✅ Temporary access granted! Loading app...")
                                            st.rerun()
                                
                            except Exception as e:
                                st.error(f"❌ Unexpected error: {str(e)}")
                    else:
                        st.error("Please enter your email address.")
                
                # Add admin access as a smaller option
                st.markdown("---")
                with st.expander("🔐 Admin Access", expanded=False):
                    admin_password = st.text_input("Admin Password", type="password", key="admin_password")
                    if st.button("Admin Login", type="secondary"):
                        correct_password = st.secrets.get("admin_password", "feedbackai2024")
                        if admin_password == correct_password:
                            st.session_state.admin_access = True
                            st.session_state.access_granted = True
                            st.rerun()
                        else:
                            st.error("Incorrect admin password.")
    

    
    # Instructions for access
    st.markdown("---")
    st.markdown("""
        <div style='text-align: center; padding: 1rem;'>
            <h4 style='color: #666;'>How to Access FeedbackAI:</h4>
            <div style='color: #666; font-size: 0.9rem; text-align: left; max-width: 400px; margin: 0 auto;'>
                <p><strong>New Users:</strong></p>
                <p>1. Click "Subscribe Now" to purchase access<br>
                2. Complete payment in the new tab<br>
                3. Return here and use "Subscriber Login" with your email</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Add BGorgeous Solutions trademark at the bottom
    st.markdown("---")
    st.markdown("""
        <div style='text-align: center; padding: 1rem 0; color: #888; font-size: 0.9rem;'>
            <p>© 2025 BGorgeous Solutions Private Limited™. All rights reserved.</p>
            <p style='font-size: 0.8rem; margin-top: 0.5rem;'>Powered by BGorgeous Solutions - Innovative AI & Data Analytics</p>
        </div>
    """, unsafe_allow_html=True)

def check_access():
    """Check if user has access to the app."""
    # Initialize session states
    if "access_granted" not in st.session_state:
        st.session_state.access_granted = False
    if "admin_access" not in st.session_state:
        st.session_state.admin_access = False
    
    # Admin access check first
    if st.session_state.admin_access:
        st.session_state.access_granted = True
        return True
    
    # For now, allow access without subscription for testing
    # You can enable this after payment system is fully set up
    # st.session_state.access_granted = True
    # return True
    
    # Check subscription via the existing auth system
    user_subscribed = st.session_state.get("user_subscribed", False)
    
    # Grant access if subscribed or admin
    if user_subscribed:
        st.session_state.access_granted = True
        return True
    
    return False

# Check access before showing the app
if not check_access():
    show_access_gate()
    st.stop()

# # If access is granted, show the full app interface
# st.sidebar.write(f"Memory usage: {get_memory_usage():.2f} MB")

# # Add access control in sidebar

if st.session_state.admin_access:
    st.sidebar.success("✅ Admin Access")
else:
    user_email = st.session_state.get("user_email", "Unknown")
    st.sidebar.success("✅ Subscriber Access")
    st.sidebar.info(f"👤 {user_email}")
    
    # # Show subscription details if available
    # if "subscription_info" in st.session_state:
    #     sub_info = st.session_state.subscription_info
    #     if sub_info.get("total_active_subscriptions", 0) > 0:
    #         st.sidebar.success(f"🎯 {sub_info['total_active_subscriptions']} Active Subscription(s)")

if st.sidebar.button("🚪 Logout", type="secondary"):
    # Clear all session states
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

st.sidebar.markdown("---")

# Create three columns with ratios (4:1:1 works well for title + two logos)
col1, col2 = st.columns([4, 1])

# Add title to the left column
with col1:
    st.title("FeedbackAI")
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

### MAIN APPLICATION ###
def main():

    # Single startup status message (keep only one status as requested)
    st.info("📂 Loading data...")

    # Load data from specified location
    file_path_1 = "data/gt_chennai_locations_metadata.csv"
    columns_to_load_1 = ["Place ID", "City Area", "Area", "Name", "City", "Rating", "Total Reviews", "Address"]  # Replace with actual column names you need
    try:
        ratings_df = load_data(file_path_1, columns=columns_to_load_1)
        ratings_df = load_data(file_path_1)
        ratings_df.rename(columns={"Place ID": "place_id"}, inplace=True)
    except Exception as e:
        st.error(f"Error loading location data: {str(e)}")
        return

    bucket = 'gt-reviews'
    key = 'combined/gt_kov_reviews.csv'
    columns_to_load_2 = ["id_review", "caption", "review_date", "rating", "username", "place_id"]

    reviews_df = load_csv_from_s3(bucket, key, columns_to_load_2)
    if reviews_df.empty:
        st.error("Failed to load reviews data. Please check your AWS configuration or local cache.")
        return

    reviews_df['review_date'] = pd.to_datetime(reviews_df['review_date'], errors='coerce')
    last_date = reviews_df['review_date'].max()

    reviews_df['caption'] = reviews_df['caption'].fillna("No Review Available")

    df = pd.merge(ratings_df, reviews_df, on="place_id", how="left")
    # df = pd.merge(df, sentiments_df, on=["id_review"], how="left")

    df = df[df["caption"].notna()]
    df['full_location'] = df['Area'] + " " + df['Name']

    # Initialize AI sentiment analyzer with progress indicator
    with st.spinner("🤖 Loading AI sentiment analysis model..."):
        from app_utils import get_sentiment_analyzer
        analyzer = get_sentiment_analyzer()
        
    if analyzer is None:
        st.warning("⚠️ AI model unavailable, using rating-based fallback analysis.")
    else:
        st.success("✅ AI sentiment model loaded successfully!")

    # Run sentiment analysis (batch). Keep output minimal; only warn on failure.
    with st.spinner("🔍 Analyzing sentiment for all reviews..."):
        try:
            sentiment_categories, sentiment_scores, sentiment_emojis = analyze_sentiments_batch(
                df, 'caption', 'rating', batch_size=16
            )
            df['sentiment_category'] = sentiment_categories
            df['sentiment_score'] = sentiment_scores
            df['sentiment_emoji'] = sentiment_emojis
        except Exception as e:
            st.warning(f"AI batch processing failed, falling back to individual analysis: {str(e)}")
            sentiment_results = df.apply(lambda row: analyze_sentiment(row['caption'], row['rating']), axis=1)
            df['sentiment_category'] = sentiment_results.apply(lambda x: x[0])
            df['sentiment_score'] = sentiment_results.apply(lambda x: x[1])
            df['sentiment_emoji'] = sentiment_results.apply(lambda x: x[2])

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


    if last_date:
        day = last_date.day
        day_suffix = get_day_suffix(day)
        formatted_date = last_date.strftime(f"%B {day}{day_suffix} at %I %p").replace(" 0", " ")  # Remove leading 0
        st.write(f"🔄 Data was last scraped on **{formatted_date}**")
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

    # Custom date range inputs (show only when Custom Range is selected)
    start_date = None
    end_date = None
    if selected_timeline_label == "Custom Range":
        start_date = st.sidebar.date_input("Start Date", value=today)
        end_date = st.sidebar.date_input("End Date", value=today)
        
        if start_date > end_date:
            st.sidebar.error("Start Date cannot be after End Date.")

    # Rating filter
    rating = st.sidebar.slider(
        "Select Rating",
        min_value=0,  # Minimum value for the slider
        max_value=5,  # Maximum value for the slider
        value=0,  # Default value
        step=1  # Step size for the slider
    )

    # Sentiment filter
    sentiment_options = ["All", "Very Positive", "Positive", "Neutral", "Negative", "Very Negative"]
    selected_sentiment = st.sidebar.selectbox(
        "Select Sentiment",
        options=sentiment_options
    )

    # Location filter with "All" option

    # City and City Area Filters
    # selected_city = st.sidebar.selectbox("Select City", options=["All"] + list(df['City'].dropna().unique()))

    # selected_city_area = st.sidebar.selectbox(
    #     "Select City Area",
    #     options=["All"] + list(df['City Area'].dropna().unique()),
    #     key="city_area_selectbox"
    # )
    # selected_location = st.sidebar.selectbox("Select a Naturals Location",
    #                                          options=["All"] + list(df['full_location'].unique()))

    # Sidebar: City Filter
    selected_city = st.sidebar.selectbox(
        "Select City",
        options=["All"] + sorted(df['City'].dropna().unique())
    )

    # Filter City Area options based on selected City
    if selected_city != "All":
        filtered_city_areas = df[df['City'] == selected_city]['City Area'].dropna().unique()
    else:
        filtered_city_areas = df['City Area'].dropna().unique()

    selected_city_area = st.sidebar.selectbox(
        "Select City Area",
        options=["All"] + sorted(filtered_city_areas),
        key="city_area_selectbox"
    )

    # Filter Naturals Locations based on selected City Area
    if selected_city_area != "All":
        filtered_locations = df[df['City Area'] == selected_city_area]['full_location'].dropna().unique()
    elif selected_city != "All":
        filtered_locations = df[df['City'] == selected_city]['full_location'].dropna().unique()
    else:
        filtered_locations = df['full_location'].dropna().unique()

    selected_location = st.sidebar.selectbox(
        "Select a Naturals Location",
        options=["All"] + sorted(filtered_locations)
    )


    # APPLY FILTERS
    filtered_df = df.copy()
    # Ensure 'review_date' is in datetime64[ns]
    filtered_df['review_date'] = pd.to_datetime(filtered_df['review_date'], errors='coerce')

    if selected_city != "All":
        filtered_df = filtered_df.loc[filtered_df['City'] == selected_city]

    if selected_city_area != "All":
        filtered_df = filtered_df.loc[filtered_df['City Area'] == selected_city_area]

    # Convert 'selected_timeline' to datetime64[ns]
    if selected_timeline:
        selected_timeline = (
            pd.to_datetime(selected_timeline[0]),
            pd.to_datetime(selected_timeline[1])
        )

    # Filtering Logic
    # Apply timeline filter
    if selected_timeline_label == "All":
        # No date filter, show all data
        pass  
    elif selected_timeline_label == "Custom Range":
        if start_date and end_date and start_date <= end_date:
            # Convert dates to datetime and include the full end date (until 23:59:59)
            start_datetime = pd.to_datetime(start_date)
            end_datetime = pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
            
            # Apply filter using datetime comparison
            filtered_df = filtered_df[
                (filtered_df['review_date'] >= start_datetime) &
                (filtered_df['review_date'] <= end_datetime)
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
    if selected_sentiment != "All":
        filtered_df = filtered_df[filtered_df['sentiment_category'] == selected_sentiment]

    # #### Key Metrics ####
    st.header("Key Metrics")
    M1, M2 = st.columns(2)
    m1, m2, m3, m4 = M1.columns(4)
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

    # Overall Sentiment Score
    overall_sentiment_score = calculate_overall_sentiment_score(filtered_df)
    sentiment_emoji = "😍" if overall_sentiment_score >= 4.5 else "😊" if overall_sentiment_score >= 3.5 else "😐" if overall_sentiment_score >= 2.5 else "😞" if overall_sentiment_score >= 1.5 else "😡"
    m4.metric(label="🤖 AI Sentiment Score", value=f"{sentiment_emoji} {overall_sentiment_score}/5")

    if not filtered_df.empty:
        # Ensure 'review_date' is in datetime format
        filtered_df['review_date'] = pd.to_datetime(filtered_df['review_date'], errors='coerce')

        # Calculate performance metrics for best/least rated locations
        # Get the date range for the filtered data
        min_date = filtered_df['review_date'].min()
        max_date = filtered_df['review_date'].max()
        
        # Calculate midpoint to split the period
        date_range = max_date - min_date
        midpoint_date = min_date + (date_range / 2)
        
        # Split data into first half and second half periods
        first_half = filtered_df[filtered_df['review_date'] <= midpoint_date]
        second_half = filtered_df[filtered_df['review_date'] > midpoint_date]
        
        # Calculate average ratings for each location in both periods
        location_performance = []
        
        for location in filtered_df['full_location'].unique():
            location_data = filtered_df[filtered_df['full_location'] == location]
            
            # First half ratings
            first_half_data = first_half[first_half['full_location'] == location]
            first_half_rating = first_half_data['rating'].mean() if not first_half_data.empty else None
            
            # Second half ratings  
            second_half_data = second_half[second_half['full_location'] == location]
            second_half_rating = second_half_data['rating'].mean() if not second_half_data.empty else None
            
            # Overall rating for this location
            overall_rating = location_data['rating'].mean()
            
            # Calculate percentage change
            if first_half_rating is not None and second_half_rating is not None and first_half_rating > 0:
                percentage_change = ((second_half_rating - first_half_rating) / first_half_rating) * 100
            else:
                percentage_change = 0
            
            location_performance.append({
                'Location': location,
                'Overall_Rating': overall_rating,
                'First_Half_Rating': first_half_rating,
                'Second_Half_Rating': second_half_rating,
                'Percentage_Change': percentage_change,
                'Review_Count': len(location_data)
            })
        
        # Convert to DataFrame for easier manipulation
        performance_df = pd.DataFrame(location_performance)
        
        # Filter out locations with very few reviews to avoid misleading metrics
        performance_df = performance_df[performance_df['Review_Count'] >= 3]
        
        if not performance_df.empty:
            # Identify best-rated and least-rated locations
            best_location = performance_df.loc[performance_df['Overall_Rating'].idxmax()]
            least_location = performance_df.loc[performance_df['Overall_Rating'].idxmin()]
            
            # Display metrics
            with l1:
                best_delta = best_location['Percentage_Change']
                delta_display = f"{best_delta:+.1f}%" if not pd.isna(best_delta) else "N/A"
                st.metric(
                    label="Best Rated Location",
                    value=f"{best_location['Location'][:25]}..." if len(best_location['Location']) > 25 else best_location['Location'],
                    delta=f"{delta_display} (Rating: {best_location['Overall_Rating']:.2f})"
                )

            with l2:
                least_delta = least_location['Percentage_Change'] 
                delta_display = f"{least_delta:+.1f}%" if not pd.isna(least_delta) else "N/A"
                st.metric(
                    label="Least Rated Location",
                    value=f"{least_location['Location'][:25]}..." if len(least_location['Location']) > 25 else least_location['Location'],
                    delta=f"{delta_display} (Rating: {least_location['Overall_Rating']:.2f})"
                )
        else:
            with l1:
                st.metric(label="Best Rated Location", value="Insufficient Data")
            with l2:
                st.metric(label="Least Rated Location", value="Insufficient Data")

    else:
        st.warning("No data available for the selected timeline.")

    #### Charts ####
    # Sentiment Distribution Chart
    st.header("🤖 AI-Powered Customer Sentiment Analysis")
    
    if not filtered_df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            # Sentiment Distribution Pie Chart
            sentiment_dist = get_sentiment_distribution(filtered_df)
            if not sentiment_dist.empty:
                # Add colors for each sentiment
                colors = {
                    'Very Positive': '#0be881',  # Green
                    'Positive': '#48dbfb',       # Light Blue
                    'Neutral': '#feca57',        # Yellow
                    'Negative': '#ff9ff3',       # Pink
                    'Very Negative': '#ff6b6b'   # Red
                }
                
                fig_pie = px.pie(
                    sentiment_dist, 
                    names='Sentiment', 
                    values='Count',
                    title='AI-Analyzed Customer Sentiment Distribution',
                    color='Sentiment',
                    color_discrete_map=colors
                )
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_pie, theme="streamlit", use_container_width=True)
        
        with col2:
            # Sentiment vs Rating Correlation
            if 'sentiment_score' in filtered_df.columns and 'rating' in filtered_df.columns:
                # Create scatter plot showing correlation between sentiment score and rating
                fig_scatter = px.scatter(
                    filtered_df,
                    x='rating',
                    y='sentiment_score',
                    color='sentiment_category',
                    title='AI Sentiment Score vs Star Rating Correlation',
                    labels={
                        'rating': 'Star Rating (1-5)',
                        'sentiment_score': 'AI Sentiment Score (1-5)',
                        'sentiment_category': 'AI Sentiment Category'
                    },
                    color_discrete_map=colors
                )
                fig_scatter.update_layout(showlegend=True)
                st.plotly_chart(fig_scatter, theme="streamlit", use_container_width=True)
    else:
        st.warning("No data available for sentiment analysis.")

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

    filtered_df['review_date'] = pd.to_datetime(filtered_df['review_date'], errors='coerce')
    filtered_df['review_date'] = filtered_df['review_date'].dt.strftime('%d-%b-%y')

    filtered_df = filtered_df.rename(columns={
                            "caption": "Review",
                            "review_date": "Review Date",
                            "username": "User Name",
                            "rating": "Rating ",
                            "id_review": "Review ID",
                            "Name": "Salon Name",
                            "sentiment_category": "Sentiment",
                            "sentiment_score": "Sentiment Score"
                            })

    # Create sentiment display column with emoji
    filtered_df['Sentiment Display'] = filtered_df['sentiment_emoji'] + " " + filtered_df['Sentiment']

    # Create Google Maps Place Links using the Place ID (more reliable than individual review links)
    filtered_df['Review Link'] = filtered_df['place_id'].apply(
        lambda place_id: f"https://www.google.com/maps/place/?q=place_id:{place_id}" if pd.notna(place_id) else ""
    )

    #### Filtered Table ####
    st.header("Customer Google Reviews")
    
    # Method 1: Using pandas styling to highlight specific columns
    def highlight_rating_column(s):
        """Highlight the Rating column based on values"""
        if s.name == 'Rating ':
            # Color based on rating value
            return ['background-color: #ff6b6b' if val <= 2 else 
                   'background-color: #feca57' if val <= 3 else 
                   'background-color: #48dbfb' if val <= 4 else
                   'background-color: #0be881' for val in s]
        elif s.name == 'Sentiment Score':
            # Color based on sentiment score
            return ['background-color: #ff6b6b' if val <= 2 else 
                   'background-color: #feca57' if val <= 3 else 
                   'background-color: #48dbfb' if val <= 4 else
                   'background-color: #0be881' for val in s]
        else:
            return [''] * len(s)
    
    # Method 2: Highlight specific column with single color
    def highlight_column(s):
        """Highlight specific columns with colors"""
        if s.name == 'Rating ':
            return ['background-color: #fff3cd; color: #856404'] * len(s)
        elif s.name == 'Review':
            return ['background-color: #f8f9fa; font-style: italic'] * len(s)
        elif s.name == 'Sentiment Display':
            return ['background-color: #e8f5e8; font-weight: bold'] * len(s)
        else:
            return [''] * len(s)
    
    # Choose which styling to apply
    display_df = filtered_df[["User Name", "Review", "Rating ", "Sentiment Display", "Sentiment Score", "Review Date", "Area", "City", "Review Link", "Review ID", "Salon Name"]]
    
    # Option 1: Rating and sentiment-based color coding
    styled_df = display_df.style.apply(highlight_rating_column, axis=0)
    
    # Option 2: Simple column highlighting (uncomment to use instead)
    # styled_df = display_df.style.apply(highlight_column, axis=0)
    
    # Option 3: Multiple column highlighting with different colors
    # styled_df = (display_df.style
    #              .apply(lambda x: ['background-color: #e8f5e8' if x.name == 'Rating ' else ''] * len(x), axis=0)
    #              .apply(lambda x: ['background-color: #fff2e8' if x.name == 'Review' else ''] * len(x), axis=0))
    
    st.dataframe(styled_df, use_container_width=True)

    # Add BGorgeousSolutions trademark at the bottom of main app
    st.markdown("---")
    st.markdown("""
        <div style='text-align: center; padding: 1rem 0; color: #888; font-size: 0.9rem;'>
            <p>© 2025 BGorgeous Solutions Private Limited™. All rights reserved.</p>
        </div>
    """, unsafe_allow_html=True)



# Run the app
if __name__ == "__main__":
    main()
