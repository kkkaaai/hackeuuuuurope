import json
import sys
import statistics

def calculate_statistics(numbers):
    if not numbers:
        return {}
    total = sum(numbers)
    count = len(numbers)
    mean = total / count
    return {
        'sum': total,
        'mean': mean,
        'count': count
    }

input_data = json.loads(sys.stdin.read())
numbers = input_data.get('numbers', [])
result = calculate_statistics(numbers)
output = {'result': result}
print(json.dumps(output))