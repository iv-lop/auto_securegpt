import sys
import os
import re
import json
import argparse
import glob
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd
import time
import pyperclip
from datetime import datetime
import pytz

def send_data_and_get_output(
        driver,
        prompt, 
        input_text_lag_time,
        generation_sleep_timer,
        max_data_loading_retries,
        retry_data_loading_wait_time,
        max_chat_dialogs,
        global_iteration,
        total_iterations,
        llm_output,
        prompt_column_name,
        output_column_name,
        disclaimer_statement,
        terms_to_avoid,
        min_output_word_count,
):
    if global_iteration == 1 and disclaimer_statement is not None:
        print(f"Sending disclaimer statement")
        search_bar = driver.find_element(By.CSS_SELECTOR, 'textarea.flex.w-full')
        search_bar.clear()
        search_bar.send_keys(disclaimer_statement)
        time.sleep(5)
        click_send_data_button(driver)
        time.sleep(generation_sleep_timer)

    search_bar = driver.find_element(By.CSS_SELECTOR, 'textarea.flex.w-full') # Find the search bar
    search_bar.clear()  # Clearing the search bar before sending new data
    processed_data = prompt.replace('\n', ' ') # Remove or replace newline characters, then add a newline at the end
    search_bar.send_keys(processed_data) # Send the data to the search bar
    time.sleep(input_text_lag_time) # Wait for input to be sent to search bar
    click_send_data_button(driver) # Click send data button
    time.sleep(generation_sleep_timer) # Wait for the output to be displayed

    retries = 0
    while is_loading_present(driver) and retries < max_data_loading_retries:
        retries += 1
        print(f"Count {retries}: Waiting for data to load...")
        time.sleep(retry_data_loading_wait_time)

    # Find all elements that match the output structure
    elements_start = driver.find_elements(By.XPATH, "//*[contains(@class, 'container mx-auto max-w-4xl py-6 flex flex-col items-start')]")
    elements_end = driver.find_elements(By.XPATH, "//*[contains(@class, 'container mx-auto max-w-4xl py-6 flex flex-col items-end')]")

    if retries < max_data_loading_retries:        
        # Assuming the newest output is always last, get the last element's text and dialog sent
        latest_output = elements_start[-1].text.replace('Secure GPT (Beta)\n', '').replace('\n', ' ').lower()
        user_contained_text = elements_end[-1].text
        latest_send = re.sub(r'.*\s\(SU\)\n', '', user_contained_text)
        word_count = len(latest_output.split())
        
        if global_iteration != 1:
            # Validate latest_output for content moderation failure
            latest_output, latest_send = validate_latest_dialog_sent(
                latest_output=latest_output, 
                latest_send=latest_send, 
                llm_output=llm_output, 
                prompt_column_name=prompt_column_name, 
                output_column_name=output_column_name, 
                processed_data=processed_data
                )
    elif retries >= max_data_loading_retries:
        print(f"Data loading retries exceeded. Setting output as 'DATA_LOAD_FAILURE'")
        latest_output = "DATA_LOAD_FAILURE"
        user_contained_text = elements_end[-1].text
        latest_send = re.sub(r'.*\s\(SU\)\n', '', user_contained_text)
        word_count = len(latest_output.split()) # recalculating word count for 'DATA_LOAD_FAILURE' to initiate check_for_terms_and_resend_data_if_needed() loop
    
    print(f"Checking LLM Output for terms to avoid...")
    latest_output, latest_send, word_count = check_for_terms_and_resend_data_if_needed(
        latest_output=latest_output,
        latest_send=latest_send,
        disclaimer_statement=disclaimer_statement,
        terms_to_avoid=terms_to_avoid,
        min_output_word_count=min_output_word_count,
        word_count=word_count,
        driver=driver,
        prompt=prompt, 
        input_text_lag_time=input_text_lag_time,
        generation_sleep_timer=generation_sleep_timer,
        max_data_loading_retries=max_data_loading_retries,
        retry_data_loading_wait_time=retry_data_loading_wait_time,
        global_iteration=global_iteration,
        llm_output=llm_output,
        prompt_column_name=prompt_column_name,
        output_column_name=output_column_name,
        )
    print(f"LLM Output:\n{latest_output}")

    # # validate latest_output:
    # latest_output = validate_output_text(latest_output)

    # Create new chat window (if statement)
    if disclaimer_statement is not None:
        total_outputs = len(elements_start)-1
    else:
        total_outputs = len(elements_start)
    if total_outputs % max_chat_dialogs == 0 and global_iteration != total_iterations:
            print("\n\nCreating new chat window...")
            click_new_chat_button(driver=driver)
            time.sleep(3)
            click_balanced_button(driver=driver)
            # time.sleep(3)
            # click_file_button(driver=driver)
            print("New chat window created\n\n")
            time.sleep(5)

            if disclaimer_statement is not None:
                print(f"Sending disclaimer statement")
                search_bar = driver.find_element(By.CSS_SELECTOR, 'textarea.flex.w-full')
                search_bar.clear()
                search_bar.send_keys(disclaimer_statement)
                time.sleep(5)
                click_send_data_button(driver)
                time.sleep(generation_sleep_timer)

    return latest_output, latest_send

