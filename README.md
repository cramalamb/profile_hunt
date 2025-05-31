# LinkedIn Scraper

A drop-in Python/Selenium script to scrape people by **keyword** or 

# env setup - jake version
## cd /Users/jake/Desktop/coding/LinkedIn/breakline
## cp .env.example .env
# then open .env in your editor and fill in LINKEDIN_USER and LINKEDIN_PASS

# create and activate
## python3 -m venv venv
## source venv/bin/activate

# install dependents
## pip install -r requirements.txt


**company** (current & past).

## Setup

1. `git clone <repo>`
2. `cd linkedin_scraper`
3. `cp .env.example .env` & fill in your LinkedIn creds
4. `python3 -m venv venv && source venv/bin/activate`
5. `pip install -r requirements.txt`
6. Download matching ChromeDriver & put it in your PATH

## Usage

```bash
# Keyword mode (always 10 pages):
python scraper.py -q "machine learning" --mode keyword

# Company mode (uses -p pages, default 5):
python scraper.py -q "Acme Corp" --mode company -p 3 --headless
