import json
import os
import random
import time
import requests

# --- Configuration ---
# You'll need to sign up for a NewsAPI.org key: https://newsapi.org/
# The free developer tier allows up to 100 requests per day.
# Store this key as a GitHub Secret named NEWS_API_KEY
NEWS_API_BASE_URL = "https://newsapi.org/v2/top-headlines" # Changed to top-headlines
NEWS_API_KEY = os.getenv('NEWS_API_KEY') # Fetched from GitHub Secrets

# --- Debugging Print ---
if NEWS_API_KEY:
    print("NEWS_API_KEY successfully loaded from environment.")
else:
    print("WARNING: NEWS_API_KEY is NOT loaded from environment. Please check GitHub Secrets.")
# --- End Debugging Print ---

# Define the regions and categories that match your index.html
# Mapping regions to NewsAPI country codes (simplified, NewsAPI mostly by country)
REGIONS = {
    "global": {"name": "the entire world", "country_code": None}, # No specific country code for global top-headlines
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
    "news": ["general"], # NewsAPI top-headlines uses 'category' parameter, not 'q' for general news
    "technology": ["technology"],
    "finance": ["business"],
    "travel": ["travel"], # NewsAPI doesn't have a direct 'travel' category, will use general or simulated
    "world": ["politics"],
    "weather": ["science"], # NewsAPI doesn't have a direct 'weather' category, using 'science' as closest
    "blogs": ["general"] # NewsAPI doesn't have a direct 'blogs' category, using 'general' as closest
}

# --- Functions ---

def fetch_content_from_newsapi(query=None, category=None, country_code=None, count=10):
    """
    Fetches real news articles from NewsAPI.org using the /v2/top-headlines endpoint.
    """
    if not NEWS_API_KEY:
        print("NEWS_API_KEY is not set. Cannot fetch real news.")
        return []

    params = {
        'language': 'en',
        'pageSize': count, # Number of articles to fetch per request
        'apiKey': NEWS_API_KEY
    }

    if country_code:
        params['country'] = country_code
    else:
        # For global, we cannot use 'country' parameter with top-headlines.
        # NewsAPI requires either 'country' or 'sources' for top-headlines.
        # If no country, we'll try a general query or fallback to simulated.
        # For now, if no country, it will likely return an error unless a 'q' is used.
        # We will handle this by falling back to simulated content if the API fails.
        pass 

    if category:
        params['category'] = category
    elif query: # 'q' parameter is for keywords, not categories
        params['q'] = query

    try:
        response = requests.get(NEWS_API_BASE_URL, params=params, timeout=10)
        response.raise_for_status()
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
        print(f"Error fetching from NewsAPI for category '{category}'/query '{query}', country '{country_code if country_code else 'N/A'}': {e}")
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
        country_code = region_data["country_code"]
        
        all_content[region_key] = {}

        for category_key, keywords in CATEGORIES.items():
            print(f"Processing Region: {region_name_full}, Category: {category_key}")
            
            # Fetch from NewsAPI if API key is present.
            if NEWS_API_KEY: 
                newsapi_category = keywords[0] # Use the first keyword as the NewsAPI category
                
                # NewsAPI /top-headlines requires 'country' or 'sources' parameter.
                # If country_code is None (e.g., for 'global' region), NewsAPI will likely return an error
                # unless a general 'q' parameter is used, which is not ideal for 'top-headlines' by category.
                # So, for global or regions without a specific country_code, we'll generate simulated content.
                if country_code:
                    articles = fetch_content_from_newsapi(category=newsapi_category, country_code=country_code, count=35) # Changed count to 35
                else:
                    # For 'global' or other regions without a country_code, fall back to simulated.
                    # NewsAPI's /top-headlines endpoint requires a country or source.
                    print(f"NewsAPI /top-headlines requires a country for {region_key}/{category_key}. Generating simulated content.")
                    articles = [] # Ensure articles is empty to trigger simulated content fallback

                if not articles:
                    print(f"NewsAPI returned no articles or failed for {region_key}/{category_key}. Falling back to simulated content.")
                    articles = generate_simulated_content(region_name_full, category_key, count=15)
            else:
                print(f"Skipping NewsAPI for {region_key}/{category_key} (API key not loaded). Generating simulated content.")
                articles = generate_simulated_content(region_name_full, category_key, count=15)
            
            all_content[region_key][category_key] = articles
            time.sleep(5) # Increased sleep time to 5 seconds (from 1 second)

    output_file_path = 'updates.json'
    try:
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(all_content, f, indent=2, ensure_ascii=False)
        print(f"Successfully generated and saved content to {output_file_path}")
    except IOError as e:
        print(f"Error writing to file {output_file_path}: {e}")

if __name__ == "__main__":
    main()
