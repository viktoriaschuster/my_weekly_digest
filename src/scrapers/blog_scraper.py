import requests
from bs4 import BeautifulSoup
import logging
import json
import os
import datetime
import time
from pathlib import Path
import re
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

def load_config(config_path):
    """Load configuration from a JSON file."""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading config from {config_path}: {e}")
        return {}

def keyword_matches(entry, keywords):
    """Check if entry matches any keywords."""
    if not keywords:
        return True
        
    ml_terms = keywords.get('ml_terms', [])
    biology_terms = keywords.get('biology_terms', [])
    exclude_terms = keywords.get('exclude_terms', [])
    
    all_terms = ml_terms + biology_terms
    
    # Combine all text fields
    text = f"{entry['title']} {entry['abstract']} {entry['authors']}"
    text_lower = text.lower()
    
    # Check if any positive terms match
    matches_positive = any(term.lower() in text_lower for term in all_terms)
    
    # Check if any exclude terms match
    matches_exclude = any(term.lower() in text_lower for term in exclude_terms)
    
    return matches_positive and not matches_exclude

def is_recent_publication(entry, start_date, end_date):
    """Check if an entry was published within the given date range."""

    try:
        published = entry.get('published', '')
        if not published:
            return False  # No date, can't determine if recent
            
        # Check for month-year format patterns first
        month_year_match = re.match(r'([A-Za-z]+)\s+(\d{4})$', published) or re.match(r'(\d{4})-(\d{1,2})$', published)
        if month_year_match:
            # This is a month-year format (e.g., "March 2025" or "2025-03")
            if re.match(r'([A-Za-z]+)\s+(\d{4})$', published):
                # Convert month name to number
                month_name, year_str = month_year_match.groups()
                try:
                    temp_date = datetime.datetime.strptime(f"{month_name} 1, {year_str}", "%B 1, %Y")
                    entry_month = temp_date.month
                    entry_year = temp_date.year
                except ValueError:
                    # Try abbreviated month name
                    try:
                        temp_date = datetime.datetime.strptime(f"{month_name} 1, {year_str}", "%b 1, %Y")
                        entry_month = temp_date.month
                        entry_year = temp_date.year
                    except ValueError:
                        logger.warning(f"Could not parse month name: {month_name}")
                        return False
            else:
                # Format is YYYY-MM
                year_str, month_str = month_year_match.groups()
                entry_year = int(year_str)
                entry_month = int(month_str)
            
            # Check if this month-year is the current month or previous month relative to end_date
            end_year = end_date.year
            end_month = end_date.month
            
            # Create a range of acceptable months (previous, current, next)
            if end_month == 1:
                acceptable_months = [(end_year-1, 12), (end_year, 1), (end_year, 2)]
            elif end_month == 12:
                acceptable_months = [(end_year, 11), (end_year, 12), (end_year+1, 1)]
            else:
                acceptable_months = [(end_year, end_month-1), (end_year, end_month), (end_year, end_month+1)]
            
            # Include if it's within the acceptable range
            if (entry_year, entry_month) in acceptable_months:
                return True
            
            # Also check against start_date (for older papers)
            start_year_month = (start_date.year, start_date.month)
            end_year_month = (end_date.year, end_date.month)
            entry_year_month = (entry_year, entry_month)

            return start_year_month <= entry_year_month <= end_year_month
            
        # For specific dates (with day information), use the existing logic
        date_formats = [
            '%Y-%m-%d',            # 2025-03-01
            '%B %d, %Y',           # March 1, 2025
            '%d %B %Y',            # 1 March 2025
            '%Y/%m/%d',            # 2025/03/01
        ]
        
        parsed_date = None
        for fmt in date_formats:
            try:
                parsed_date = datetime.datetime.strptime(published, fmt)
                break
            except ValueError:
                continue
                
        if not parsed_date:
            # Try to extract year, month, day from any format
            date_match = re.search(r'(\d{4})[-/]?(\d{1,2})[-/]?(\d{1,2})', published)
            if date_match:
                year, month, day = date_match.groups()
                try:
                    parsed_date = datetime.datetime(int(year), int(month), int(day))
                except ValueError:
                    # Handle invalid dates
                    logger.warning(f"Invalid date components: {year}-{month}-{day}")
                    return False
        
        # If we have a specific date, do the direct comparison
        if parsed_date:
            return start_date <= parsed_date <= end_date
            
        # If we couldn't parse the date in any way
        logger.warning(f"Could not parse date: {published}")
        return False  # Include by default if date can't be parsed
        
    except Exception as e:
        logger.error(f"Error checking publication date: {e}")
        return False  # Include by default if there's an error

