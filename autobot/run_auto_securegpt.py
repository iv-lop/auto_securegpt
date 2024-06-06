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

pd.set_option('display.max_rows', 50)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)

sys.path.append('~/auto_securegpt')
from autobot.helper_functions import (
    send_data_and_get_output,
    check_for_terms_and_resend_data_if_needed,
    validate_latest_dialog_sent,
    click_balanced_button,
    click_new_chat_button,
    attempt_send_action,
    close_notification_box,
    click_send_data_button,
)

def run_auto_securegpt(
        test,
        test_sample_size,
        inference_prompt_data_path,
        backup_data_path,
        disclaimer_statement,
        min_output_word_count,
        terms_to_avoid,
        save_filename,
        save_folder_path,
        max_chat_dialogs,
        input_text_lag_time,
        generation_sleep_timer,
        max_data_loading_retries,
        retry_data_loading_wait_time,
        website_email_input,
        website_url,
):
    llm_inference_timestamp = datetime.now(pytz.utc).astimezone(pytz.timezone('US/Pacific')).strftime('%Y-%m-%d_%H:%M:%S')

    print(f"\nExpanding Paths")
    prompt_filename = os.path.basename(inference_prompt_data_path)
    inference_prompt_data_path = os.path.expanduser(inference_prompt_data_path)
    save_filename = save_filename.format(timestamp=llm_inference_timestamp, prompt_filename=prompt_filename)
    save_folder_path = os.path.expanduser(save_folder_path)
    print(f"Paths Expanded")

    print(f"\nExpanding Paths")
    inference_prompt_data_path = os.path.expanduser(inference_prompt_data_path)
    print(f"Paths Expanded")

    print(f"\nLoading Data")
    inference_prompt_data = pd.read_csv(inference_prompt_data_path)
    print(f"Data Loaded")
    if backup_data_path is not None:
        print(f"\nLoading Backup Data")
        saved_backup_data = pd.read_csv(os.path.expanduser(backup_data_path))
        print(f"Removing Already Processed Data from Inference Prompt Data")
        inference_prompt_data = inference_prompt_data[~inference_prompt_data['prompt_id'].isin(saved_backup_data['prompt_id'])].reset_index(drop=True)
    print(f"Data Loaded:\{inference_prompt_data}")

    print(f"\nSetting Up Iteration Data")
    prompt_list = inference_prompt_data['formatted_prompt'].to_list()
    prompt_id_list = inference_prompt_data['prompt_id'].to_list()
    print(f"Data Ready")

    print("\nSetup the Chrome WebDriver")
    if website_email_input is not None:
        pyperclip.copy(website_email_input)
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    print("Going to Website")
    driver.get(website_url)
    # Loop until the user inputs '1'
    user_input = ""
    while user_input != "1":
        user_input = input("\nPlease set-up GPT environment. Press 'Enter' after typing '1' to proceed: ")
        if user_input == "1":
            print("Proceeding...")
        else:
            print("Incorrect input. Please type '1' to proceed: ")

    if test:
        print(f"\n\n***Loading Testing Environment***\n\n")
        prompt_list = prompt_list[:test_sample_size]
        prompt_id_list = prompt_id_list[:test_sample_size]

    print(f"\nGenerating Synthetic Data")
    original_column_names = inference_prompt_data.columns.tolist()
    llm_output = pd.DataFrame(columns=original_column_names + ['synthetic_data'])
    global_iteration = 0
    total_iterations = len(prompt_list)

    for prompt, prompt_id in zip(prompt_list, prompt_id_list):
        try:
            global_iteration += 1
            print(f"\n\nProcessing iteration {global_iteration}/{total_iterations}")
            latest_output, latest_send = send_data_and_get_output(
                driver=driver,
                prompt=prompt, 
                input_text_lag_time=input_text_lag_time,
                generation_sleep_timer=generation_sleep_timer,
                max_data_loading_retries=max_data_loading_retries,
                retry_data_loading_wait_time=retry_data_loading_wait_time,
                max_chat_dialogs=max_chat_dialogs,
                global_iteration=global_iteration,
                total_iterations=total_iterations,
                llm_output=llm_output,
                prompt_column_name='formatted_prompt',
                output_column_name='synthetic_data',
                disclaimer_statement=disclaimer_statement,
                terms_to_avoid=terms_to_avoid,
                min_output_word_count=min_output_word_count,
                )

            current_data = {'prompt_id': prompt_id, 'formatted_prompt': latest_send, 'synthetic_data': latest_output}
            llm_output = pd.concat([llm_output, pd.DataFrame([current_data])], ignore_index=True)
        except Exception as e:
            print("An error occurred. Saving progress...")
            error_timestamp = datetime.now(pytz.utc).astimezone(pytz.timezone('US/Pacific')).strftime('%Y-%m-%d_%H:%M:%S')
            save_progress_filename = f"llm_output_backup_{error_timestamp}.csv"
            full_path = os.path.join(save_folder_path, save_progress_filename)
            llm_output.to_csv(full_path, index=False)
            print(f"Progress saved to {full_path}")
            raise e
    print(f"Synthetic Data Generated")

    print(f"\nQuitting Chrome WebDriver")
    driver.quit()
    print(f"Chrome Driver Quit")

    print(f"\nSaving Synthetic Data")
    if test:
        save_filename = f"TEST_{save_filename}"
    full_path = os.path.join(save_folder_path, save_filename)
    llm_output.to_csv(full_path, index=False)
    print(f"Synthetic Data Saved to {full_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run SecureGPT Bot')
    parser.add_argument('test', type=int, nargs='?', help='Start testing environment', default=False)
    parser.add_argument('test_sample_size', type=int, nargs='?', help='', default=5)
    parser.add_argument('inference_prompt_data_path', type=int, nargs='?', help='')
    parser.add_argument('backup_data_path', type=int, nargs='?', help='', default=None)
    parser.add_argument('disclaimer_statement', type=int, nargs='?', help='', default=None)
    parser.add_argument('min_output_word_count', type=int, nargs='?', help='', default=40)
    parser.add_argument('terms_to_avoid', type=int, nargs='?', help='python list', default=["As an AI language model", "As a language model", "As a language AI model"])
    parser.add_argument('save_filename', type=int, nargs='?', help='', default="gpt-4_{timestamp}_{prompt_filename}")
    parser.add_argument('save_folder_path', type=int, nargs='?', help='', default="~/Downloads")
    parser.add_argument('max_chat_dialogs', type=int, nargs='?', help='', default=5)
    parser.add_argument('input_text_lag_time', type=int, nargs='?', help='', default=15)
    parser.add_argument('generation_sleep_timer', type=int, nargs='?', help='', default=50)
    parser.add_argument('max_data_loading_retries', type=int, nargs='?', help='', default=10)
    parser.add_argument('retry_data_loading_wait_time', type=int, nargs='?', help='', default=5)
    parser.add_argument('website_email_input', type=int, nargs='?', help='', default=None)
    args = parser.parse_args()
    
    website_url = "https://securegpt.stanfordhealthcare.org/chat"
    run_auto_securegpt(
        test=args.test,
        test_sample_size=args.test_sample_size,
        inference_prompt_data_path=args.inference_prompt_data_path,
        backup_data_path=args.backup_data_path,
        disclaimer_statement=args.disclaimer_statement,
        min_output_word_count=args.min_output_word_count,
        terms_to_avoid=args.terms_to_avoid,
        save_filename=args.save_filename,
        save_folder_path=args.save_folder_path,
        max_chat_dialogs=args.max_chat_dialogs,
        input_text_lag_time=args.input_text_lag_time,
        generation_sleep_timer=args.generation_sleep_timer,
        max_data_loading_retries=args.max_data_loading_retries,
        retry_data_loading_wait_time=args.retry_data_loading_wait_time,
        website_email_input=args.website_email_input,
        website_url=website_url,
        )