def check_for_terms_and_resend_data_if_needed(
        latest_output,
        latest_send,
        disclaimer_statement,
        terms_to_avoid,
        min_output_word_count,
        word_count,
        driver,
        prompt,
        input_text_lag_time,
        generation_sleep_timer,
        max_data_loading_retries,
        retry_data_loading_wait_time,
        global_iteration,
        llm_output,
        prompt_column_name,
        output_column_name,
):
    while True:
        # Check conditions
        contains_forbidden_terms = any(term.lower() in latest_output.lower() for term in terms_to_avoid)
        below_min_word_count = word_count <= min_output_word_count

        if not contains_forbidden_terms and not below_min_word_count:
            break  # Exit loop if output is acceptable

        # Debug printouts to identify the cause of the reiteration
        if contains_forbidden_terms:
            print("Output contains forbidden terms.")
        if below_min_word_count:
            print("Output is below the minimum word count.")

        # Inform about the inference error with specifics
        print(f"LLM Inference Error:\n{latest_output}\nWord Count: {word_count}\nForbidden Terms Present: {contains_forbidden_terms}")

        # Reset process
        print("\n\nCreating new chat window...")
        click_new_chat_button(driver=driver)
        time.sleep(3)
        click_balanced_button(driver=driver)
        print("New chat window created\n\n")
        time.sleep(5)

        print(f"\nSending disclaimer statement")
        search_bar = driver.find_element(By.CSS_SELECTOR, 'textarea.flex.w-full')
        search_bar.clear()
        search_bar.send_keys(disclaimer_statement)
        time.sleep(5)
        click_send_data_button(driver)
        time.sleep(generation_sleep_timer)

        # Resend data process
        search_bar = driver.find_element(By.CSS_SELECTOR, 'textarea.flex.w-full')
        search_bar.clear()
        processed_data = prompt.replace('\n', ' ')
        search_bar.send_keys(processed_data)
        time.sleep(input_text_lag_time)
        click_send_data_button(driver)
        time.sleep(generation_sleep_timer)

        retries = 0
        while is_loading_present(driver) and retries < max_data_loading_retries:
            retries += 1
            print(f"Count {retries}: Waiting for data to load...")
            time.sleep(retry_data_loading_wait_time)

        # Find all elements that match the output structure
        elements_start = driver.find_elements(By.XPATH, "//*[contains(@class, 'container mx-auto max-w-4xl py-6 flex flex-col items-start')]")
        elements_end = driver.find_elements(By.XPATH, "//*[contains(@class, 'container mx-auto max-w-4xl py-6 flex flex-col items-end')]")

        if retries < max_data_loading_retries:        
            # Assuming the newest output is always last, get the last element's text and dialog sent
            latest_output = elements_start[-1].text.replace('Secure GPT (Beta)\n', '').replace('\n', ' ').lower()
            user_contained_text = elements_end[-1].text
            latest_send = re.sub(r'.*\s\(SU\)\n', '', user_contained_text)
            word_count = len(latest_output.split())

            if global_iteration != 1:
                # Validate latest_output for content moderation failure
                latest_output, latest_send = validate_latest_dialog_sent(
                    latest_output=latest_output, 
                    latest_send=latest_send, 
                    llm_output=llm_output, 
                    prompt_column_name=prompt_column_name, 
                    output_column_name=output_column_name, 
                    processed_data=processed_data
                    )
        elif retries >= max_data_loading_retries:
            print(f"Data loading retries exceeded. Setting output as 'DATA_LOAD_FAILURE'")
            latest_output = "DATA_LOAD_FAILURE"
            user_contained_text = elements_end[-1].text
            latest_send = re.sub(r'.*\s\(SU\)\n', '', user_contained_text)
            word_count = len(latest_output.split()) # recalculating word count for 'DATA_LOAD_FAILURE' to initiate check_for_terms_and_resend_data_if_needed() loop

    return latest_output, latest_send, word_count

