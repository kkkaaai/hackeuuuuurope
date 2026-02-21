import math

async def execute(inputs: dict, context: dict) -> dict:
    stories = inputs['stories']
    max_views = max(story['view_count'] for story in stories) if stories else 0
    scored_stories = []
    for story in stories:
        score = math.ceil((story['view_count'] / max_views) * 100) if max_views > 0 else 0
        scored_stories.append({
            'headline': story['headline'],
            'score': score,
            'link': story['link']
        })
    return {'scored_stories': scored_stories}
