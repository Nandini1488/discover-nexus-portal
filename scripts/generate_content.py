import json
import os
import random
import time

# IMPORTANT: This is a placeholder for actual Gemini API calls.
# In a real scenario, you would use a library like `google-generativeai`
# to interact with the Gemini API to generate your content based on prompts.
# For this example, we're simulating the content generation.

# Define the regions and categories that match your index.html
REGIONS = {
    "global": "the entire world",
    "north_america": "North America",
    "europe": "Europe",
    "asia": "Asia",
    "africa": "Africa",
    "oceania": "Oceania",
    "south_america": "South America",
    "middle_east": "the Middle East",
    "southeast_asia": "Southeast Asia",
    "north_africa": "North Africa",
    "sub_saharan_africa": "Sub-Saharan Africa",
    "east_asia": "East Asia",
    "south_asia": "South Asia",
    "australia_nz": "Australia and New Zealand"
}

CATEGORIES = [
    "news",
    "technology",
    "finance",
    "travel",
    "world",
    "weather",
    "blogs"
]

# Function to simulate Gemini API call and generate content
def generate_gemini_content(region, category, count=15):
    """
    Simulates calling the Gemini API to generate content.
    In a real application, this function would prompt Gemini
    and parse its response into the desired format.
    """
    print(f"Simulating content generation for {category} in {region}...")
    articles = []
    for i in range(count):
        # Generate a random hex color for the placeholder image
        hex_color_bg = ''.join([random.choice('0123456789ABCDEF') for _ in range(6)])
        hex_color_text = ''.join([random.choice('0123456789ABCDEF') for _ in range(6)])

        title = f"{category.replace('_', ' ').title()} Update {i + 1} for {REGIONS[region]}"
        content = f"This is a simulated summary of {category.replace('_', ' ')} related to {REGIONS[region]}, article number {i + 1}. It highlights key developments and insights."
        link = f"https://example.com/{region}/{category}/{i + 1}"
        image_url = f"https://placehold.co/600x400/{hex_color_bg}/{hex_color_text}?text={category.title()}+{i+1}"

        articles.append({
            "title": title,
            "content": content,
            "link": link,
            "imageUrl": image_url
        })
    return articles

def main():
    # Attempt to get the Gemini API key from environment variables (GitHub Secrets)
    # gemini_api_key = os.getenv('GEMINI_API_KEY')
    # if not gemini_api_key:
    #     print("Error: GEMINI_API_KEY environment variable not set.")
    #     # In a real GitHub Action, you might exit here or raise an error
    #     # For this simulation, we'll continue with mock data.
    #     pass

    all_content = {}
    for region_key, region_name in REGIONS.items():
        all_content[region_key] = {}
        for category in CATEGORIES:
            print(f"Generating content for Region: {region_name}, Category: {category}")
            # Call the simulated Gemini function
            content_list = generate_gemini_content(region_key, category, count=random.randint(10, 25)) # Generate varying amounts
            all_content[region_key][category] = content_list
            time.sleep(0.5) # Simulate some work/API delay

    # Define the path to the updates.json file relative to the script
    # The script will be run from the root of the repository by the GitHub Action
    output_file_path = 'updates.json'

    # Write the generated content to updates.json
    try:
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(all_content, f, indent=2, ensure_ascii=False)
        print(f"Successfully generated and saved content to {output_file_path}")
    except IOError as e:
        print(f"Error writing to file {output_file_path}: {e}")

if __name__ == "__main__":
    main()
