import json
import os
import random
import time
import requests # Added for making HTTP requests to external APIs

# --- Configuration ---
# You'll need to sign up for a NewsAPI.org key: https://newsapi.org/
# The free developer tier allows up to 100 requests per day.
# Store this key as a GitHub Secret named NEWS_API_KEY
NEWS_API_BASE_URL = "https://newsapi.org/v2/everything" # Or /v2/top-headlines for simpler fetching
NEWS_API_KEY = os.getenv('NEWS_API_KEY') # Fetched from GitHub Secrets

# Define the regions and categories that match your index.html
# Mapping regions to NewsAPI country codes (simplified, NewsAPI mostly by country)
# For broader regions like 'Europe', you might fetch from multiple countries.
# This mapping is crucial for making targeted API calls.
# Note: NewsAPI 'country' parameter only accepts specific 2-letter ISO codes.
# For regions like "global" or broad continents, NewsAPI's 'country' filter
# is not applicable, so we'll treat them as a global search without a country filter.
REGIONS = {
    "global": {"name": "the entire world", "country_code": None}, # No specific country code for global
    "north_america": {"name": "North America", "country_code": "us"}, # Focusing on US for simplicity
    "europe": {"name": "Europe", "country_code": "gb"}, # Focusing on UK for Europe example
    "asia": {"name": "Asia", "country_code": "in"}, # Focusing on India for Asia example
    "africa": {"name": "Africa", "country_code": "ng"}, # Focusing on Nigeria for Africa example
    "oceania": {"name": "Oceania", "country_code": "au"}, # Focusing on Australia for Oceania example
    "south_america": {"name": "South America", "country_code": "br"}, # Focusing on Brazil for South America example
    "middle_east": {"name": "Middle East", "country_code": "ae"}, # Focusing on UAE for Middle East example
    "southeast_asia": {"name": "Southeast Asia", "country_code": "sg"}, # Focusing on Singapore for Southeast Asia example
    "north_africa": {"name": "North Africa", "country_code": "eg"}, # Focusing on Egypt for North Africa example
    "sub_saharan_africa": {"name": "Sub-Saharan Africa", "country_code": "za"}, # Focusing on South Africa for Sub-Saharan Africa example
    "east_asia": {"name": "East Asia", "country_code": "jp"}, # Focusing on Japan for East Asia example
    "south_asia": {"name": "South Asia", "country_code": "pk"}, # Focusing on Pakistan for South Asia example
    "australia_nz": {"name": "Australia & NZ", "country_code": "nz"} # Focusing on New Zealand for Australia & NZ example
}


CATEGORIES = {
    "news": ["general", "breaking news"],
    "technology": ["technology", "AI", "cybersecurity", "gadgets"],
    "finance": ["business", "finance", "markets", "economy"],
    "travel": ["travel", "tourism", "adventure"],
    "world": ["politics", "international relations", "global affairs"],
    "weather": ["weather", "climate change", "natural disasters"], # NewsAPI isn't ideal for weather forecasts, more for weather-related *news*
    "blogs": ["opinion", "analysis", "lifestyle"]
}

# --- Functions ---

def fetch_content_from_newsapi(query, country_code=None, count=10):
    """
    Fetches real news articles from NewsAPI.org.
    """
    if not NEWS_API_KEY:
        print("NEWS_API_KEY is not set. Cannot fetch real news.")
        return []

    params = {
        'q': query,
        'language': 'en',
        'pageSize': count, # Number of articles to fetch
        'apiKey': NEWS_API_KEY
    }
    if country_code: # Only add country param if a specific code is provided
        params['country'] = country_code

    try:
        response = requests.get(NEWS_API_BASE_URL, params=params, timeout=10)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        
        articles = []
        for article in data.get('articles', []):
            if article.get('title') and article.get('description') and article.get('url'):
                articles.append({
                    "title": article['title'],
                    "content": article['description'],
                    "link": article['url'],
                    "imageUrl": article.get('urlToImage', 'https://placehold.co/600x400/CCCCCC/333333?text=Image+Unavailable')
                })
        return articles
    except requests.exceptions.RequestException as e:
        print(f"Error fetching from NewsAPI for query '{query}', country '{country_code if country_code else 'N/A'}': {e}")
        return []

def generate_simulated_content(region_name, category_name, count=15):
    """
    Generates simulated content as a fallback or for categories not covered by NewsAPI.
    """
    articles = []
    for i in range(count):
        hex_color_bg = ''.join([random.choice('0123456789ABCDEF') for _ in range(6)])
        hex_color_text = ''.join([random.choice('0123456789ABCDEF') for _ in range(6)])

        title = f"{category_name.replace('_', ' ').title()} Update {i + 1} for {region_name}"
        content = f"This is a simulated summary of {category_name.replace('_', ' ')} related to {region_name}, article number {i + 1}. It highlights key developments and insights."
        link = f"https://example.com/{region_name.lower().replace(' ', '-')}/{category_name.lower().replace(' ', '-')}/{i + 1}"
        image_url = f"https://placehold.co/600x400/{hex_color_bg}/{hex_color_text}?text={category_name.title()}+{i+1}"

        articles.append({
            "title": title,
            "content": content,
            "link": link,
            "imageUrl": image_url
        })
    return articles

def main():
    all_content = {}
    
    for region_key, region_data in REGIONS.items():
        region_name_full = region_data["name"]
        country_code = region_data["country_code"] # Get country code from the region data
        
        all_content[region_key] = {}

        for category_key, keywords in CATEGORIES.items():
            print(f"Processing Region: {region_name_full}, Category: {category_key}")
            
            # Prioritize fetching from NewsAPI if key is available and a country code is applicable
            # Note: NewsAPI 'country' parameter only works for specific 2-letter codes.
            # For 'global' or general categories, country_code will be None.
            if NEWS_API_KEY and country_code: 
                # Use the first keyword from the list as the main query for NewsAPI
                query = keywords[0] if keywords else category_key
                articles = fetch_content_from_newsapi(query, country_code, count=20) # Fetch up to 20 articles
                if not articles: # Fallback to simulated if API call fails or returns no articles
                    print(f"NewsAPI returned no articles or failed for {region_key}/{category_key}. Falling back to simulated content.")
                    articles = generate_simulated_content(region_name_full, category_key, count=20)
            else:
                # Fallback to simulated content if API key is missing or no specific country code
                print(f"Skipping NewsAPI for {region_key}/{category_key} (no API key or country code). Generating simulated content.")
                articles = generate_simulated_content(region_name_full, category_key, count=20)
            
            all_content[region_key][category_key] = articles
            time.sleep(1) # Be mindful of API rate limits, especially for free tiers

    output_file_path = 'updates.json'
    try:
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(all_content, f, indent=2, ensure_ascii=False)
        print(f"Successfully generated and saved content to {output_file_path}")
    except IOError as e:
        print(f"Error writing to file {output_file_path}: {e}")

if __name__ == "__main__":
    main()
