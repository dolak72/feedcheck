import streamlit as st
import pandas as pd
import requests
import time
import io
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import os

st.title('Dead Link Checker')
st.write('Upload a text file with URLs (one per line) to check if pages are dead or alive.')

# Configuration settings with UI controls
with st.sidebar:
    st.header('Settings')
    use_selenium = st.checkbox('Use Selenium (more accurate but slower)', value=False)
    redirect_param = st.text_input('Redirect Parameter', value='redirectFromMissingVDP=true')
    wait_time = st.slider('Wait time (seconds)', min_value=1, max_value=5, value=2)
    st.markdown("---")
    st.markdown("### How it works")
    st.markdown("""
    This tool checks if URLs are dead or alive by:
    1. Loading each URL and checking for redirects
    2. Checking if it redirects to a page with the parameter: `redirectFromMissingVDP=true`
    3. Checking if the page contains the text "Oops!" and "This page is in the shop"
    """)

uploaded_file = st.file_uploader("Choose a text file with URLs", type="txt")

# Setup Selenium Chrome web driver for Streamlit Cloud
def setup_selenium():
    try:
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-infobars')
        
        # Check if we're on Streamlit Cloud
        if os.path.exists("/home/appuser"):
            # Streamlit Cloud path
            options.binary_location = "/usr/bin/chromium"
            return webdriver.Chrome(options=options)
        else:
            # Local development path
            return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    except Exception as e:
        st.error(f"Failed to initialize Selenium: {e}")
        return None

# Function to check URL with Selenium
def check_url_with_selenium(url, redirect_param, wait_time):
    driver = None
    try:
        driver = setup_selenium()
        if not driver:
            return "Selenium Error", url
            
        driver.get(url)
        time.sleep(wait_time)
        
        current_url = driver.current_url
        
        if redirect_param in current_url:
            return "Dead Page (Redirected)", current_url
        
        page_source = driver.page_source
        if "Oops!" in page_source and "This page is in the shop" in page_source:
            return "Dead Page (Error Message)", url
            
        return "Live Page", current_url
        
    except Exception as e:
        return f"Error: {str(e)}", url
    finally:
        if driver:
            driver.quit()

# Function to check URL with Requests
def check_url_with_requests(url, redirect_param):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, allow_redirects=True, timeout=10)
        
        if redirect_param in response.url:
            return "Dead Page (Redirected)", response.url
            
        if "Oops!" in response.text and "This page is in the shop" in response.text:
            return "Dead Page (Error Message)", url
            
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
                if use_selenium:
                    status, final_url = check_url_with_selenium(url, redirect_param, wait_time)
                else:
                    status, final_url = check_url_with_requests(url, redirect_param)
                    
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