def validate_latest_dialog_sent(
        latest_output,
        latest_send,
        llm_output,
        prompt_column_name,
        output_column_name,
        processed_data,
):
    # Checking last recorded dialog and latest dialog sent for content moderation failure
    last_send_with_recorded_output = llm_output[llm_output[output_column_name] != 'NA'][prompt_column_name].iloc[-1]
    
    # Check if the latest dialog sent matches the last recorded dialog
    if last_send_with_recorded_output == latest_send:
        # Now check if this duplication is unexpected (i.e., not just repeating processed_data)
        if clean_processed_data(latest_send) != clean_processed_data(processed_data):
            print(f"***Content moderation failure detected***")
            print(f"Last recorded dialog and latest dialog sent are the same - setting latest_output to 'NA'")
            latest_output = "NA"  # Indicating a need to discard this latest output due to moderation failure
            latest_send = processed_data  # Aligning latest_send with processed_data to attempt a 'correction'
    # Always return latest_output and latest_send, potentially adjusted
    return latest_output, latest_send

def click_balanced_button(driver):
    # Assuming 'Balanced' is unique text on the button
    balanced_button_xpath = "//button[contains(., 'Balanced')]"
    balanced_button = driver.find_element(By.XPATH, balanced_button_xpath)
    balanced_button.click()

def click_new_chat_button(driver):
    # Specific CSS selector targeting the parent div and then the button
    # This assumes the combination of div classes is unique to this button
    specific_button_css_selector = 'div.flex.pb-2.items-center.justify-end > button.inline-flex.items-center.justify-center'
    specific_button = driver.find_element(By.CSS_SELECTOR, specific_button_css_selector)
    specific_button.click()

def attempt_send_action(driver):
    if not click_send_data_button(driver):
        # If clicking the send button fails, try to close the notification box
        if close_notification_box(driver):
            # If successfully closed the notification, try clicking the send button again
            click_send_data_button(driver)
        else:
            # If could not close the notification, wait for user input to proceed
            print("Could not handle the notification box; further action might be needed.")
            user_input = input("Please fix the issue and type 1 to continue: ")
            if user_input == "1":
                # Try clicking the send button again after the user indicates the problem is fixed
                click_send_data_button(driver)
            else:
                print("Incorrect input. Exiting the function.")

def close_notification_box(driver):
    try:
        # Wait for the notification box to be visible, but only wait for 1 second
        # Adjust the XPath to use a more direct approach if the button has a unique identifier like `toast-close`
        close_button = WebDriverWait(driver, 1).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[toast-close]"))
        )
        close_button.click()
        print("Notification box closed.")
        return True  # Successfully closed the notification
    except TimeoutException:
        print("No notification box found or could not close in time.")
        return False  # Failed to close the notification

def click_send_data_button(driver):
    send_button_css_selector = "button[type='submit'] svg.lucide.lucide-send"
    send_button = driver.find_element(By.CSS_SELECTOR, send_button_css_selector)
    send_button.click()

def is_loading_present(driver):
    try:
        # Check if the loading spinner is present
        loading_element = driver.find_element(By.XPATH, "//*[contains(@class, 'lucide lucide-loader animate-spin')]")
        return loading_element is not None
    except NoSuchElementException:
        return False

def clean_processed_data(processed_data):
    # Replace one or more whitespace characters (including spaces, tabs, newlines) with a single space
    cleaned_data = re.sub(r'\s+', ' ', processed_data)
    
    # Remove leading and trailing whitespace
    cleaned_data = cleaned_data.strip()
    
    return cleaned_data