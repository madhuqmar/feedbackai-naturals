import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import os
from app_utils import get_last_scraping_date, load_data, run_scraper, load_csv_from_s3
from utils.st_paywall.aggregate_auth import add_auth
import psutil


### APP HEADERS ###
st.set_page_config(layout="wide")

logo_path_1 = "images/naturals_logo.png"
logo_path_2 = "images/naturals_signature.png"

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
        tab1, tab2 = st.tabs(["🔐 Subscribe to Access", "� Subscriber Login"])
        
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
    
    # Add KRAM Solutions trademark at the bottom
    st.markdown("---")
    st.markdown("""
        <div style='text-align: center; padding: 1rem 0; color: #888; font-size: 0.9rem;'>
            <p>© 2025 KRAM Solutions™. All rights reserved.</p>
            <p style='font-size: 0.8rem; margin-top: 0.5rem;'>Powered by KRAM Solutions - Innovative AI & Data Analytics</p>
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

# If access is granted, show the full app interface
st.sidebar.write(f"Memory usage: {get_memory_usage():.2f} MB")

# Add access control in sidebar
st.sidebar.markdown("---")
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

# Create three columns with ratios (4:1:1 works well for title + two logos)
col1, col2, col3 = st.columns([4, 1, 1])

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

# Add the second logo to the third column
with col3:
    st.image(logo_path_2)

### MAIN APPLICATION ###
def main():

    # Load data from specified location
    file_path_1 = "data/naturals_chennai_locations_metadata.csv"
    columns_to_load_1 = ["Place ID", "City Area", "Area", "Name", "City", "Rating", "Total Reviews", "Address"]  # Replace with actual column names you need
    ratings_df = load_data(file_path_1, columns=columns_to_load_1)
    ratings_df = load_data(file_path_1)
    ratings_df.rename(columns={"Place ID": "place_id"}, inplace=True)

    # file_path_2 = "data/data/newest_gm_reviews_2025-01-16.csv"
    # columns_to_load_2 = ["id_review", "caption", "review_date", "rating", "username", "place_id"]
    # reviews_df = load_data(file_path_2, columns=columns_to_load_2)
    # last_date = get_last_scraping_date(file_path_2)

    bucket = 'naturals-reviews'
    key = 'combined/all_4_naturals_salons.csv'
    columns_to_load_2 = ["id_review", "caption", "review_date", "rating", "username", "place_id"]

    reviews_df = load_csv_from_s3(bucket, key, columns=columns_to_load_2)
    reviews_df['review_date'] = pd.to_datetime(reviews_df['review_date'], errors='coerce')
    last_date = reviews_df['review_date'].max()

    reviews_df['caption'] = reviews_df['caption'].fillna("No Review Available")



    # file_path_3 = "data/naturals_sentiments.csv"
    # columns_to_load_3 = ["id_review", "sentiment"]
    # sentiments_df = load_data(file_path_3, columns=columns_to_load_3)

    df = pd.merge(ratings_df, reviews_df, on="place_id", how="left")
    # df = pd.merge(df, sentiments_df, on=["id_review"], how="left")

    df = df[df["caption"].notna()]
    df['full_location'] = df['Area'] + " " + df['Name']

    if not ratings_df.empty and not reviews_df.empty:
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
        filtered_df = filtered_df # No date filter, show all data
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

    filtered_df['review_date'] = pd.to_datetime(filtered_df['review_date'], errors='coerce')
    filtered_df['review_date'] = filtered_df['review_date'].dt.strftime('%d-%b-%y')

    filtered_df = filtered_df.rename(columns={
                            "caption": "Review",
                            "review_date": "Review Date",
                            "username": "User Name",
                            "rating": "Rating ",
                            "id_review": "Review ID",
                            "Name": "Salon Name"
                            })


    #### Filtered Table ####
    st.header("Customer Google Reviews")
    st.dataframe(filtered_df[["Review ID", "Review Date", "Review", "Rating ", "User Name", "City", "Area", "Salon Name"]])

    # Add KRAM Solutions trademark at the bottom of main app
    st.markdown("---")
    st.markdown("""
        <div style='text-align: center; padding: 1rem 0; color: #888; font-size: 0.9rem;'>
            <p>© 2025 KRAM Solutions™. All rights reserved.</p>
        </div>
    """, unsafe_allow_html=True)



# Run the app
if __name__ == "__main__":
    main()
