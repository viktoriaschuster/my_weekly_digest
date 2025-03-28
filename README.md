# Research Digest

This project is designed to automate the process of scraping, filtering, analyzing, and generating reports on recent research works in the fields of machine learning, particularly focusing on mechanistic interpretability (mechinterp). 

## Project Structure

- **src/**: Contains the main source code for the project.
  - **scrapers/**: Modules for scraping data from various sources.
    - `arxiv_scraper.py`: Functions to scrape new entries from arXiv based on specified keywords.
    - `biorxiv_scraper.py`: Functions to scrape new entries from bioRxiv based on specified keywords.
    - `blog_scraper.py`: Functions to scrape relevant machine learning blogs for new entries based on specified keywords.
  - **filtering/**: Modules for filtering scraped entries.
    - `keyword_filter.py`: Functions to filter scraped entries based on specified keywords.
  - **analysis/**: Modules for analyzing the scraped entries.
    - `llm_processor.py`: Functions to process the scraped entries using a local LLM, summarizing the works and assessing their quality and novelty.
  - **output/**: Modules for generating output from the processed data.
    - `blog_generator.py`: Functions to generate a blog post from the summarized entries.
    - `pdf_generator.py`: Functions to generate a PDF from the summarized entries.
  - **utils/**: Utility functions that assist with various tasks throughout the project.
    - `helpers.py`: Contains utility functions.
  - `main.py`: The entry point for the application, orchestrating the scraping, filtering, analysis, and output generation processes.

- **config/**: Configuration files for the project.
  - `keywords.json`: Contains a list of keywords used for filtering relevant works.
  - `sources.json`: Contains the URLs or identifiers for the sources to scrape (arXiv, bioRxiv, blogs).
  - `llm_config.json`: Contains configuration settings for the local LLM, such as model parameters and paths.

- **data/**: Directories for storing raw and processed data.
  - `raw/`: Intended to store raw scraped data.
  - `processed/`: Intended to store processed data after filtering and analysis.

- **output/**: Directories for storing generated outputs.
  - `blog/`: Intended to store generated blog posts.
  - `pdf/`: Intended to store generated PDF files.

- **scripts/**: Contains automation scripts.
  - `weekly_run.sh`: A shell script that automates the weekly scraping and processing tasks.

- **requirements.txt**: Lists the dependencies required for the project.

- **.gitignore**: Specifies files and directories that should be ignored by version control.

## Setup Instructions

1. Clone the repository to your local machine.
2. Set up the conda environment:
   ```bash
   conda env create -f environment.yml
   conda activate research-digest
3. Install the required dependencies using:
   ```
   pip install -r requirements.txt
   ```
4. Configure the `config/keywords.json`, `config/sources.json`, and `config/llm_config.json` files according to your needs.
5. Run the `scripts/exec.sh` script to start the weekly scraping and processing tasks.

## Usage

The project will scrape new research entries every Monday based on the specified keywords, summarize them using a local LLM, and generate a blog post and PDF report that can be hosted on your website or printed.

## Contribution

Contributions are welcome! Please feel free to submit a pull request or open an issue for any suggestions or improvements.