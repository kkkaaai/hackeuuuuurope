import collections
import re

async def execute(inputs: dict, context: dict) -> dict:
    results = inputs['results']
    title_counter = collections.Counter()
    title_to_url = {}

    for result in results:
        title = result['title']
        url = result['url']
        # Normalize the title by removing non-alphanumeric characters and converting to lowercase
        normalized_title = re.sub(r'\W+', ' ', title).lower()
        title_counter[normalized_title] += 1
        if normalized_title not in title_to_url:
            title_to_url[normalized_title] = url

    stories = [
        {
            'headline': title,
            'score': count,
            'link': title_to_url[title]
        }
        for title, count in title_counter.items()
    ]

    # Sort stories by score in descending order
    stories.sort(key=lambda x: x['score'], reverse=True)

    return {'stories': stories}
