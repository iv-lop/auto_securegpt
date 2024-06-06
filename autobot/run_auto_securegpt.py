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
from helper_functions import (
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
        input_data_path,
        backup_data_path,
        disclaimer_statement,
        min_output_word_count,
        prompt_column_name,
        output_column_name,
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

    print(f"Formatting terms to avoid")
    terms_to_avoid = [term.strip() for term in args.terms_to_avoid.split(',') if term.strip()]
    print(f"Formatted terms to avoid:\n{terms_to_avoid}")

    print(f"\nExpanding Paths")
    prompt_filename = os.path.basename(input_data_path)
    input_data_path = os.path.expanduser(input_data_path)
    save_filename = save_filename.format(timestamp=llm_inference_timestamp, prompt_filename=prompt_filename)
    save_folder_path = os.path.expanduser(save_folder_path)
    print(f"Paths Expanded")

    print(f"\nLoading Data")
    input_data_df = pd.read_csv(input_data_path)
    if 'prompt_id' not in input_data_df.columns:
        input_data_df['prompt_id'] = input_data_df.index + 1
    print(f"Data Loaded")
    if backup_data_path is not None:
        print(f"\nLoading Backup Data")
        saved_backup_data = pd.read_csv(os.path.expanduser(backup_data_path))
        print(f"Removing Already Processed Data from Inference Prompt Data")
        input_data_df = input_data_df[~input_data_df['prompt_id'].isin(saved_backup_data['prompt_id'])].reset_index(drop=True)
    print(f"Data Loaded:\n{input_data_df}")

    print("\nSetup the Chrome WebDriver")
    if website_email_input is not None:
        pyperclip.copy(website_email_input)
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    print("Going to Website")
    driver.get(website_url)
    # Loop until the user inputs '1'
    user_input = ""
    while user_input != "1":
        user_input = input("\nPlease set-up the GPT environment by fully logging into SecureGPT and opening a new chat window. Select your preferred GPT (GPT-3.5 vs. GPT-4) and conversation style (Creative vs. Balanced vs. Precise). Press 'Enter' after typing '1' to proceed: ")
        if user_input == "1":
            print("Proceeding...")
        else:
            print("Incorrect input. Please type '1' to proceed: ")

    if test:
        print(f"\n\n***Loading Testing Environment***\n\n")
        input_data_df = input_data_df.head(test_sample_size)

    print(f"\nGenerating Data")
    original_column_names = input_data_df.columns.tolist()
    llm_output = pd.DataFrame(columns=original_column_names + [output_column_name])
    global_iteration = 0
    total_iterations = len(input_data_df)

    for index, row in input_data_df.iterrows():
        try:
            global_iteration += 1
            print(f"\n\nProcessing iteration {global_iteration}/{total_iterations}")
            latest_output, latest_send = send_data_and_get_output(
                driver=driver,
                prompt=row[prompt_column_name], 
                input_text_lag_time=input_text_lag_time,
                generation_sleep_timer=generation_sleep_timer,
                max_data_loading_retries=max_data_loading_retries,
                retry_data_loading_wait_time=retry_data_loading_wait_time,
                max_chat_dialogs=max_chat_dialogs,
                global_iteration=global_iteration,
                total_iterations=total_iterations,
                llm_output=llm_output,
                prompt_column_name=prompt_column_name,
                output_column_name=output_column_name,
                disclaimer_statement=disclaimer_statement,
                terms_to_avoid=terms_to_avoid,
                min_output_word_count=min_output_word_count,
                )

            current_data = {col: row[col] for col in input_data_df.columns}
            current_data[prompt_column_name] = latest_send
            current_data[output_column_name] = latest_output
            llm_output = pd.concat([llm_output, pd.DataFrame([current_data])], ignore_index=True)
        except Exception as e:
            print("An error occurred. Saving progress...")
            error_timestamp = datetime.now(pytz.utc).astimezone(pytz.timezone('US/Pacific')).strftime('%Y-%m-%d_%H:%M:%S')
            save_progress_filename = f"llm_output_backup_{error_timestamp}.csv"
            full_path = os.path.join(save_folder_path, save_progress_filename)
            llm_output.to_csv(full_path, index=False)
            print(f"Progress saved to {full_path}")
            raise e
    print(f"Data Generated")

    print(f"\nQuitting Chrome WebDriver")
    driver.quit()
    print(f"Chrome Driver Quit")

    print(f"\nSaving Data")
    if test:
        save_filename = f"TEST_{save_filename}"
    full_path = os.path.join(save_folder_path, save_filename)
    llm_output.to_csv(full_path, index=False)
    print(f"Data Saved to {full_path}")

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Run SecureGPT Bot')
    parser.add_argument('--test', action='store_true', help='Start testing environment')
    parser.add_argument('--test_sample_size', type=int, nargs='?', help='Define the sample size for testing', default=5)
    parser.add_argument('--input_data_path', type=str, nargs='?', help='Path to the input data file')
    parser.add_argument('--backup_data_path', type=str, nargs='?', help='Path for backup data', default=None)
    parser.add_argument('--disclaimer_statement', type=str, nargs='?', help='Disclaimer statement to be displayed', default="I am going to give you a prompt. You don't need a file to perform the task. Just read the prompt and perform the task and don't give me any extra explanation.")
    parser.add_argument('--min_output_word_count', type=int, nargs='?', help='Minimum word count for the output', default=40)
    parser.add_argument('--prompt_column_name', type=str, nargs='?', help='Column name for the prompts')
    parser.add_argument('--output_column_name', type=str, nargs='?', help='Column name for the outputs')
    parser.add_argument('--terms_to_avoid', type=str, help='List of terms to avoid', default= 'As an AI language model, As a language model, As a language AI model')
    parser.add_argument('--save_filename', type=str, nargs='?', help='Template for output file names', default="gpt-4_{timestamp}_{prompt_filename}")
    parser.add_argument('--save_folder_path', type=str, nargs='?', help='Path to save output files', default="~/Downloads")
    parser.add_argument('--max_chat_dialogs', type=int, nargs='?', help='Maximum number of chat dialogs to process', default=5)
    parser.add_argument('--input_text_lag_time', type=int, nargs='?', help='Lag time before processing each text input', default=15)
    parser.add_argument('--generation_sleep_timer', type=int, nargs='?', help='Sleep timer between generations', default=50)
    parser.add_argument('--max_data_loading_retries', type=int, nargs='?', help='Maximum retries for data loading', default=10)
    parser.add_argument('--retry_data_loading_wait_time', type=int, nargs='?', help='Wait time between data loading retries', default=5)
    parser.add_argument('--website_email_input', type=str, nargs='?', help='Email input for website', default=None)
    args = parser.parse_args()
    
    website_url = "https://securegpt.stanfordhealthcare.org/chat"
    run_auto_securegpt(
        test=args.test,
        test_sample_size=args.test_sample_size,
        input_data_path=args.input_data_path,
        backup_data_path=args.backup_data_path,
        disclaimer_statement=args.disclaimer_statement,
        min_output_word_count=args.min_output_word_count,
        prompt_column_name=args.prompt_column_name,
        output_column_name=args.output_column_name,
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
