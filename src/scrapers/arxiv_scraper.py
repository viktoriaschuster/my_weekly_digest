import arxiv
import logging
import json
import os
import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

def load_config(config_path):
    """Load configuration from a JSON file."""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading config from {config_path}: {e}")
        return {}

def get_search_query(keywords):
    """Construct a search query string from keywords."""
    ml_terms = keywords.get('ml_terms', [])
    biology_terms = keywords.get('biology_terms', [])
    exclude_terms = keywords.get('exclude_terms', [])
    
    # Combine the ML and biology terms with OR
    positive_terms = " OR ".join(ml_terms + biology_terms)
    
    # Add excluded terms with AND NOT
    negative_terms = " ".join([f"AND NOT {term}" for term in exclude_terms]) if exclude_terms else ""
    
    return f"({positive_terms}) {negative_terms}"

def format_paper(paper):
    """Format an arXiv paper into a standardized dictionary."""
    return {
        'title': paper.title,
        'authors': ", ".join([author.name for author in paper.authors]),
        'abstract': paper.summary,
        'url': paper.entry_id,
        'pdf_url': paper.pdf_url,
        'published': paper.published.isoformat(),
        'updated': paper.updated.isoformat(),
        'categories': paper.categories,
        'source': 'arxiv'
    }

def scrape_arxiv(start_date, end_date, max_results=50):
    """
    Scrape arXiv for papers published between start_date and end_date.
    """
    try:
        # Load keywords from config
        base_dir = Path(__file__).resolve().parents[2]  # Go back two directories to root
        keywords_path = base_dir / "config" / "keywords.json"
        
        # Print debug info
        logger.info(f"Looking for config at: {keywords_path}")
        
        keywords = load_config(keywords_path)
        
        # Debug: Use simpler search for testing
        search_query = get_search_query(keywords)
        logger.info(f"Using search query: {search_query}")
        
        # Use a simpler date filter - just get recent papers  
        # Instead of using the date filter which can be tricky, just sort by recent
        client = arxiv.Client(page_size=100, delay_seconds=3)
        
        search = arxiv.Search(
            query=search_query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate
        )
        
        # Execute the search
        results = list(client.results(search))
        logger.info(f"Found {len(results)} papers on arXiv")
        
        # Now filter by date after getting results
        filtered_results = []
        for paper in results:
            published_date = paper.published.replace(tzinfo=None)  # Remove timezone for comparison
            if start_date <= published_date <= end_date:
                filtered_results.append(paper)
        
        logger.info(f"After date filtering: {len(filtered_results)} papers")
        
        # Format the results
        papers = [format_paper(paper) for paper in filtered_results]
        
        raw_data_dir = base_dir / "data" / "raw"
        # Check if 'raw' exists and is not a directory
        if raw_data_dir.exists() and not raw_data_dir.is_dir():
            # Rename the existing file
            os.rename(raw_data_dir, str(raw_data_dir) + '.old')
            logger.warning(f"Found a file named 'raw' instead of a directory. Renamed to 'raw.old'")
        
        os.makedirs(raw_data_dir, exist_ok=True)
        
        output_file = raw_data_dir / f"arxiv_{start_date.strftime('%Y%m%d')}.json"
        with open(output_file, 'w') as f:
            json.dump(papers, f, indent=2)
        logger.info(f"Saved {len(papers)} papers to {output_file}")
            
        return papers
    
    except Exception as e:
        logger.error(f"Error scraping arXiv: {e}")
        return []

if __name__ == "__main__":
    # Simple test: scrape papers from the last week
    logging.basicConfig(level=logging.INFO)
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=7)
    papers = scrape_arxiv(start_date, end_date)
    print(f"Found {len(papers)} papers")
    
    # Print the first paper's title
    if papers:
        print(f"First paper: {papers[0]['title']}")