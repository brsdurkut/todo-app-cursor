from flask import Flask, render_template, request, redirect, url_for, jsonify
from notion_client import Client
from datetime import datetime
import os
from dotenv import load_dotenv
import pytz
from flask_cors import CORS

load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Security settings
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')

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

def get_categories():
    try:
        # Query the database to get its properties
        database = notion.databases.retrieve(database_id=DATABASE_ID)
        # Get the category options from the select property
        category_options = database.get('properties', {}).get('Category', {}).get('select', {}).get('options', [])
        return [{'id': option.get('id'), 'name': option.get('name')} for option in category_options]
    except Exception as e:
        print(f"Error fetching categories: {e}")
        return []

def create_todo(title, description="", deadline=None, category_name=None):
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

        # Add category if provided
        if category_name:
            properties["Category"] = {
                "select": {
                    "name": category_name
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

def update_todo_category(page_id, new_category):
    try:
        properties = {
            "Category": {
                "select": {
                    "name": new_category
                } if new_category != "Uncategorized" else None
            }
        }
        notion.pages.update(
            page_id=page_id,
            properties=properties
        )
        return True
    except Exception as e:
        print(f"Error updating todo category: {e}")
        return False

def update_todo_completion(page_id, is_completed, completion_date=None):
    try:
        properties = {
            "Status": {
                "checkbox": is_completed
            }
        }
        
        if is_completed and completion_date:
            properties["CompletedAt"] = {
                "date": {
                    "start": completion_date.isoformat()
                }
            }
        elif not is_completed:
            properties["CompletedAt"] = None
            
        notion.pages.update(
            page_id=page_id,
            properties=properties
        )
        return True
    except Exception as e:
        print(f"Error updating todo completion: {e}")
        return False

def update_todo(page_id, title, description="", deadline=None, category_name=None):
    try:
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
            }
        }

        # Update category if provided
        if category_name:
            properties["Category"] = {
                "select": {
                    "name": category_name
                }
            }
        elif category_name == "":  # Explicitly remove category
            properties["Category"] = {
                "select": None
            }

        # Update deadline if provided
        if deadline:
            properties["Deadline"] = {
                "date": {
                    "start": deadline
                }
            }
        elif deadline == "":  # Explicitly remove deadline
            properties["Deadline"] = {
                "date": None
            }

        notion.pages.update(
            page_id=page_id,
            properties=properties
        )
        return True
    except Exception as e:
        print(f"Error updating todo: {e}")
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
        # Get current status and current date
        page = notion.pages.retrieve(page_id=page_id)
        current_status = page['properties']['Status']['checkbox']
        now = get_utc_now()
        
        # Determine new status
        new_status = not current_status
        
        # If task is completed, find the highest order number and add to it
        new_order = None
        if new_status:  # If task is being completed
            todos = get_todos()
            max_order = 0
            for todo in todos:
                current_order = todo['properties'].get('Order', {}).get('number', 0)
                max_order = max(max_order, current_order or 0)
            new_order = max_order + 1000

        # Prepare properties update
        properties = {
            "Status": {
                "type": "checkbox",
                "checkbox": new_status
            }
        }
        
        if new_status:
            # If task is being completed, set completion date to now
            properties["CompletedAt"] = {
                "type": "date",
                "date": {
                    "start": now.isoformat()
                }
            }
        else:
            # If task is being uncompleted:
            # 1. Remove completion date
            # 2. Move task to today by updating CompletedAt to None
            properties["CompletedAt"] = {
                "type": "date",
                "date": None
            }
        
        # Add new order if determined
        if new_order is not None:
            properties["Order"] = {
                "type": "number",
                "number": new_order
            }

        # Update the page
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
    categories = get_categories()
    now = get_utc_now()
    today = now.date()
    
    # Dictionary to store todos grouped by day and category
    grouped_todos = {}
    
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
            
            # Get category from select field
            category = todo['properties'].get('Category', {}).get('select', {})
            category_name = category.get('name', '') if category else 'Uncategorized'
            
            # Get completion status and date
            is_completed = todo['properties'].get('Status', {}).get('checkbox', False)
            completed_at = todo['properties'].get('CompletedAt', {}).get('date', {})
            completed_date = None
            if completed_at and completed_at.get('start'):
                completed_date = datetime.fromisoformat(completed_at['start'].replace('Z', '+00:00')).astimezone(pytz.UTC)
            
            # Format the todo
            formatted_todo = {
                'id': todo['id'],
                'title': title_content,
                'description': description_content,
                'category': category_name,
                'completed': is_completed,
                'created_at': datetime.fromisoformat(todo['created_time'].replace('Z', '+00:00')).astimezone(pytz.UTC),
                'completed_at': completed_date,
                'deadline': deadline_date,
                'order': todo['properties'].get('Order', {}).get('number', 0)
            }
            
            # Determine which day to show the todo
            if is_completed and completed_date:
                display_date = completed_date.date()
            else:
                display_date = today
            
            day_str = display_date.strftime('%Y-%m-%d')
            
            # Initialize the day if it doesn't exist
            if day_str not in grouped_todos:
                grouped_todos[day_str] = {
                    'date': display_date,
                    'categories': {}
                }
            
            # Initialize the category if it doesn't exist for this day
            if category_name not in grouped_todos[day_str]['categories']:
                grouped_todos[day_str]['categories'][category_name] = []
            
            # Add the todo to its category within the day
            grouped_todos[day_str]['categories'][category_name].append(formatted_todo)
            
        except Exception as e:
            print(f"Error formatting todo: {e}")
            continue
    
    # Sort days in reverse chronological order
    sorted_days = sorted(grouped_todos.items(), key=lambda x: x[1]['date'], reverse=True)
    
    # For each day, sort categories alphabetically and sort todos within categories
    for day_str, day_data in grouped_todos.items():
        # Sort categories alphabetically
        day_data['categories'] = dict(sorted(day_data['categories'].items()))
        
        # Sort todos within each category
        for category in day_data['categories'].values():
            category.sort(key=lambda x: (
                x['completed'],
                x['deadline'] if x['deadline'] else datetime.max.replace(tzinfo=pytz.UTC),
                x['completed_at'] if x['completed_at'] else x['created_at']
            ))
    
    return render_template('index.html', grouped_todos=sorted_days, categories=categories, now=now)

