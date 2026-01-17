'''
If you're wondering what's that file. Scraper.py is the main async version of the 
scraper script using Playwright async API - That uses two threads (One for live section another from top section
based on one query) main.py runs scraper.py on multiple threads using multiple queries. Which makes it 
the fastest version. 
'''


import asyncio
from Scraper import run_all_queries

queries = [
    "Physics and astronomy",
    "Astrophysics",
    "Quantum mechanics",
    "Cosmology"
]

if __name__ == "__main__":
    results = asyncio.run(run_all_queries(queries, max_scrolls=3))

    # Merge all results safely
    final_data = {
        'Usernames': [],
        'DisplayNames': [],
        'VerifiedStatus': []
    }
    seen = set()

    for data in results:
        for u, d, v in zip(data['Usernames'], data['DisplayNames'], data['VerifiedStatus']):
            if u not in seen:
                seen.add(u)
                final_data['Usernames'].append(u)
                final_data['DisplayNames'].append(d)
                final_data['VerifiedStatus'].append(v)

    print(f"Total unique posts from all queries: {len(final_data['Usernames'])}")
