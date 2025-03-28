def filter_entries_by_keywords(entries, keywords):
    filtered_entries = []
    for entry in entries:
        if any(keyword.lower() in entry['title'].lower() or keyword.lower() in entry['abstract'].lower() for keyword in keywords):
            filtered_entries.append(entry)
    return filtered_entries

def load_keywords_from_config(config_path):
    import json
    with open(config_path, 'r') as file:
        config = json.load(file)
    return config.get('keywords', [])

def save_filtered_entries(filtered_entries, output_path):
    import json
    with open(output_path, 'w') as file:
        json.dump(filtered_entries, file, indent=4)