from flask import Flask, render_template, request, redirect, url_for, jsonify
from notion_client import Client
from datetime import datetime
import os
from dotenv import load_dotenv
import pytz

load_dotenv()

app = Flask(__name__)

# Notion API credentials
NOTION_TOKEN = os.getenv('NOTION_TOKEN')
DATABASE_ID = os.getenv('NOTION_DATABASE_ID')

notion = Client(auth=NOTION_TOKEN)

def get_utc_now():
    return datetime.now(pytz.UTC)

def get_todos():
    try:
        response = notion.databases.query(
            database_id=DATABASE_ID,
            sorts=[
                {
                    "property": "Status",
                    "direction": "ascending"  # Show uncompleted tasks first
                },
                {
                    "property": "Order",
                    "direction": "ascending"  # Then sort by order
                }
            ],
            filter={
                "property": "Title",
                "title": {
                    "is_not_empty": True
                }
            }
        )
        print("Notion API Response:", response)
        return response.get('results', [])
    except Exception as e:
        print(f"Error fetching todos: {e}")
        return []

def create_todo(title, description="", deadline=None):
    try:
        # Get the current maximum order
        todos = get_todos()
        max_order = 0
        for todo in todos:
            current_order = todo['properties'].get('Order', {}).get('number', 0)
            max_order = max(max_order, current_order or 0)

        properties = {
            "Title": {
                "title": [
                    {
                        "text": {
                            "content": title
                        }
                    }
                ]
            },
            "Description": {
                "rich_text": [
                    {
                        "text": {
                            "content": description
                        }
                    }
                ]
            },
            "Status": {
                "checkbox": False
            },
            "Order": {
                "number": max_order + 1000
            }
        }

        # Add deadline if exists
        if deadline:
            properties["Deadline"] = {
                "date": {
                    "start": deadline
                }
            }

        notion.pages.create(
            parent={"database_id": DATABASE_ID},
            properties=properties
        )
        return True
    except Exception as e:
        print(f"Error creating todo: {e}")
        return False

def update_todo_order(page_id, new_order):
    try:
        notion.pages.update(
            page_id=page_id,
            properties={
                "Order": {
                    "number": new_order
                }
            }
        )
        return True
    except Exception as e:
        print(f"Error updating todo order: {e}")
        return False

@app.route('/reorder', methods=['POST'])
def reorder():
    try:
        data = request.get_json()
        todos = data.get('todos', [])
        
        # Update each todo's order
        for index, todo_id in enumerate(todos):
            update_todo_order(todo_id, (index + 1) * 1000)
        
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error in reorder: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

def toggle_todo(page_id):
    try:
        # Get current status
        page = notion.pages.retrieve(page_id=page_id)
        current_status = page['properties']['Status']['checkbox']
        
        # Determine new status
        new_status = not current_status
        
        # If task is completed, find the highest order number and add to it
        new_order = None
        if new_status:  # If task is completed
            todos = get_todos()
            max_order = 0
            for todo in todos:
                current_order = todo['properties'].get('Order', {}).get('number', 0)
                max_order = max(max_order, current_order or 0)
            new_order = max_order + 1000

        # Update properties
        properties = {
            "Status": {
                "checkbox": new_status
            }
        }
        
        # Add new order if determined
        if new_order is not None:
            properties["Order"] = {
                "number": new_order
            }

        notion.pages.update(
            page_id=page_id,
            properties=properties
        )
        return True
    except Exception as e:
        print(f"Error toggling todo: {e}")
        return False

def delete_todo(page_id):
    try:
        notion.pages.update(
            page_id=page_id,
            archived=True
        )
        return True
    except Exception as e:
        print(f"Error deleting todo: {e}")
        return False

