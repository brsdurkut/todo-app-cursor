from flask import Flask, render_template, request, redirect, url_for, jsonify
from notion_client import Client
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import pytz
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
import time
import logging

load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Security settings
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')

# Notion API credentials
NOTION_TOKEN = os.getenv('NOTION_TOKEN')
DATABASE_ID = os.getenv('NOTION_DATABASE_ID')

notion = Client(auth=NOTION_TOKEN)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_utc_now():
    return datetime.now(pytz.UTC)

def get_todos():
    try:
        all_results = []
        has_more = True
        next_cursor = None
        
        while has_more:
            query_params = {
                "database_id": DATABASE_ID,
                "sorts": [
                    {
                        "property": "Status",
                        "direction": "ascending"
                    },
                    {
                        "property": "Order",
                        "direction": "ascending"
                    }
                ],
                "filter": {
                    "and": [
                        {
                            "property": "Title",
                            "title": {
                                "is_not_empty": True
                            }
                        },
                        {
                            "property": "IsLater",
                            "checkbox": {
                                "equals": False
                            }
                        }
                    ]
                },
                "page_size": 100
            }
            
            if next_cursor:
                query_params["start_cursor"] = next_cursor
            
            response = notion.databases.query(**query_params)
            results = response.get('results', [])
            all_results.extend(results)
            has_more = response.get('has_more', False)
            next_cursor = response.get('next_cursor')
        
        return all_results
    except Exception as e:
        print(f"Error fetching todos: {e}")
        return []

def get_later_todos():
    try:
        all_results = []
        has_more = True
        next_cursor = None
        
        while has_more:
            query_params = {
                "database_id": DATABASE_ID,
                "sorts": [
                    {
                        "property": "Status",
                        "direction": "ascending"
                    },
                    {
                        "property": "Order",
                        "direction": "ascending"
                    }
                ],
                "filter": {
                    "and": [
                        {
                            "property": "Title",
                            "title": {
                                "is_not_empty": True
                            }
                        },
                        {
                            "property": "IsLater",
                            "checkbox": {
                                "equals": True
                            }
                        }
                    ]
                },
                "page_size": 100
            }
            
            if next_cursor:
                query_params["start_cursor"] = next_cursor
            
            response = notion.databases.query(**query_params)
            results = response.get('results', [])
            all_results.extend(results)
            has_more = response.get('has_more', False)
            next_cursor = response.get('next_cursor')
        
        return all_results
    except Exception as e:
        print(f"Error fetching later todos: {e}")
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
        
        # Find the last incomplete todo's order
        last_incomplete_order = None
        for todo in todos:
            if not todo['properties'].get('Status', {}).get('checkbox', False):
                order_text = todo['properties'].get('Order', {}).get('rich_text', [{}])[0].get('text', {}).get('content', '')
                if order_text:
                    last_incomplete_order = order_text

        # Generate new order value
        new_order = get_lexorank_between(last_incomplete_order, None, False)
        logger.debug(f"Creating new todo with order {new_order}")

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
                "rich_text": [{"text": {"content": new_order}}]
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
        logger.error(f"Error creating todo: {e}")
        return False

def update_todo_order(page_id, new_order):
    try:
        notion.pages.update(
            page_id=page_id,
            properties={
                "Order": {
                    "rich_text": [{"text": {"content": new_order}}]
                }
            }
        )
        return True
    except Exception as e:
        logger.error(f"Error updating todo order: {e}")
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
            properties["CompletedAt"] = {
                "date": None
            }
            
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

