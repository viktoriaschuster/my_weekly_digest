#!/usr/bin/env python3

import sys
import os
import logging
import datetime
import json
from pathlib import Path

# Add the src directory to the Python path
base_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(base_dir / "src"))

# Import the scrapers
from scrapers import arxiv_scraper, biorxiv_scraper, blog_scraper

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("scraper_test")

def main():
    """Test all scrapers and show results."""
    logger.info("Starting scraper test...")
    
    # Get date range for the past week
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=14)  # Try 2 weeks for more results
    
    logger.info(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    # Test arXiv scraper
    logger.info("Testing arXiv scraper...")
    arxiv_papers = arxiv_scraper.scrape_arxiv(start_date, end_date, max_results=10)
    logger.info(f"Found {len(arxiv_papers)} papers on arXiv")
    
    # Test bioRxiv scraper
    logger.info("Testing bioRxiv scraper...")
    biorxiv_papers = biorxiv_scraper.scrape_biorxiv(start_date, end_date, max_papers=10)
    logger.info(f"Found {len(biorxiv_papers)} papers on bioRxiv")
    
    # Test blog scraper
    logger.info("Testing blog scraper...")
    blog_entries = blog_scraper.scrape_blogs(start_date, end_date, max_entries=10)
    logger.info(f"Found {len(blog_entries)} blog entries")
    
    # Combine results
    all_content = arxiv_papers + biorxiv_papers + blog_entries
    logger.info(f"Total content found: {len(all_content)}")
    
    # Display sample results
    if arxiv_papers:
        logger.info(f"Sample arXiv paper: {arxiv_papers[0]['title']}")
    if biorxiv_papers:
        logger.info(f"Sample bioRxiv paper: {biorxiv_papers[0]['title']}")
    if blog_entries:
        logger.info(f"Sample blog entry: {blog_entries[0]['title']}")
    
    # Save combined results
    test_output_dir = base_dir / "data" / "test"
    os.makedirs(test_output_dir, exist_ok=True)
    
    output_file = test_output_dir / f"scraper_test_{end_date.strftime('%Y%m%d')}.json"
    with open(output_file, 'w') as f:
        json.dump(all_content, f, indent=2)
    
    logger.info(f"Test results saved to {output_file}")
    logger.info("Scraper test completed")

if __name__ == "__main__":
    main()