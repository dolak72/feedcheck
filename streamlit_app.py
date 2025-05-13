import streamlit as st
import pandas as pd
import requests
import time
import csv
import io
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

st.title('Dead Link Checker')
st.write('Upload a text file with URLs (one per line) to check if pages are dead or alive.')

# Configuration settings with UI controls
with st.sidebar:
    st.header('Settings')
    use_selenium = st.checkbox('Use Selenium (more accurate but slower)', value=True)
    num_threads = st.slider('Number of threads', min_value=1, max_value=10, value=3)
    redirect_param = st.text_input('Redirect Parameter', value='redirectFromMissingVDP=true')

uploaded_file = st.file_uploader("Choose a text file with URLs", type="txt")

def setup_selenium():
    options = Options()
    options.add_argument('user-agent=Mozilla/5.0')
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920x1080")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def check_url(url):
    if use_selenium:
        driver = None
        try:
            driver = setup_selenium()
            driver.get(url)
            time.sleep(2)
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
    else:
        try:
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, allow_redirects=True)
            final_url = response.url
            if redirect_param in final_url:
                return "Dead Page (Redirected)", final_url
            return "Live Page", final_url
        except Exception as e:
            return f"Error: {str(e)}", url

if uploaded_file is not None:
    urls = [line.decode("utf-8").strip() for line in uploaded_file.readlines() if line.decode("utf-8").strip()]
    st.write(f"Found {len(urls)} URLs to check")
    
    if st.button('Start Checking'):
        progress_bar = st.progress(0)
        result_data = []
        
        # Create placeholder for results table that we'll update
        results_placeholder = st.empty()
        df = pd.DataFrame(columns=["URL", "Status", "Final URL"])
        results_placeholder.dataframe(df)
        
        for i, url in enumerate(urls):
            with st.spinner(f'Checking URL {i+1}/{len(urls)}: {url}'):
                status, final_url = check_url(url)
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