def get_lexorank_between(prev_rank=None, next_rank=None, is_completed=False):
    """Generate a lexicographically ordered string rank between prev_rank and next_rank"""
    logger.debug(f"Generating lexorank: prev_rank={prev_rank}, next_rank={next_rank}, is_completed={is_completed}")
    
    BASE_36_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    MIN_RANK = "0"
    MAX_RANK = "ZZZZZZZZZZ"  # 10 characters max
    COMPLETED_PREFIX = "Z"  # Ensures completed tasks are always after incomplete ones
    
    # If no ranks provided, return middle of available range
    if not prev_rank and not next_rank:
        result = COMPLETED_PREFIX + "5" + "0" * 8 if is_completed else "5" + "0" * 9
        logger.debug(f"No ranks provided, returning middle rank: {result}")
        return result
    
    # Handle edge cases
    if not prev_rank:
        prev_rank = MIN_RANK if not is_completed else COMPLETED_PREFIX + MIN_RANK
        logger.debug(f"No prev_rank, using: {prev_rank}")
    if not next_rank:
        next_rank = MAX_RANK if is_completed else COMPLETED_PREFIX + MIN_RANK
        logger.debug(f"No next_rank, using: {next_rank}")
        
    # Ensure proper length
    prev_rank = prev_rank.ljust(10, '0')
    next_rank = next_rank.ljust(10, '0')
    logger.debug(f"Padded ranks: prev={prev_rank}, next={next_rank}")
    
    # If ranks are consecutive in BASE_36, create a mid rank
    if ord(next_rank[-1]) - ord(prev_rank[-1]) == 1:
        prev_rank = prev_rank[:-1] + BASE_36_CHARS[(BASE_36_CHARS.index(prev_rank[-1]) + 1) % 36]
        logger.debug(f"Adjusted consecutive ranks, new prev_rank: {prev_rank}")
    
    # Find the midpoint
    mid_rank = ""
    for i in range(10):
        prev_char = prev_rank[i] if i < len(prev_rank) else '0'
        next_char = next_rank[i] if i < len(next_rank) else 'Z'
        
        prev_index = BASE_36_CHARS.index(prev_char)
        next_index = BASE_36_CHARS.index(next_char)
        
        if next_index == prev_index:
            mid_rank += prev_char
            continue
            
        mid_index = (prev_index + next_index) // 2
        mid_rank += BASE_36_CHARS[mid_index]
        break
    
    # Pad to 10 characters
    mid_rank = mid_rank.ljust(10, '0')
    logger.debug(f"Generated mid_rank: {mid_rank}")
    
    # Add completed prefix if needed
    if is_completed and not mid_rank.startswith(COMPLETED_PREFIX):
        mid_rank = COMPLETED_PREFIX + mid_rank[1:]
        logger.debug(f"Added completed prefix, final rank: {mid_rank}")
        
    return mid_rank