def scrape_anthropic_research(url):
    """Scrape Anthropic news page for recent announcements and updates."""
    entries = []
    try:
        logger.info(f"Scraping Anthropic news: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        
        response = requests.get(url, headers=headers, timeout=60)
        if response.status_code != 200:
            logger.error(f"Failed to access Anthropic news: {response.status_code}")
            return entries
            
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Specifically target PostCard elements based on the provided structure
        post_cards = soup.select('a[class*="PostCard_post-card"]') or soup.select('a[class*="post-card"]')
        
        logger.info(f"Found {len(post_cards)} post cards on Anthropic news page")
        
        # Process each post card
        seen_titles = set()
        for card in post_cards:
            # Extract URL from the card's href attribute
            url_path = card.get('href')
            news_url = urljoin("https://www.anthropic.com", url_path) if url_path else ""
            
            # Find title in the heading element
            title_elem = card.select_one('[class*="post-heading"]') or card.find(['h2', 'h3', 'h4', 'h5'])
            if not title_elem:
                continue
                
            title = title_elem.text.strip()
            
            # Skip duplicates or very short titles
            if title in seen_titles or len(title) < 10:
                continue
                
            seen_titles.add(title)
            
            # Find date in the timestamp element
            date = datetime.datetime.now().strftime('%Y-%m-%d')  # Default to today
            date_elem = card.select_one('[class*="post-date"]') or card.select_one('[class*="timestamp"]')
            
            if date_elem:
                date_text = date_elem.text.strip()
                if date_text:
                    # Try to parse the date - common format is "Mar 27, 2025"
                    try:
                        date_formats = ['%b %d, %Y', '%B %d, %Y', '%Y-%m-%d', '%m/%d/%Y']
                        for fmt in date_formats:
                            try:
                                parsed_date = datetime.datetime.strptime(date_text, fmt)
                                date = parsed_date.strftime('%Y-%m-%d')
                                break
                            except ValueError:
                                continue
                    except Exception as e:
                        logger.warning(f"Could not parse date '{date_text}': {e}")
            
            # Find category tags if available
            category = ""
            category_elem = card.select_one('[class*="post-category"]')
            if category_elem:
                category = category_elem.text.strip()
            
            # Add the entry
            entries.append({
                'title': title,
                'url': news_url,
                'published': date,
                'abstract': category,  # Use category as abstract if no other content is available
                'authors': "Anthropic",
                'source': 'anthropic_news'
            })
            #logger.info(f"Found Anthropic news: {title}")
        
        # If the specific approach didn't find any entries, fall back to the general approach
        if not entries:
            logger.info("No entries found with specific selector, trying fallback method")
            
            # Look for any elements with "post" or "card" in their class names
            fallback_items = soup.select('[class*="post"], [class*="card"]')
            
            for item in fallback_items:
                # Skip if already processed
                title_elem = item.find(['h2', 'h3', 'h4', 'h5'])
                if not title_elem:
                    continue
                    
                title = title_elem.text.strip()
                
                if title in seen_titles or len(title) < 10:
                    continue
                    
                seen_titles.add(title)
                
                # Find URL - either from the item itself if it's a link or from any link inside
                news_url = ""
                if item.name == 'a':
                    url_path = item.get('href')
                    news_url = urljoin("https://www.anthropic.com", url_path) if url_path else ""
                else:
                    link = item.find('a')
                    if link:
                        url_path = link.get('href')
                        news_url = urljoin("https://www.anthropic.com", url_path) if url_path else ""
                
                # Add the entry
                entries.append({
                    'title': title,
                    'url': news_url,
                    'published': datetime.datetime.now().strftime('%Y-%m-%d'),
                    'abstract': "",
                    'authors': "Anthropic",
                    'source': 'anthropic_news'
                })
                #logger.info(f"Found Anthropic news (fallback): {title}")
        
        logger.info(f"Total Anthropic news items found: {len(entries)}")
        return entries
        
    except Exception as e:
        logger.error(f"Error scraping Anthropic news: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return entries

def scrape_circuits_research(url):
    """Scrape Anthropic's Transformer Circuits research blog with specific structure."""
    entries = []
    seen_titles = set()  # Track seen titles to avoid duplicates
    
    try:
        logger.info(f"Scraping Transformer Circuits: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=60)
        if response.status_code != 200:
            logger.error(f"Failed to access Transformer Circuits: {response.status_code}")
            return entries
            
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Specifically look for elements containing "paper" in their class
        paper_elements = []
        for element in soup.find_all(class_=lambda c: c and "paper" in c.lower()):
            paper_elements.append(element)
            
        logger.info(f"Found {len(paper_elements)} paper elements with 'paper' in class name")
        
        # Process each paper element
        for paper in paper_elements:
            # Find title
            title_elem = paper.find(['h2', 'h3', 'h4']) or paper.select_one('.title, .post-title')
            if not title_elem:
                continue
                
            title = title_elem.text.strip()
            
            # Skip duplicates
            if title in seen_titles:
                continue
            
            # Skip navigation elements
            if title in ['Articles', 'Publications', 'Research'] or len(title) < 15:
                continue
                
            seen_titles.add(title)
            
            # Look for date - first try the previous sibling with class "date"
            date = ""
            date_elem = None
            
            # Try to find a div with class "date" before this paper
            prev_elem = paper.find_previous_sibling(class_="date")
            if prev_elem:
                date_elem = prev_elem

            # If not found, try to find date within the paper element
            if not date_elem:
                date_elem = paper.select_one('.date, .post-date') or paper.find('time')
            
            # If date element found, extract the date
            if date_elem:
                date = date_elem.text.strip()
            else:
                # Default to current date
                date = datetime.datetime.now().strftime('%Y-%m-%d')
            
            # Parse the date which might be in month/year format
            # If it's a simple "Month Year" format, convert it
            try:
                # Check if the date is in "Month Year" format like "March 2023"
                if re.match(r'[A-Za-z]+ \d{4}$', date):
                    # Convert to YYYY-MM-DD format with the last day of the month (but not further in the future than now)
                    parsed_date = datetime.datetime.strptime(date, '%B %Y')
                    date = parsed_date.strftime('%Y-%m-%d')
                    # make sure it is the last day of the month
                    last_day = (parsed_date + datetime.timedelta(days=31)).replace(day=1) - datetime.timedelta(days=1)
                    date = last_day.strftime('%Y-%m-%d')
                    # check if the date is in the future
                    if parsed_date > datetime.datetime.now():
                        date = datetime.datetime.now().strftime('%Y-%m-%d')
            except:
                # Keep original if parsing fails
                pass

            # check if date is in the future
            if date and (datetime.datetime.strptime(date, '%Y-%m-%d') > datetime.datetime.now()):
                date = datetime.datetime.now().strftime('%Y-%m-%d')
            
            # Extract URL - IMPROVED URL EXTRACTION FOR TRANSFORMER CIRCUITS
            url_path = ""
            
            # Check if paper itself is an anchor tag (common in transformer-circuits)
            if paper.name == 'a' and 'href' in paper.attrs:
                url_path = paper['href']
            # Then check if title_elem itself is a link
            elif title_elem.name == 'a':
                url_path = title_elem.get('href', '')
            # Then look for link inside title element
            elif title_elem.find('a'):
                url_path = title_elem.find('a').get('href', '')
            # Then look for any link in the paper element 
            else:
                for link in paper.find_all('a'):
                    href = link.get('href', '')
                    if href and not href.startswith('#') and not 'javascript:' in href:
                        url_path = href
                        break
            
            full_url = urljoin(url, url_path) if url_path else ""
            
            # Extract abstract/summary
            abstract = ""
            abstract_elem = paper.select_one('.description, .excerpt, .summary') or paper.find('p')
            if abstract_elem:
                abstract = abstract_elem.text.strip()
            
            # Add the entry
            entries.append({
                'title': title,
                'url': full_url,
                'published': date,
                'abstract': abstract,
                'authors': "Anthropic Transformer Circuits Team",
                'source': 'transformer_circuits'
            })
            logger.info(f"Found Transformer Circuits paper: {title} ({date}) - {full_url}")
        
        logger.info(f"Total Transformer Circuits entries found: {len(entries)}")
        return entries
        
    except Exception as e:
        logger.error(f"Error scraping Transformer Circuits: {e}")
        return entries

def scrape_openai_research(url):
    """Scrape OpenAI publications page with specific structure."""
    entries = []
    try:
        logger.info(f"Scraping OpenAI publications: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        
        response = requests.get(url, headers=headers, timeout=60)
        if response.status_code != 200:
            logger.error(f"Failed to access OpenAI publications: {response.status_code}")
            return entries
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find publication divs with the specific structure from the example
        publication_items = soup.select('div.py-md.border-primary-4') or soup.select('div[class*="border-primary-4"]')
        
        if not publication_items:
            # Fallback to more general selectors
            publication_items = soup.select('div[class*="py-md"]') or soup.select('div[class*="border-b"]')
        
        logger.info(f"Found {len(publication_items)} publication items")
        
        seen_titles = set()
        for item in publication_items:
            # Extract the title from the anchor element
            title_link = item.select_one('a[class*="text-primary"]') or item.select_one('a div.text-h5') or item.select_one('a div[class*="mb-2xs"]')
            
            if title_link:
                # If we found the anchor, look for the actual title text
                title_elem = title_link.select_one('div.text-h5') or title_link.select_one('div[class*="mb-2xs"]')
                if not title_elem:
                    title_elem = title_link  # Use the link itself if no specific title element
                
                title = title_elem.text.strip()
            else:
                # Try to find any heading-like element
                title_elem = item.find(['h2', 'h3', 'h4', 'h5']) or item.select_one('[class*="title"], [class*="heading"]')
                if not title_elem:
                    continue
                title = title_elem.text.strip()
            
            # Skip duplicates or very short titles
            if title in seen_titles or len(title) < 15:
                continue
                
            seen_titles.add(title)
            
            # Extract URL from the anchor
            url_path = ""
            link = item.find('a')
            if link and 'href' in link.attrs:
                url_path = link['href']
            full_url = urljoin("https://openai.com", url_path) if url_path else ""
            
            # Extract date from the time element
            date = datetime.datetime.now().strftime('%Y-%m-%d')  # Default to today
            time_elem = item.find('time')
            if time_elem:
                # First try datetime attribute
                if 'datetime' in time_elem.attrs:
                    date_text = time_elem['datetime']
                    # Handle ISO format with time (e.g., 2025-03-25T11:00)
                    if 'T' in date_text:
                        date_text = date_text.split('T')[0]
                    try:
                        parsed_date = datetime.datetime.strptime(date_text, '%Y-%m-%d')
                        date = parsed_date.strftime('%Y-%m-%d')
                    except ValueError:
                        # Use the visible text as fallback
                        date_text = time_elem.text.strip()
                else:
                    date_text = time_elem.text.strip()
                
                # Try to parse visible date text if needed
                if date == datetime.datetime.now().strftime('%Y-%m-%d') and date_text:
                    try:
                        date_formats = ['%b %d, %Y', '%B %d, %Y', '%Y-%m-%d']
                        for fmt in date_formats:
                            try:
                                parsed_date = datetime.datetime.strptime(date_text, fmt)
                                date = parsed_date.strftime('%Y-%m-%d')
                                break
                            except ValueError:
                                continue
                    except Exception as e:
                        logger.warning(f"Could not parse date '{date_text}': {e}")
            
            # Extract abstract - look for paragraph with specific class
            abstract = ""
            abstract_elem = item.select_one('p[class*="text-p2"]') or item.select_one('p[class*="line-clamp"]')
            if not abstract_elem:
                # Fallback to any paragraph
                abstract_elem = item.find('p')
            
            if abstract_elem:
                abstract = abstract_elem.text.strip()
            
            # Add entry
            entries.append({
                'title': title,
                'url': full_url,
                'published': date,
                'abstract': abstract,
                'authors': "OpenAI",
                'source': 'openai_publications'
            })
            logger.info(f"Found OpenAI publication: {title}")
        
        logger.info(f"Total OpenAI publications found: {len(entries)}")
        return entries
        
    except Exception as e:
        logger.error(f"Error scraping OpenAI publications: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return entries

def scrape_deepmind_research(url):
    """Scrape DeepMind publications page."""
    entries = []
    try:
        logger.info(f"Scraping DeepMind publications: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        
        response = requests.get(url, headers=headers, timeout=60)
        if response.status_code != 200:
            logger.error(f"Failed to access DeepMind publications: {response.status_code}")
            return entries
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Specifically target the list items containing publications based on the provided HTML structure
        publication_items = soup.select('li.list-compact__item')
        
        if not publication_items:
            # Fallback to more general selectors if the specific class isn't found
            publication_items = soup.select('li[class*="publication"], li[class*="item"]')
            
        logger.info(f"Found {len(publication_items)} DeepMind publication items")
        
        seen_titles = set()
        for item in publication_items:
            # Extract title from the specific link element
            title_link = item.select_one('a.list-compact__link, a[class*="link--publication"]')
            if not title_link:
                continue
                
            # Get the inner span if present, otherwise use the link text directly
            title_span = title_link.select_one('.list-compact__inner')
            title = title_span.text.strip() if title_span else title_link.text.strip()
            
            # Skip duplicates or very short titles
            if title in seen_titles or len(title) < 15:
                continue
                
            seen_titles.add(title)
            
            # Extract URL from the publication link
            url_path = title_link.get('href', '')
            full_url = urljoin("https://deepmind.google", url_path) if url_path else ""
            
            # Extract date from the time element
            date = datetime.datetime.now().strftime('%Y-%m-%d')  # Default to today
            time_elem = item.find('time')
            if time_elem:
                # First try datetime attribute
                if 'datetime' in time_elem.attrs:
                    date_text = time_elem['datetime']
                    try:
                        parsed_date = datetime.datetime.strptime(date_text, '%Y-%m-%d')
                        date = parsed_date.strftime('%Y-%m-%d')
                    except ValueError:
                        # Use the visible text as fallback
                        date_text = time_elem.text.strip()
                else:
                    # Get the long date format if available
                    date_span = time_elem.select_one('.list-compact__date--long')
                    if date_span:
                        date_text = date_span.text.strip()
                    else:
                        date_text = time_elem.text.strip()
                    
                    # Try to parse the date text
                    try:
                        date_formats = ['%d %B %Y', '%B %d, %Y', '%d %b %y']
                        for fmt in date_formats:
                            try:
                                parsed_date = datetime.datetime.strptime(date_text, fmt)
                                date = parsed_date.strftime('%Y-%m-%d')
                                break
                            except ValueError:
                                continue
                    except Exception as e:
                        logger.warning(f"Could not parse date '{date_text}': {e}")
            
            # check if date is in the future
            if date and (datetime.datetime.strptime(date, '%Y-%m-%d') > datetime.datetime.now()):
                date = datetime.datetime.now().strftime('%Y-%m-%d')
            
            # Extract authors - they are in the first .glue-caption element after the title
            authors = "DeepMind"
            dd_elements = item.find_all('dd', class_='glue-caption')
            if dd_elements and len(dd_elements) > 0:
                authors = dd_elements[0].text.strip()
            
            # Extract venue - it would be the second .glue-caption if available
            venue = ""
            if dd_elements and len(dd_elements) > 1:
                venue = dd_elements[1].text.strip()
            
            # Combine venue with title for abstract if available
            abstract = venue if venue else ""
            
            # Add entry
            entries.append({
                'title': title,
                'url': full_url,
                'published': date,
                'abstract': abstract,
                'authors': authors,
                'source': 'deepmind_research'
            })
            logger.info(f"Found DeepMind publication: {title}")
        
        # If we didn't find any publications with the specific structure, try a more general approach
        if not entries:
            logger.info("No publications found with specific structure, trying fallback method")
            
            # Try to find any articles or card elements
            fallback_items = soup.select('article, div[class*="card"], div[class*="publication"]')
            
            for item in fallback_items:
                # Extract title
                title_elem = item.find(['h2', 'h3', 'h4']) or item.select_one('[class*="title"]')
                if not title_elem:
                    continue
                    
                title = title_elem.text.strip()
                
                # Skip duplicates or very short titles
                if title in seen_titles or len(title) < 15:
                    continue
                    
                seen_titles.add(title)
                
                # Extract URL
                url_path = ""
                link = title_elem.find('a') or item.find('a')
                if link:
                    url_path = link.get('href', '')
                full_url = urljoin("https://deepmind.google", url_path) if url_path else ""
                
                # Extract date
                date = datetime.datetime.now().strftime('%Y-%m-%d')  # Default to today
                date_elem = item.find('time') or item.select_one('[class*="date"]')
                if date_elem:
                    date_text = date_elem.text.strip()
                    # Try to parse the date
                    try:
                        date_formats = ['%d %B %Y', '%B %d, %Y', '%Y-%m-%d']
                        for fmt in date_formats:
                            try:
                                parsed_date = datetime.datetime.strptime(date_text, fmt)
                                date = parsed_date.strftime('%Y-%m-%d')
                                break
                            except ValueError:
                                continue
                    except Exception as e:
                        logger.warning(f"Could not parse date '{date_text}': {e}")
                
                # Extract abstract
                abstract = ""
                abstract_elem = item.find('p') or item.select_one('[class*="description"], [class*="excerpt"]')
                if abstract_elem and abstract_elem != title_elem:
                    abstract = abstract_elem.text.strip()
                
                # Add entry using fallback
                entries.append({
                    'title': title,
                    'url': full_url,
                    'published': date,
                    'abstract': abstract,
                    'authors': "DeepMind",
                    'source': 'deepmind_research'
                })
                logger.info(f"Found DeepMind publication (fallback): {title}")
        
        logger.info(f"Total DeepMind publications found: {len(entries)}")
        return entries
        
    except Exception as e:
        logger.error(f"Error scraping DeepMind publications: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return entries

def scrape_blogs(start_date, end_date, max_entries=50, enable_keywords=False):
    """
    Scrape ML blogs for entries published between start_date and end_date.
    
    Args:
        start_date (datetime): Start date for the search
        end_date (datetime): End date for the search
        max_entries (int): Maximum number of entries to return
        
    Returns:
        list: List of dictionaries containing blog entries
    """
    try:
        # Define base_dir
        base_dir = Path(__file__).resolve().parents[2]
        
        # Load blog sources
        sources_path = base_dir / "config" / "sources.json"
        sources_config = load_config(sources_path)
        blog_sources = sources_config.get('blogs', [])
        
        if not blog_sources:
            logger.error("No blog sources found in config")
            return []
            
        logger.info(f"Found {len(blog_sources)} blog sources in config")
        
        # Load keywords
        keywords_path = base_dir / "config" / "keywords.json"
        keywords = load_config(keywords_path)
        
        # Scrape each blog
        all_entries = []
        for blog_info in blog_sources:
            if 'url' not in blog_info or not blog_info['url']:
                logger.warning(f"Skipping blog with no URL: {blog_info.get('name', 'Unknown')}")
                continue
            
            blog_entries = []
            
            # Use specialized scrapers for known sites
            url = blog_info['url'].lower()  # Use lowercase for consistent comparison
            if 'transformer-circuits.pub' in url:
                blog_entries = scrape_circuits_research(url)
                logger.info(f"Used Transformer Circuits scraper for {url}")
            elif 'anthropic.com/' in url:
                blog_entries = scrape_anthropic_research(url)
                logger.info(f"Used Anthropic scraper for {url}")
            elif 'openai.com/research' in url:
                blog_entries = scrape_openai_research(url)
                logger.info(f"Used OpenAI scraper for {url}")
            elif 'deepmind' in url:
                blog_entries = scrape_deepmind_research(url)
                logger.info(f"Used DeepMind scraper for {url}")
            else:
                raise ValueError(f"Unknown blog source: {url}")
                #blog_entries = scrape_generic_blog(blog_info)
                #logger.info(f"Used generic scraper for {url}")
                
            # Filter by keywords if needed
            if enable_keywords:
                if keywords:
                    filtered_entries = [e for e in blog_entries if keyword_matches(e, keywords)]
                    logger.info(f"Filtered from {len(blog_entries)} to {len(filtered_entries)} entries by keywords")
                    blog_entries = filtered_entries
            
            blog_entries = [e for e in blog_entries if is_recent_publication(e, start_date, end_date)]
            logger.info(f"Filtered to {len(blog_entries)} recent entries from {url}")

            all_entries.extend(blog_entries)
            
            # Respect rate limits between different sites
            time.sleep(2)
            
        logger.info(f"Total blog entries found: {len(all_entries)}")
        
        # Limit to max_entries
        all_entries = all_entries[:max_entries]
        
        # Save raw data
        raw_data_dir = base_dir / "data" / "raw"
        os.makedirs(raw_data_dir, exist_ok=True)
        
        output_file = raw_data_dir / f"blogs_{start_date.strftime('%Y%m%d')}.json"
        with open(output_file, 'w') as f:
            json.dump(all_entries, f, indent=2)
            
        logger.info(f"Saved {len(all_entries)} blog entries to {output_file}")
        
        return all_entries
        
    except Exception as e:
        logger.error(f"Error in scrape_blogs: {e}")
        return []

if __name__ == "__main__":
    # Test directly
    logging.basicConfig(level=logging.INFO)
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=30)  # Search for blog posts from the last month
    blog_entries = scrape_blogs(start_date, end_date, max_entries=100)
    print(f"Found {len(blog_entries)} blog entries")
    
    # Display the first entry if available
    if blog_entries:
        print(f"First entry: {blog_entries[0]['title']}")