import requests
import xml.etree.ElementTree as ET
from xml.dom import minidom
from tqdm import tqdm
import re

# --------------------------------------------------------------------
# 1) Definitions & Constants
# --------------------------------------------------------------------
SUMMARY_URL_BOOK = "https://raw.githubusercontent.com/HackTricks-wiki/hacktricks/refs/heads/master/src/SUMMARY.md"
SUMMARY_URL_CLOUD = "https://raw.githubusercontent.com/HackTricks-wiki/hacktricks-cloud/refs/heads/master/src/SUMMARY.md"

BOOK_DOMAIN = "book.hacktricks.wiki"
CLOUD_DOMAIN = "cloud.hacktricks.wiki"

# Dictionary of languages and their codes
languages = {
    "es": "es",
    "af": "af",
    "zh": "zh",
    "fr": "fr",
    "de": "de",
    "el": "el",
    "hi": "hi",
    "it": "it",
    "ja": "ja",
    "ko": "ko",
    "pl": "pl",
    "pt": "pt",
    "sr": "sr",
    "sw": "sw",
    "tr": "tr",
    "uk": "uk",
}

# --------------------------------------------------------------------
# 2) Helper Functions
# --------------------------------------------------------------------
def fetch_summary(url):
    """Fetch the content of a SUMMARY.md-like file."""
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.text

def parse_paths_from_summary(summary_text):
    """
    Parse the SUMMARY.md content and extract paths of the form:
       [Title](some/path.md)
       [Title](some/path/)
       [Title](some/README.md)
       etc.

    According to your instructions:
      - Do NOT remove '/index' paths
      - Change '.md' to '.html'
      - Change '/README.md' -> '/index.html'
    
    Returns a list of unique paths (without duplicates).
    """
    # Regex to find standard Markdown links: [some text](some/path)
    # Capture everything inside parentheses after the bracket, ignoring any leading/trailing spaces.
    pattern = r"\[[^\]]+\]\(\s*([^)]+?)\s*\)"
    matches = re.findall(pattern, summary_text)

    cleaned_paths = []
    for path in matches:
        # Trim whitespace just in case
        path = path.strip()

        # 1) Handle /README.md -> /index.html
        #    (anywhere in the path, not just the very end, but typically it should be at the end)
        if path.endswith("README.md"):
            path = path[:-9] + "index.html"

        # 2) Else if it ends with .md -> .html
        elif path.endswith(".md"):
            path = path[:-3] + ".html"

        # You asked NOT to remove /index or trailing slashes
        # so we won't do any extra trimming beyond that.

        # Avoid duplicates
        if path not in cleaned_paths:
            cleaned_paths.append(path)

    return cleaned_paths

def compute_priority_from_depth(path):
    """
    The priority starts at 1.0 for depth 0, 
    and each additional subfolder subtracts 0.1.
      Depth 0 => priority = 1.00
      Depth 1 => priority = 0.9
      Depth 2 => priority = 0.8
      ...
      Min 0.5
    """
    effective_path = path.strip('/')
    if not effective_path:
        depth = 0
    else:
        depth = effective_path.count('/')
    priority = 1.0 - (0.1 * depth)
    return max(priority, 0.5)

def prettify_xml(element):
    """Return a prettified string representation of the XML with XML declaration."""
    rough_string = ET.tostring(element, encoding='utf-8')
    reparsed = minidom.parseString(rough_string)
    pretty = reparsed.toprettyxml(indent="  ", encoding="UTF-8")
    return pretty.decode('UTF-8')

def add_translated_urls(url_element, base_domain, path):
    """
    Add translated URLs with language codes, e.g.:
       https://<base_domain>/<lang_code><path>

    Also sets x-default to English by default.
    """
    # We'll set x-default to the English version
    xdefault_link = ET.SubElement(url_element, '{http://www.w3.org/1999/xhtml}link')
    xdefault_link.set('rel', 'alternate')
    xdefault_link.set('hreflang', 'x-default')
    xdefault_link.set('href', f"https://{base_domain}/en/{path}")

    # Add one <xhtml:link> for each language
    for lang_code in languages.values():
        alt_link = ET.SubElement(url_element, '{http://www.w3.org/1999/xhtml}link')
        alt_link.set('rel', 'alternate')
        alt_link.set('hreflang', lang_code)
        alt_link.set('href', f"https://{base_domain}/{lang_code}/{path}")

# --------------------------------------------------------------------
# 3) Main logic
# --------------------------------------------------------------------
def main():
    print("**Fetching SUMMARY files**...")
    book_summary = fetch_summary(SUMMARY_URL_BOOK)
    cloud_summary = fetch_summary(SUMMARY_URL_CLOUD)

    print("**Extracting paths from summaries**...")
    book_paths = parse_paths_from_summary(book_summary)
    cloud_paths = parse_paths_from_summary(cloud_summary)

    # Prepare the output sitemap root
    ET.register_namespace('', "http://www.sitemaps.org/schemas/sitemap/0.9")
    ET.register_namespace('xhtml', "http://www.w3.org/1999/xhtml")
    root = ET.Element('{http://www.sitemaps.org/schemas/sitemap/0.9}urlset')

    # ----------------------------------------------------------------
    # 3.1) Process Book paths
    # ----------------------------------------------------------------
    print("**Processing Book paths**...")
    for p in tqdm(book_paths, desc="Book paths"):
        # Create <url> element
        url_element = ET.Element('{http://www.sitemaps.org/schemas/sitemap/0.9}url')

        # Our base location for English is domain/en/path
        loc_el = ET.SubElement(url_element, '{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
        full_en_url = f"https://{BOOK_DOMAIN}/en/{p}"
        loc_el.text = full_en_url

        # Priority calculation
        priority_el = ET.SubElement(url_element, '{http://www.sitemaps.org/schemas/sitemap/0.9}priority')
        priority_el.text = f"{compute_priority_from_depth(p):.2f}"

        # Add translations
        add_translated_urls(url_element, BOOK_DOMAIN, p)
        root.append(url_element)

    # ----------------------------------------------------------------
    # 3.2) Process Cloud paths
    # ----------------------------------------------------------------
    print("**Processing Cloud paths**...")
    for p in tqdm(cloud_paths, desc="Cloud paths"):
        # Create <url> element
        url_element = ET.Element('{http://www.sitemaps.org/schemas/sitemap/0.9}url')

        # Our base location for English is domain/en/path
        loc_el = ET.SubElement(url_element, '{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
        full_en_url = f"https://{CLOUD_DOMAIN}/en/{p}"
        loc_el.text = full_en_url

        # Priority calculation
        priority_el = ET.SubElement(url_element, '{http://www.sitemaps.org/schemas/sitemap/0.9}priority')
        priority_el.text = f"{compute_priority_from_depth(p):.2f}"

        # Add translations
        add_translated_urls(url_element, CLOUD_DOMAIN, p)
        root.append(url_element)

    # ----------------------------------------------------------------
    # 3.3) Write the final sitemap
    # ----------------------------------------------------------------
    print("**Generating final sitemap**...")
    sitemap_xml = prettify_xml(root)
    with open("sitemap.xml", "w", encoding="utf-8") as f:
        f.write(sitemap_xml)

    print("**sitemap.xml has been successfully generated.**")

if __name__ == "__main__":
    main()