@app.route('/reorder', methods=['POST'])
def reorder():
    try:
        data = request.get_json()
        todos = data.get('todos', [])
        logger.info(f"Reordering {len(todos)} todos")
        
        # Update orders with retry mechanism
        prev_rank = None
        for todo_id in todos:
            try:
                # Get current todo status
                page = notion.pages.retrieve(page_id=todo_id)
                is_completed = page['properties']['Status']['checkbox']
                
                # Generate new rank
                new_rank = get_lexorank_between(prev_rank, None, is_completed)
                logger.debug(f"Updating todo {todo_id} with rank {new_rank} (prev_rank={prev_rank})")
                
                # Update the todo with new rank
                success = update_notion_with_retry(
                    todo_id,
                    {
                        "Order": {
                            "rich_text": [{"text": {"content": new_rank}}]
                        }
                    }
                )
                
                if not success:
                    logger.error(f"Failed to update order for todo {todo_id}")
                    return jsonify({"success": False, "error": f"Failed to update order for todo {todo_id}"}), 500
                
                prev_rank = new_rank
                
            except Exception as e:
                logger.error(f"Error updating todo {todo_id}: {e}")
                return jsonify({"success": False, "error": f"Error updating todo {todo_id}: {e}"}), 500
        
        logger.info("Reordering completed successfully")
        return jsonify({"success": True})
        
    except Exception as e:
        logger.error(f"Error in reorder: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

def toggle_todo(page_id):
    try:
        # Get current status and current date
        page = notion.pages.retrieve(page_id=page_id)
        current_status = page['properties']['Status']['checkbox']
        now = get_utc_now()
        
        # Toggle status
        new_status = not current_status
        
        # Get all todos to determine new order
        todos = get_todos()
        
        # Find appropriate order value
        new_order = None
        if new_status:  # If task is being completed
            # Find the last completed task's order
            last_completed_order = None
            for todo in todos:
                if todo['properties'].get('Status', {}).get('checkbox', True):
                    order_text = todo['properties'].get('Order', {}).get('rich_text', [{}])[0].get('text', {}).get('content', '')
                    if order_text:
                        last_completed_order = order_text
            new_order = get_lexorank_between(last_completed_order, None, True)
        else:  # If task is being uncompleted
            # Find the last incomplete task's order
            last_incomplete_order = None
            for todo in todos:
                if not todo['properties'].get('Status', {}).get('checkbox', False):
                    order_text = todo['properties'].get('Order', {}).get('rich_text', [{}])[0].get('text', {}).get('content', '')
                    if order_text:
                        last_incomplete_order = order_text
            new_order = get_lexorank_between(last_incomplete_order, None, False)
        
        logger.debug(f"Toggling todo {page_id} to {new_status} with new order {new_order}")
        
        # Prepare properties update
        properties = {
            "Status": {
                "checkbox": new_status
            },
            "Order": {
                "rich_text": [{"text": {"content": new_order}}]
            }
        }
        
        if new_status:
            # If task is being completed, set completion date to now
            properties["CompletedAt"] = {
                "date": {
                    "start": now.isoformat()
                }
            }
        else:
            # If task is being uncompleted, remove completion date
            properties["CompletedAt"] = {
                "date": None
            }
        
        # Update the page
        notion.pages.update(
            page_id=page_id,
            properties=properties
        )
        return True
    except Exception as e:
        logger.error(f"Error toggling todo: {e}")
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
    
    # Get user's local timezone
    local_tz = pytz.timezone('Europe/Istanbul')  # Türkiye için
    today = now.astimezone(local_tz).date()
    
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
                deadline_date = datetime.fromisoformat(deadline['start'].replace('Z', '+00:00')).astimezone(local_tz)
            
            # Get category from select field
            category = todo['properties'].get('Category', {}).get('select', {})
            category_name = category.get('name', '') if category else 'Uncategorized'
            
            # Get completion status and date
            is_completed = todo['properties'].get('Status', {}).get('checkbox', False)
            completed_at = todo['properties'].get('CompletedAt', {}).get('date', {})
            completed_date = None
            if completed_at and completed_at.get('start'):
                # Parse the completion date and ensure it's in UTC
                completed_str = completed_at['start']
                # Fix malformed UTC offset by removing any duplicate +00:00
                if completed_str.count('+00:00') > 1:
                    completed_str = completed_str.replace('+00:00', '', completed_str.count('+00:00') - 1)
                if not completed_str.endswith('Z') and not completed_str.endswith('+00:00'):
                    completed_str += 'Z'
                completed_date = datetime.fromisoformat(completed_str.replace('Z', '+00:00')).astimezone(local_tz)
            
            # Format the todo
            formatted_todo = {
                'id': todo['id'],
                'title': title_content,
                'description': description_content,
                'category': category_name,
                'completed': is_completed,
                'created_at': datetime.fromisoformat(todo['created_time'].replace('Z', '+00:00')).astimezone(local_tz),
                'completed_at': completed_date,
                'deadline': deadline_date,
                'order': todo['properties'].get('Order', {}).get('rich_text', [{}])[0].get('text', {}).get('content', '0')
            }
            
            # Determine which day to show the todo
            if is_completed and completed_date:
                display_date = completed_date.date()
            elif deadline_date and deadline_date.date() >= today:
                display_date = deadline_date.date()
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
        # Sort categories with Uncategorized always first, then alphabetically
        day_data['categories'] = dict(sorted(
            day_data['categories'].items(),
            key=lambda x: ('1' if x[0] == '' or x[0] == 'Uncategorized' else '2' + x[0].lower())
        ))
        
        # Sort todos within each category
        for category in day_data['categories'].values():
            category.sort(key=lambda x: (
                x['completed'],
                x['order'],
                x['deadline'] if x['deadline'] else datetime.max.replace(tzinfo=pytz.UTC),
                x['completed_at'] if x['completed_at'] else x['created_at']
            ))
    
    return render_template('index.html', grouped_todos=sorted_days, categories=categories, now=now)

@app.route('/recurring')
def recurring_tasks_page():
    tasks = get_recurring_tasks()
    formatted_tasks = []
    
    for task in tasks:
        try:
            properties = task.get('properties', {})
            
            # Get title
            title = properties.get('Title', {})
            title_content = ''
            if title and title.get('title') and len(title['title']) > 0:
                title_content = title['title'][0].get('text', {}).get('content', 'Untitled')
            
            # Get pattern and interval
            pattern_obj = properties.get('RecurrencePattern', {}).get('select', {})
            pattern = pattern_obj.get('name', 'daily') if pattern_obj else 'daily'
            
            interval = properties.get('RecurrenceInterval', {}).get('number', 1)
            
            # Get category
            category_obj = properties.get('Category', {}).get('select', {})
            category = category_obj.get('name', '') if category_obj else ''
            
            formatted_tasks.append({
                'id': task.get('id', ''),
                'title': title_content,
                'pattern': pattern,
                'interval': interval,
                'category': category
            })
        except Exception as e:
            print(f"Error formatting recurring task: {str(e)}")
            continue
    
    categories = get_categories()
    return render_template('recurring.html', tasks=formatted_tasks, categories=categories)

@app.route('/add', methods=['POST'])
def add():
    title = request.form.get('title')
    description = request.form.get('description', '')
    deadline = request.form.get('deadline', '')
    category = request.form.get('category', '')
    
    if title:
        if deadline:
            # Convert local time to UTC
            local_tz = pytz.timezone('Europe/Istanbul')
            local_dt = datetime.fromisoformat(deadline)
            local_dt = local_tz.localize(local_dt)
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

def update_notion_with_retry(page_id, properties, max_retries=3, delay=0.5):
    for attempt in range(max_retries):
        try:
            logger.debug(f"Updating notion page {page_id} (attempt {attempt + 1}/{max_retries})")
            logger.debug(f"Properties: {properties}")
            
            notion.pages.update(
                page_id=page_id,
                properties=properties
            )
            logger.debug(f"Successfully updated page {page_id}")
            return True
        except Exception as e:
            if "Conflict" in str(e) and attempt < max_retries - 1:
                logger.warning(f"Conflict error updating page {page_id}, retrying in {delay * (attempt + 1)}s")
                time.sleep(delay * (attempt + 1))  # Exponential backoff
                continue
            logger.error(f"Error updating todo (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                raise
    return False

@app.route('/move', methods=['POST'])
def move_todo():
    try:
        data = request.get_json()
        todo_id = data.get('todoId')
        new_category = data.get('newCategory')
        new_date = data.get('newDate')
        is_completed = data.get('isCompleted', False)
        
        # Prepare properties for a single update
        properties = {}
        
        # Add category update if needed
        if new_category is not None:
            properties["Category"] = {
                "select": {
                    "name": new_category
                } if new_category != "Uncategorized" else None
            }
        
        # Add completion status and date if needed
        if new_date is not None:
            try:
                completion_date = datetime.fromisoformat(new_date) if new_date else None
                if completion_date:
                    # Convert to UTC if it's not already
                    if not completion_date.tzinfo:
                        local_tz = pytz.timezone('Europe/Istanbul')
                        completion_date = local_tz.localize(completion_date).astimezone(pytz.UTC)
                
                properties["Status"] = {
                    "checkbox": is_completed
                }
                
                if is_completed and completion_date:
                    properties["CompletedAt"] = {
                        "date": {
                            "start": completion_date.isoformat()
                        }
                    }
                else:
                    properties["CompletedAt"] = {
                        "date": None
                    }
            except ValueError as e:
                print(f"Error parsing date: {e}")
                return jsonify({"success": False, "error": "Invalid date format"}), 400
        
        # Make a single API call to update everything with retry logic
        if properties:
            try:
                success = update_notion_with_retry(todo_id, properties)
                if success:
                    time.sleep(0.1)  # Small delay to prevent rapid consecutive updates
                    return jsonify({"success": True})
                return jsonify({"success": False, "error": "Failed to update after retries"}), 500
            except Exception as e:
                print(f"Error updating todo: {e}")
                return jsonify({"success": False, "error": str(e)}), 500
        
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error in move_todo: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/edit', methods=['POST'])
def edit():
    try:
        todo_id = request.form.get('id')
        title = request.form.get('title')
        description = request.form.get('description', '')
        deadline = request.form.get('deadline', '')
        category = request.form.get('category', '')
        
        if todo_id and title:
            if deadline:
                # Convert local time to UTC
                local_tz = pytz.timezone('Europe/Istanbul')
                local_dt = datetime.fromisoformat(deadline)
                local_dt = local_tz.localize(local_dt)
                utc_dt = local_dt.astimezone(pytz.UTC).isoformat()
                success = update_todo(todo_id, title, description, utc_dt, category)
            else:
                success = update_todo(todo_id, title, description, "", category)
                
            if not success:
                return jsonify({"success": False, "error": "Failed to update todo"}), 500
                
        return redirect(url_for('index'))
    except Exception as e:
        print(f"Error in edit: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

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

def get_recurring_tasks():
    try:
        response = notion.databases.query(
            database_id=DATABASE_ID,
            filter={
                "and": [
                    {
                        "property": "IsRecurringTemplate",
                        "checkbox": {
                            "equals": True
                        }
                    },
                    {
                        "property": "Title",
                        "title": {
                            "is_not_empty": True
                        }
                    }
                ]
            }
        )
        return response.get('results', [])
    except Exception as e:
        print(f"Error fetching recurring tasks: {e}")
        return []

def create_recurring_task(title, description="", category_name=None, recurrence_pattern="daily", interval=1, interval_unit="days"):
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
            },
            "IsRecurringTemplate": {
                "checkbox": True
            },
            "RecurrencePattern": {
                "select": {
                    "name": recurrence_pattern
                }
            },
            "RecurrenceInterval": {
                "number": interval
            },
            "LastGenerated": {
                "date": {
                    "start": get_utc_now().isoformat()
                }
            }
        }

        if category_name:
            properties["Category"] = {
                "select": {
                    "name": category_name
                }
            }

        # Create the recurring task template
        response = notion.pages.create(
            parent={"database_id": DATABASE_ID},
            properties=properties
        )

        # Generate the first instance
        generate_task_instance(response['id'])
        
        return True
    except Exception as e:
        print(f"Error creating recurring task: {e}")
        return False

def generate_task_instance(template_id):
    try:
        # Get the template task
        template = notion.pages.retrieve(page_id=template_id)
        
        # Get properties from template
        title = template['properties']['Title']['title'][0]['text']['content']
        description = template['properties']['Description']['rich_text'][0]['text']['content'] if template['properties']['Description']['rich_text'] else ""
        category = template['properties'].get('Category', {}).get('select', {}).get('name')
        
        # Create the task instance
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
            "RecurringParentId": {
                "rich_text": [
                    {
                        "text": {
                            "content": template_id
                        }
                    }
                ]
            }
        }

        if category:
            properties["Category"] = {
                "select": {
                    "name": category
                }
            }

        # Create the task instance
        notion.pages.create(
            parent={"database_id": DATABASE_ID},
            properties=properties
        )

        # Update LastGenerated date on template
        notion.pages.update(
            page_id=template_id,
            properties={
                "LastGenerated": {
                    "date": {
                        "start": get_utc_now().isoformat()
                    }
                }
            }
        )

        return True
    except Exception as e:
        print(f"Error generating task instance: {e}")
        return False

