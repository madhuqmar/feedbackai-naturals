import streamlit as st
import stripe
import urllib.parse


def get_api_key() -> str:
    testing_mode = st.secrets.get("testing_mode", False)
    return (
        st.secrets["stripe_api_key_test"]
        if testing_mode
        else st.secrets["stripe_api_key"]
    )


def redirect_button(
    text: str,
    customer_email: str,
    color="#FFFFFF",  # Default Streamlit primary button color
    payment_provider: str = "stripe",
    use_sidebar: bool = True,
):
    testing_mode = st.secrets.get("testing_mode", False)
    encoded_email = urllib.parse.quote(customer_email)
    if payment_provider == "stripe":
        stripe.api_key = get_api_key()
        stripe_link = (
            st.secrets["stripe_link_test"]
            if testing_mode
            else st.secrets["stripe_link"]
        )
        button_url = f"{stripe_link}?prefilled_email={encoded_email}"
    elif payment_provider == "bmac":
        button_url = f"{st.secrets['bmac_link']}"
    else:
        raise ValueError("payment_provider must be 'stripe' or 'bmac'")

    # Set width based on placement
    width_style = "width: 100%;" if use_sidebar else "width: auto; min-width: 120px; max-width: 240px;"
    
    # Streamlit-like button styling
    button_html = f"""
    <a href="{button_url}" target="_blank">
        <div style="
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 0.5rem 1rem;
            background-color: {color};
            color: white;
            font-size: 14px;
            font-weight: 400;
            line-height: 1.6;
            text-align: center;
            text-decoration: none;
            border-radius: 0.25rem;
            border: none;
            cursor: pointer;
            box-shadow: rgba(0, 0, 0, 0.05) 0px 1px 2px;
            transition: background-color 0.2s ease, transform 0.1s ease;
            {width_style}
            margin-bottom: 0.5rem;">
            {text}
        </div>
    </a>
    """
    
    if use_sidebar:
        st.sidebar.html(button_html)
    else:
        st.html(button_html)


def is_active_subscriber(email: str) -> bool:
    """Check if email has active subscription by querying Stripe customers and subscriptions."""
    try:
        stripe.api_key = get_api_key()
        
        # Search for customers with this email
        customers = stripe.Customer.list(email=email, limit=10)
        
        if not customers.data:
            return False
        
        # Check each customer for active subscriptions
        for customer in customers.data:
            # Get all subscriptions for this customer
            subscriptions = stripe.Subscription.list(
                customer=customer.id,
                status='active',  # Only get active subscriptions
                limit=10
            )
            
            # If any active subscriptions found, user is subscribed
            if subscriptions.data:
                # Store subscription info for debugging
                st.session_state.subscriptions = subscriptions.data
                st.session_state.customer_info = customer
                return True
        
        return False
        
    except Exception as e:
        st.error(f"Error checking subscription: {str(e)}")
        return False


def get_customer_subscription_info(email: str) -> dict:
    """Get detailed subscription information for a customer."""
    try:
        stripe.api_key = get_api_key()
        
        # Search for customers with this email
        customers = stripe.Customer.list(email=email, limit=10)
        
        if not customers.data:
            return {"status": "no_customer", "message": "No customer found with this email"}
        
        customer_info = []
        total_subscriptions = 0
        
        for customer in customers.data:
            # Get all subscriptions for this customer (including inactive ones)
            subscriptions = stripe.Subscription.list(customer=customer.id, limit=10)
            
            active_subs = [sub for sub in subscriptions.data if sub.status == 'active']
            total_subscriptions += len(active_subs)
            
            customer_info.append({
                "customer_id": customer.id,
                "email": customer.email,
                "name": customer.name or "No name",
                "created": customer.created,
                "active_subscriptions": len(active_subs),
                "all_subscriptions": len(subscriptions.data),
                "subscriptions": active_subs
            })
        
        return {
            "status": "found",
            "total_active_subscriptions": total_subscriptions,
            "customers": customer_info,
            "has_active_subscription": total_subscriptions > 0
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
