import requests
import logging
import json
import os
import datetime
from pathlib import Path
import time

logger = logging.getLogger(__name__)

def load_config(config_path):
    """Load configuration from a JSON file."""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading config from {config_path}: {e}")
        return {}

def keyword_matches(text, keywords):
    """Check if any keywords match the given text."""
    ml_terms = keywords.get('ml_terms', [])
    biology_terms = keywords.get('biology_terms', [])
    all_terms = ml_terms + biology_terms
    
    # Check if any positive terms match
    text_lower = text.lower()
    return any(term.lower() in text_lower for term in all_terms)

def format_paper(paper_data):
    """Format bioRxiv paper data into a standardized dictionary."""
    return {
        'title': paper_data.get('title', ''),
        'authors': paper_data.get('authors', ''),
        'abstract': paper_data.get('abstract', ''),
        'url': paper_data.get('url', ''),
        'pdf_url': paper_data.get('pdf_url', ''),
        'published': paper_data.get('published', ''),
        'doi': paper_data.get('doi', ''),
        'source': 'biorxiv'
    }

def fetch_biorxiv_papers(api_url, start_str, end_str, max_papers=50):
    """Helper function to fetch papers from bioRxiv API."""
    papers = []
    cursor = 0
    
    while len(papers) < max_papers:
        # The correct endpoint for bioRxiv API - using details with direct JSON output
        full_url = f"{api_url}/{start_str}/{end_str}/{cursor}"
        logger.info(f"Requesting: {full_url}")
        
        try:
            response = requests.get(full_url)
            response.raise_for_status()  # Raise exception on 4xx/5xx responses
            
            data = response.json()
            
            # Debug response structure
            if cursor == 0:
                logger.info(f"Response keys: {list(data.keys())}")
                
            # Check messages from API
            if 'messages' in data:
                logger.info(f"API message: {data['messages']}")
                
            collection = data.get('collection', [])
            logger.info(f"Found {len(collection)} papers in this batch")
            
            if not collection:
                logger.info("No more papers available")
                break
                
            for paper in collection:
                # Print first paper details for debugging
                if len(papers) == 0 and cursor == 0:
                    logger.info(f"Example paper: {json.dumps(paper, indent=2)[:200]}...")
                
                paper_data = {
                    'title': paper.get('title', ''),
                    'authors': paper.get('authors', ''),
                    'abstract': paper.get('abstract', ''),
                    'url': f"https://www.biorxiv.org/content/{paper.get('doi', '')}v{paper.get('version', '1')}",
                    'pdf_url': f"https://www.biorxiv.org/content/{paper.get('doi', '')}v{paper.get('version', '1')}.full.pdf",
                    'published': paper.get('date', ''),
                    'doi': paper.get('doi', ''),
                    'source': 'biorxiv'
                }
                papers.append(format_paper(paper_data))
                
                if len(papers) >= max_papers:
                    break
                    
            cursor += len(collection)
            time.sleep(1)  # Respect rate limits
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            break
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            logger.error(f"Response content: {response.text[:200]}...")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            break
    
    return papers

def scrape_biorxiv(start_date, end_date, max_papers=50):
    """Scrape bioRxiv for papers published between start_date and end_date."""
    try:
        # Define base_dir here explicitly
        base_dir = Path(__file__).resolve().parents[2]
        
        # Use wider date range for testing - bioRxiv may not have many recent papers
        # that match machine learning terms
        extended_start = start_date - datetime.timedelta(days=90)  # Use 90 days instead of 30
        start_str = extended_start.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        logger.info(f"Using date range for bioRxiv: {start_str} to {end_str}")
        
        # Load keywords for filtering
        keywords_path = base_dir / "config" / "keywords.json"
        keywords = load_config(keywords_path)
        
        # Fetch papers from the API
        api_url = "https://api.biorxiv.org/details/biorxiv"
        papers = fetch_biorxiv_papers(api_url, start_str, end_str, max_papers)
        
        # Filter papers by keywords if needed
        if keywords and len(papers) > max_papers:
            filtered_papers = []
            for paper in papers:
                combined_text = f"{paper['title']} {paper['abstract']}"
                if keyword_matches(combined_text, keywords):
                    filtered_papers.append(paper)
            
            logger.info(f"Filtered from {len(papers)} to {len(filtered_papers)} papers based on keywords")
            papers = filtered_papers[:max_papers]
        
        # Save raw data
        raw_data_dir = base_dir / "data" / "raw"
        os.makedirs(raw_data_dir, exist_ok=True)
        output_file = raw_data_dir / f"biorxiv_{start_date.strftime('%Y%m%d')}.json"
        
        with open(output_file, 'w') as f:
            json.dump(papers, f, indent=2)
            
        logger.info(f"Saved {len(papers)} papers to {output_file}")
        return papers
        
    except Exception as e:
        logger.error(f"Error in scrape_biorxiv: {e}")
        return []

if __name__ == "__main__":
    # Test directly
    logging.basicConfig(level=logging.INFO)
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=7)
    papers = scrape_biorxiv(start_date, end_date, max_papers=10)
    print(f"Found {len(papers)} papers")
    
    # Display the first paper if available
    if papers:
        print(f"First paper: {papers[0]['title']}")