def check_recurring_tasks():
    try:
        recurring_tasks = get_recurring_tasks()
        now = get_utc_now()
        
        for task in recurring_tasks:
            last_generated = task['properties'].get('LastGenerated', {}).get('date', {}).get('start')
            if not last_generated:
                continue
                
            last_generated = datetime.fromisoformat(last_generated.replace('Z', '+00:00'))
            pattern = task['properties'].get('RecurrencePattern', {}).get('select', {}).get('name', 'daily')
            interval = task['properties'].get('RecurrenceInterval', {}).get('number', 1)
            
            # Calculate next generation date
            if pattern == 'daily':
                next_date = last_generated + timedelta(days=interval)
            elif pattern == 'weekly':
                next_date = last_generated + timedelta(weeks=interval)
            elif pattern == 'monthly':
                # Add months by adding days (approximate)
                next_date = last_generated + timedelta(days=30 * interval)
            else:  # custom
                # Default to daily if pattern is invalid
                next_date = last_generated + timedelta(days=interval)
            
            # If it's time to generate a new instance
            if now >= next_date:
                generate_task_instance(task['id'])
    except Exception as e:
        print(f"Error checking recurring tasks: {e}")

# Initialize the scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=check_recurring_tasks, trigger="interval", minutes=30)
scheduler.start()

