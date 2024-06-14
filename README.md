# Auto-SecureGPT

Auto-SecureGPT is a library that helps automate Stanford's SecureGPT instance for research related tasks.

## Installation
Auto-SecureGPT can be installed with `pip`:
```bash
git clone https://github.com/iv-lop/auto_securegpt.git
cd auto_securegpt
conda create -n auto_sgpt python=3.10.13
conda activate auto_sgpt
pip install -e .
```

## Instructions
Example usage:
```
python autobot/run_auto_securegpt.py \
    --test \
    --test_sample_size 3 \
    --input_data_path "~/llm_data/my_data.csv" \
    --prompt_column_name "my_prompt" \
    --output_column_name "gpt4_output" \
    --terms_to_avoid 'As an AI language model, As a language model, As a language AI model' \
    --disclaimer_statement "I am going to give you a prompt. You don't need a file to perform the task. Just read the prompt and perform the task and don't give me any extra explanation." \
    --min_output_word_count 40 \
    --save_filename "gpt-4_{timestamp}_{prompt_filename}" \
    --save_folder_path "~/llm_data/gpt_outputs" \
    --max_chat_dialogs 5 \
    --input_text_lag_time 15 \
    --generation_sleep_timer 50 \
    --max_data_loading_retries 10 \
    --retry_data_loading_wait_time 5 \
    --website_email_input "ivlopez@stanford.edu"
```

Setting up the initial GPT environment using the SecureGPT UI requires your input. Make sure your screen looks like this before pressing '1' during the Chrome WebDriver setup stage of this script:
<p align="center">
  <img src="figures/chrome_setup.png" height="300">
</p>

Input data should be a CSV file where every row is a prompt sent to SecureGPT:
| note_id | my_prompt                                       |
|---------|----------------------------------------------------|
| 1       | polish this text: "The patient was hospitalized …  |
| 2       | polish this text: "The patient was hospitalized for … |
| 3       | polish this text: "The patient was admitted after … |

## Citing Auto-SecureGPT
If you use this software in your research, please cite it using the following DOI: [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.11649165.svg)](https://doi.org/10.5281/zenodo.11649165)

APA Style: 
```
Lopez, I. (2024). Auto-SecureGPT (Version 0.1.0) [Software]. https://doi.org/10.5281/zenodo.11649165
```

BibTeX Entry:
```
@software{auto_securegpt,
  author       = {Ivan Lopez},
  title        = {Auto-SecureGPT},
  month        = jun,
  year         = 2024,
  version      = {0.1.0},
  publisher    = {Zenodo},
  doi          = {10.5281/zenodo.11649165},
  url          = {https://github.com/iv-lop/auto_securegpt}
}
```