@app.route('/add', methods=['POST'])
def add():
    title = request.form.get('title')
    description = request.form.get('description', '')
    deadline = request.form.get('deadline', '')
    category = request.form.get('category', '')
    
    if title:
        if deadline:
            # Convert local time to UTC
            local_dt = datetime.fromisoformat(deadline)
            utc_dt = local_dt.astimezone(pytz.UTC).isoformat()
            create_todo(title, description, utc_dt, category if category else None)
        else:
            create_todo(title, description, None, category if category else None)
    return redirect(url_for('index'))

@app.route('/complete/<string:id>')
def complete(id):
    toggle_todo(id)
    return redirect(url_for('index'))

@app.route('/delete/<string:id>')
def delete(id):
    delete_todo(id)
    return redirect(url_for('index'))

@app.route('/move', methods=['POST'])
def move_todo():
    try:
        data = request.get_json()
        todo_id = data.get('todoId')
        new_category = data.get('newCategory')
        new_date = data.get('newDate')
        is_completed = data.get('isCompleted', False)
        
        success = True
        
        # Update category if changed
        if new_category is not None:
            success = success and update_todo_category(todo_id, new_category)
        
        # Update completion status and date if changed
        if new_date is not None:
            completion_date = datetime.fromisoformat(new_date) if new_date else None
            success = success and update_todo_completion(todo_id, is_completed, completion_date)
        
        return jsonify({"success": success})
    except Exception as e:
        print(f"Error in move_todo: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/edit', methods=['POST'])
def edit():
    todo_id = request.form.get('id')
    title = request.form.get('title')
    description = request.form.get('description', '')
    deadline = request.form.get('deadline', '')
    category = request.form.get('category', '')
    
    if todo_id and title:
        if deadline:
            # Convert local time to UTC
            local_dt = datetime.fromisoformat(deadline)
            utc_dt = local_dt.astimezone(pytz.UTC).isoformat()
            update_todo(todo_id, title, description, utc_dt, category)
        else:
            update_todo(todo_id, title, description, "", category)
            
    return redirect(url_for('index'))

def create_category(category_name):
    try:
        # First, get current database to retrieve existing categories
        database = notion.databases.retrieve(database_id=DATABASE_ID)
        current_options = database.get('properties', {}).get('Category', {}).get('select', {}).get('options', [])
        
        # Check if category already exists
        for option in current_options:
            if option.get('name') == category_name:
                return {"id": option.get('id'), "name": option.get('name')}
        
        # Add new category to existing ones
        updated_options = current_options + [{"name": category_name}]
        
        # Update database with all categories
        database = notion.databases.update(
            database_id=DATABASE_ID,
            properties={
                "Category": {
                    "select": {
                        "options": updated_options
                    }
                }
            }
        )
        
        # Get the newly created category's details
        category_options = database.get('properties', {}).get('Category', {}).get('select', {}).get('options', [])
        for option in category_options:
            if option.get('name') == category_name:
                return {"id": option.get('id'), "name": option.get('name')}
        return None
    except Exception as e:
        print(f"Error creating category: {e}")
        return None

@app.route('/create-category', methods=['POST'])
def add_category():
    try:
        data = request.get_json()
        category_name = data.get('name')
        if not category_name:
            return jsonify({"success": False, "error": "Category name is required"}), 400
            
        result = create_category(category_name)
        if result:
            return jsonify({"success": True, "category": result})
        return jsonify({"success": False, "error": "Failed to create category"}), 500
    except Exception as e:
        print(f"Error in add_category: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    if not NOTION_TOKEN or not DATABASE_ID:
        print("Error: Please set NOTION_TOKEN and NOTION_DATABASE_ID in .env file")
    else:
        app.run(debug=True) 