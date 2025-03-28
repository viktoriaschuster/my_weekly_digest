# blog_generator.py

def generate_blog_post(summarized_entries):
    """
    Generate a blog post from the summarized entries.
    
    Args:
        summarized_entries (list): A list of summarized research entries.
        
    Returns:
        str: A formatted blog post as a string.
    """
    blog_content = "# Weekly Research Digest\n\n"
    blog_content += "## Summary of New Research Works\n\n"
    
    for entry in summarized_entries:
        blog_content += f"### {entry['title']}\n"
        blog_content += f"**Authors:** {', '.join(entry['authors'])}\n"
        blog_content += f"**Summary:** {entry['summary']}\n"
        blog_content += f"**Quality Assessment:** {entry['quality']}\n"
        blog_content += f"**Link:** [Read more]({entry['link']})\n\n"
    
    return blog_content

def save_blog_post_to_file(blog_content, file_path):
    """
    Save the generated blog post to a file.
    
    Args:
        blog_content (str): The content of the blog post.
        file_path (str): The path where the blog post will be saved.
    """
    with open(file_path, 'w') as file:
        file.write(blog_content)