import streamlit as st
import pandas as pd
import requests
import time

st.title('Dead Link Checker')
st.write('Upload a text file with URLs (one per line) to check if pages are dead or alive.')

# Configuration settings
with st.sidebar:
    st.header('Settings')
    redirect_param = st.text_input('Redirect Parameter', value='redirectFromMissingVDP=true')
    timeout = st.slider('Request Timeout (seconds)', min_value=5, max_value=30, value=10)
    st.markdown("---")
    st.markdown("### How it works")
    st.markdown("""
    This tool checks if URLs are dead or alive by:
    1. Loading each URL and checking for redirects
    2. Checking if it redirects to a page with the parameter: `redirectFromMissingVDP=true`
    3. Checking if the page contains the text "Oops!" and "This page is in the shop"
    """)

uploaded_file = st.file_uploader("Choose a text file with URLs", type="txt")

# Function to check URL with Requests
def check_url(url, redirect_param, timeout):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, allow_redirects=True, timeout=timeout)
        
        # Check if we've been redirected to the inventory page with the special parameter
        if redirect_param in response.url:
            return "Dead Page (Redirected)", response.url
            
        # Check for error message in content
        if "Oops!" in response.text and "This page is in the shop" in response.text:
            return "Dead Page (Error Message)", url
            
        # Check HTTP status code
        if response.status_code >= 400:
            return f"Error: HTTP {response.status_code}", url
            
        return "Live Page", response.url
    except Exception as e:
        return f"Error: {str(e)}", url

if uploaded_file is not None:
    urls = [line.decode("utf-8").strip() for line in uploaded_file.readlines() if line.decode("utf-8").strip()]
    st.write(f"Found {len(urls)} URLs to check")
    
    if st.button('Start Checking'):
        progress_bar = st.progress(0)
        result_data = []
        
        # Create placeholder for results table
        results_placeholder = st.empty()
        df = pd.DataFrame(columns=["URL", "Status", "Final URL"])
        results_placeholder.dataframe(df)
        
        for i, url in enumerate(urls):
            with st.spinner(f'Checking URL {i+1}/{len(urls)}: {url}'):
                status, final_url = check_url(url, redirect_param, timeout)
                result_data.append({"URL": url, "Status": status, "Final URL": final_url})
                
                # Update the dataframe and display
                df = pd.DataFrame(result_data)
                results_placeholder.dataframe(df)
                
                # Update progress
                progress_bar.progress((i+1)/len(urls))
        
        st.success('All URLs checked!')
        
        # Create a download button for the results
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download results as CSV",
            data=csv,
            file_name="page_check_results.csv",
            mime="text/csv"
        )
