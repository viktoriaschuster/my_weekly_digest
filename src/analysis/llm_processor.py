import requests
import json
import time
import logging

logger = logging.getLogger(__name__)

def check_lm_studio_connection(base_url="http://localhost:1234"):
    """Check if LM Studio server is running."""
    try:
        response = requests.get(base_url)
        logger.info(f"LM Studio connection successful: {response.status_code}")
        return True
    except requests.exceptions.ConnectionError:
        logger.error("Cannot connect to LM Studio server")
        return False

def query_lm_studio(prompt, api_url="http://localhost:1234/v1/chat/completions", 
                   model="local-model", temperature=0.7, max_tokens=2048):
    """Query the local LM Studio model."""
    headers = {
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    try:
        response = requests.post(api_url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        logger.error(f"Error querying LM Studio: {e}")
        return None

def summarize_entry(entry):
    """Summarize a single research entry using LM Studio."""
    template = """
    Please provide a concise summary (3-5 sentences) of the following research paper:
    
    Title: {title}
    Authors: {authors}
    Abstract: {abstract}
    
    Focus on the key findings and contributions.
    """
    
    prompt = template.format(
        title=entry.get('title', ''),
        authors=entry.get('authors', ''),
        abstract=entry.get('abstract', '')
    )
    
    return query_lm_studio(prompt)

def assess_quality_and_novelty(entry):
    """Assess the quality and novelty of a research entry."""
    template = """
    Please assess the quality and novelty of the following research paper:
    
    Title: {title}
    Authors: {authors}
    Abstract: {abstract}
    
    Provide:
    1. Quality rating (1-5 stars, where 5 is highest quality)
    2. Novelty rating (1-5 stars, where 5 is most novel)
    3. Brief justification for your ratings (2-3 sentences)
    """
    
    prompt = template.format(
        title=entry.get('title', ''),
        authors=entry.get('authors', ''),
        abstract=entry.get('abstract', '')
    )
    
    return query_lm_studio(prompt)

def analyze_paper(paper):
    """Comprehensive analysis of a single paper with the LLM."""
    template = """
    Please analyze the following research paper:
    
    Title: {title}
    Authors: {authors}
    Abstract: {abstract}
    URL: {url}
    
    Provide:
    1. A concise summary (3-5 sentences)
    2. Main contributions and innovations
    3. Significance and potential impact (rate from 1-5 where 5 is highest)
    4. Relevance to mechanistic interpretability (if applicable)
    5. Limitations or potential flaws
    
    Keep your analysis objective and focus on the technical merits.
    """
    
    prompt = template.format(
        title=paper.get('title', ''),
        authors=paper.get('authors', ''),
        abstract=paper.get('abstract', ''),
        url=paper.get('url', '')
    )
    
    return query_lm_studio(prompt)

def process_scraped_entries(entries):
    """Process the scraped entries, analyzing each one with the LLM."""
    if not check_lm_studio_connection():
        logger.error("Cannot proceed with analysis: LM Studio not available")
        return entries  # Return unanalyzed entries
    
    processed_entries = []
    for entry in entries:
        logger.info(f"Processing entry: {entry.get('title', 'Untitled')}")
        
        # Add analysis to the entry
        entry['summary'] = summarize_entry(entry)
        entry['assessment'] = assess_quality_and_novelty(entry)
        entry['full_analysis'] = analyze_paper(entry)
        
        processed_entries.append(entry)
        time.sleep(1)  # Prevent overloading the LLM server
    
    return processed_entries

def analyze_papers(papers):
    """Legacy function to maintain API compatibility."""
    return process_scraped_entries(papers)