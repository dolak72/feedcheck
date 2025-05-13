import streamlit as st
import pandas as pd
import requests
import time
from bs4 import BeautifulSoup
from streamlit_selenium import webdriver_session
import re

st.title('Dead Link Checker')
st.write('Upload a text file with URLs (one per line) to check if pages are dead or alive.')

# Configuration settings with UI controls
with st.sidebar:
    st.header('Settings')
    redirect_param = st.text_input('Redirect Parameter', value='redirectFromMissingVDP=true')
    wait_time = st.slider('Wait time (seconds)', min_value=1, max_value=5, value=2)
    st.markdown("---")
    st.markdown("### How it works")
    st.markdown("""
    This tool checks if URLs are dead or alive by:
    1. Loading each URL in a browser
    2. Checking if it redirects to a page with the parameter: `redirectFromMissingVDP=true`
    3. Checking if the page contains the text "Oops!" and "This page is in the shop"
    """)

uploaded_file = st.file_uploader("Choose a text file with URLs", type="txt")

# Function to check if a URL is dead using Selenium
def check_url_with_selenium(driver, url, redirect_param, wait_time):
    try:
        driver.get(url)
        # Wait for any redirects to happen
        time.sleep(wait_time)
        
        # Get the current URL after potential redirect
        current_url = driver.current_url
        
        # Check if we've been redirected to the inventory page with the special parameter
        if redirect_param in current_url:
            return "Dead Page (Redirected)", current_url
        
        # Check if the original "Oops!" message is visible
        page_source = driver.page_source
        if "Oops!" in page_source and "This page is in the shop" in page_source:
            return "Dead Page (Error Message)", url
            
        # If we don't see redirect or error message, assume the page is alive
        return "Live Page", current_url
        
    except Exception as e:
        return f"Error: {str(e)}", url

# Fallback function using requests (in case Selenium isn't available)
def check_url_with_requests(url, redirect_param):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, allow_redirects=True, timeout=10)
        
        # Check if we've been redirected to the inventory page with the special parameter
        if redirect_param in response.url:
            return "Dead Page (Redirected)", response.url
            
        # Check for error message in content
        if "Oops!" in response.text and "This page is in the shop" in response.text:
            return "Dead Page (Error Message)", url
            
        # If status code is 404 or 5xx
        if response.status_code >= 400:
            return f"Error: HTTP {response.status_code}", url
            
        return "Live Page", response.url
    except Exception as e:
        return f"Error: {str(e)}", url

if uploaded_file is not None:
    urls = [line.decode("utf-8").strip() for line in uploaded_file.readlines() if line.decode("utf-8").strip()]
    st.write(f"Found {len(urls)} URLs to check")
    
    if st.button('Start Checking'):
        # Initialize Selenium session if available, otherwise use requests
        try:
            with webdriver_session() as driver:
                progress_bar = st.progress(0)
                result_data = []
                
                # Create placeholder for results table that we'll update
                results_placeholder = st.empty()
                df = pd.DataFrame(columns=["URL", "Status", "Final URL"])
                results_placeholder.dataframe(df)
                
                for i, url in enumerate(urls):
                    with st.spinner(f'Checking URL {i+1}/{len(urls)}: {url}'):
                        status, final_url = check_url_with_selenium(driver, url, redirect_param, wait_time)
                        result_data.append({"URL": url, "Status": status, "Final URL": final_url})
                        
                        # Update the dataframe and display
                        df = pd.DataFrame(result_data)
                        results_placeholder.dataframe(df)
                        
                        # Update progress
                        progress_bar.progress((i+1)/len(urls))
                
                st.success('All URLs checked!')
        except Exception as e:
            # Fallback to requests if Selenium is not available
            st.warning(f"Selenium not available, using backup method: {str(e)}")
            
            progress_bar = st.progress(0)
            result_data = []
            
            # Create placeholder for results table
            results_placeholder = st.empty()
            df = pd.DataFrame(columns=["URL", "Status", "Final URL"])
            results_placeholder.dataframe(df)
            
            for i, url in enumerate(urls):
                with st.spinner(f'Checking URL {i+1}/{len(urls)}: {url}'):
                    status, final_url = check_url_with_requests(url, redirect_param)
                    result_data.append({"URL": url, "Status": status, "Final URL": final_url})
                    
                    # Update the dataframe and display
                    df = pd.DataFrame(result_data)
                    results_placeholder.dataframe(df)
                    
                    # Update progress
                    progress_bar.progress((i+1)/len(urls))
            
            st.success('All URLs checked using fallback method!')
        
        # Create a download button for the results
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download results as CSV",
            data=csv,
            file_name="page_check_results.csv",
            mime="text/csv"
        )