@app.route('/recurring-tasks')
def get_recurring_tasks_route():
    tasks = get_recurring_tasks()
    formatted_tasks = []
    
    for task in tasks:
        try:
            properties = task.get('properties', {})
            
            # Get title
            title = properties.get('Title', {})
            title_content = ''
            if title and title.get('title') and len(title['title']) > 0:
                title_content = title['title'][0].get('text', {}).get('content', 'Untitled')
            
            # Get pattern and interval
            pattern_obj = properties.get('RecurrencePattern', {}).get('select', {})
            pattern = pattern_obj.get('name', 'daily') if pattern_obj else 'daily'
            
            interval = properties.get('RecurrenceInterval', {}).get('number', 1)
            
            # Get category
            category_obj = properties.get('Category', {}).get('select', {})
            category = category_obj.get('name', '') if category_obj else ''
            
            formatted_tasks.append({
                'id': task.get('id', ''),
                'title': title_content,
                'pattern': pattern,
                'interval': interval,
                'category': category
            })
        except Exception as e:
            print(f"Error formatting recurring task: {str(e)}")
            continue
    
    return jsonify(formatted_tasks)

@app.route('/add-recurring', methods=['POST'])
def add_recurring():
    title = request.form.get('title')
    description = request.form.get('description', '')
    category = request.form.get('category', '')
    pattern = request.form.get('recurrence_pattern', 'daily')
    
    interval = 1
    if pattern == 'custom':
        try:
            interval = int(request.form.get('interval', 1))
            interval_unit = request.form.get('interval_unit', 'days')
            pattern = f"every_{interval}_{interval_unit}"
        except ValueError:
            interval = 1
    
    if title:
        create_recurring_task(
            title=title,
            description=description,
            category_name=category if category else None,
            recurrence_pattern=pattern,
            interval=interval
        )
    
    return redirect(url_for('index'))

