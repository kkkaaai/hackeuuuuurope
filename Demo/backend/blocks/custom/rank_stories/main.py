import json

async def execute(inputs: dict, context: dict) -> dict:
    stories = inputs['stories']
    # Sort stories by score in descending order
    sorted_stories = sorted(stories, key=lambda x: x['score'], reverse=True)
    # Assign ranks to the sorted stories
    ranked_stories = [
        {
            'rank': index + 1,
            'headline': story['headline'],
            'score': story['score'],
            'link': story['link']
        }
        for index, story in enumerate(sorted_stories)
    ]
    return {'ranked_stories': ranked_stories}