def get_page_info(page_id):
    try:
        # First, retrieve the page itself
        page = notion.pages.retrieve(page_id=page_id)
        print(f"Retrieved page data: {page}")
        
        # Find the title
        title = ""
        if 'properties' in page:
            for prop in page['properties'].values():
                if prop.get('type') == 'title':
                    title_parts = prop.get('title', [])
                    if title_parts:
                        title = title_parts[0].get('plain_text', '')
                        break

        # Get the page content
        blocks = notion.blocks.children.list(block_id=page_id)
        print(f"Retrieved blocks: {blocks}")
        
        preview_text = []
        for block in blocks.get('results', []):
            block_type = block.get('type', '')
            
            if block_type == 'paragraph':
                text_content = block['paragraph'].get('rich_text', [])
                if text_content:
                    preview_text.append(text_content[0].get('plain_text', ''))
            
            elif block_type == 'heading_1':
                text_content = block['heading_1'].get('rich_text', [])
                if text_content:
                    preview_text.append(f"# {text_content[0].get('plain_text', '')}")
            
            elif block_type == 'heading_2':
                text_content = block['heading_2'].get('rich_text', [])
                if text_content:
                    preview_text.append(f"## {text_content[0].get('plain_text', '')}")
            
            elif block_type == 'heading_3':
                text_content = block['heading_3'].get('rich_text', [])
                if text_content:
                    preview_text.append(f"### {text_content[0].get('plain_text', '')}")
            
            elif block_type == 'bulleted_list_item':
                text_content = block['bulleted_list_item'].get('rich_text', [])
                if text_content:
                    preview_text.append(f"• {text_content[0].get('plain_text', '')}")
            
            elif block_type == 'numbered_list_item':
                text_content = block['numbered_list_item'].get('rich_text', [])
                if text_content:
                    preview_text.append(f"1. {text_content[0].get('plain_text', '')}")

            # Max 5 blocks
            if len(preview_text) >= 5:
                break

        return {
            'title': title,
            'preview': '\n'.join(preview_text)
        }
    except Exception as e:
        print(f"Error fetching page info: {e}")
        return {'title': '', 'preview': ''}

def extract_page_id_from_url(url):
    try:
        # Get the ID at the end of the URL
        page_id = url.split('-')[-1].split('?')[0]
        # Convert the ID to the format Notion expects (8-4-4-4-12)
        if len(page_id) == 32:
            return f"{page_id[:8]}-{page_id[8:12]}-{page_id[12:16]}-{page_id[16:20]}-{page_id[20:]}"
        return None
    except Exception as e:
        print(f"Error extracting page ID from URL: {e}")
        return None

@app.route('/')
def index():
    todos = get_todos()
    formatted_todos = []
    now = get_utc_now()
    
    for todo in todos:
        try:
            title = todo['properties'].get('Title', {}).get('title', [])
            title_content = title[0]['text']['content'] if title else 'Untitled'
            
            description = todo['properties'].get('Description', {}).get('rich_text', [])
            description_content = description[0]['text']['content'] if description else ''
            
            # Get deadline
            deadline = todo['properties'].get('Deadline', {}).get('date', {})
            deadline_date = None
            if deadline and deadline.get('start'):
                deadline_date = datetime.fromisoformat(deadline['start'].replace('Z', '+00:00')).astimezone(pytz.UTC)
            
            # Get category information from mention
            category_info = {'title': '', 'preview': ''}
            category_text = todo['properties'].get('Category', {}).get('rich_text', [])
            if category_text and len(category_text) > 0:
                mention_data = category_text[0]
                if mention_data.get('type') == 'mention' and mention_data.get('mention', {}).get('type') == 'page':
                    category_title = mention_data.get('plain_text', '')
                    page_id = mention_data['mention']['page']['id']
                    
                    if page_id:
                        print(f"Fetching info for category page: {page_id}")
                        category_info = get_page_info(page_id)
                        if not category_info['title']:
                            category_info['title'] = category_title
                        print(f"Category info found: {category_info}")
            
            formatted_todo = {
                'id': todo['id'],
                'title': title_content,
                'description': description_content,
                'category': category_info['title'],
                'category_preview': category_info['preview'],
                'completed': todo['properties'].get('Status', {}).get('checkbox', False),
                'created_at': datetime.fromisoformat(todo['created_time'].replace('Z', '+00:00')).astimezone(pytz.UTC),
                'deadline': deadline_date,
                'order': todo['properties'].get('Order', {}).get('number', 0)
            }
            formatted_todos.append(formatted_todo)
            print("Formatted todo:", formatted_todo)
        except Exception as e:
            print(f"Error formatting todo: {e}")
            continue
    
    return render_template('index.html', todos=formatted_todos, now=now)

@app.route('/add', methods=['POST'])
def add():
    title = request.form.get('title')
    description = request.form.get('description', '')
    deadline = request.form.get('deadline', '')
    
    if title:
        if deadline:
            # Convert local time to UTC
            local_dt = datetime.fromisoformat(deadline)
            utc_dt = local_dt.astimezone(pytz.UTC).isoformat()
            create_todo(title, description, utc_dt)
        else:
            create_todo(title, description, None)
    return redirect(url_for('index'))

@app.route('/complete/<string:id>')
def complete(id):
    toggle_todo(id)
    return redirect(url_for('index'))

@app.route('/delete/<string:id>')
def delete(id):
    delete_todo(id)
    return redirect(url_for('index'))

if __name__ == '__main__':
    if not NOTION_TOKEN or not DATABASE_ID:
        print("Error: Please set NOTION_TOKEN and NOTION_DATABASE_ID in .env file")
    else:
        app.run(debug=True) 