@app.route('/delete-recurring/<string:id>')
def delete_recurring(id):
    try:
        # Archive the template
        notion.pages.update(
            page_id=id,
            archived=True
        )
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error deleting recurring task: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/later')
def later_tasks():
    todos = get_later_todos()
    categories = get_categories()
    now = get_utc_now()
    
    # Get user's local timezone
    local_tz = pytz.timezone('Europe/Istanbul')
    today = now.astimezone(local_tz).date()
    
    # Dictionary to store todos grouped by category
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
                deadline_date = datetime.fromisoformat(deadline['start'].replace('Z', '+00:00')).astimezone(local_tz)
            
            # Get category
            category = todo['properties'].get('Category', {}).get('select', {})
            category_name = category.get('name', '') if category else 'Uncategorized'
            
            # Get completion status
            is_completed = todo['properties'].get('Status', {}).get('checkbox', False)
            
            # Format the todo
            formatted_todo = {
                'id': todo['id'],
                'title': title_content,
                'description': description_content,
                'category': category_name,
                'completed': is_completed,
                'deadline': deadline_date,
                'order': todo['properties'].get('Order', {}).get('rich_text', [{}])[0].get('text', {}).get('content', '0')
            }
            
            # Initialize the category if it doesn't exist
            if category_name not in grouped_todos:
                grouped_todos[category_name] = []
            
            # Add the todo to its category
            grouped_todos[category_name].append(formatted_todo)
            
        except Exception as e:
            print(f"Error formatting todo: {e}")
            continue
    
    # Sort categories with Uncategorized always first
    sorted_categories = dict(sorted(
        grouped_todos.items(),
        key=lambda x: ('1' if x[0] == '' or x[0] == 'Uncategorized' else '2' + x[0].lower())
    ))
    
    return render_template('later.html', grouped_todos=sorted_categories, categories=categories, now=now)

@app.route('/toggle-later/<string:id>')
def toggle_later_route(id):
    toggle_later(id)
    referrer = request.referrer
    if referrer and 'later' in referrer:
        return redirect(url_for('later_tasks'))
    return redirect(url_for('index'))

def toggle_later(page_id):
    try:
        # Get current later status
        page = notion.pages.retrieve(page_id=page_id)
        current_status = page['properties'].get('IsLater', {}).get('checkbox', False)
        
        # Toggle status
        new_status = not current_status
        
        # Update the page
        notion.pages.update(
            page_id=page_id,
            properties={
                "IsLater": {
                    "checkbox": new_status
                }
            }
        )
        
        # If removing from later, update the order for current day
        if not new_status:
            todos = get_todos()
            last_incomplete_order = None
            for todo in todos:
                if not todo['properties'].get('Status', {}).get('checkbox', False):
                    order_text = todo['properties'].get('Order', {}).get('rich_text', [{}])[0].get('text', {}).get('content', '')
                    if order_text:
                        last_incomplete_order = order_text
            
            new_order = get_lexorank_between(last_incomplete_order, None, False)
            
            notion.pages.update(
                page_id=page_id,
                properties={
                    "Order": {
                        "rich_text": [{"text": {"content": new_order}}]
                    }
                }
            )
        
        return True
    except Exception as e:
        logger.error(f"Error toggling later status: {e}")
        return False

if __name__ == '__main__':
    if not NOTION_TOKEN or not DATABASE_ID:
        print("Error: Please set NOTION_TOKEN and NOTION_DATABASE_ID in .env file")
    else:
        app.run(debug=True) 