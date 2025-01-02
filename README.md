# Todo Application

A Flask-based todo application integrated with Notion API, featuring a modern UI with drag & drop functionality and dark/light theme support.

## Features

### Task Management
- Add, edit, delete, and complete/uncomplete tasks
- Rich task details including title, description, category, and deadline
- Mark tasks as complete/incomplete with visual feedback
- Automatic task organization by completion status

### Organization
- Tasks automatically grouped by day and category
- Drag & drop support for:
  - Moving tasks between categories
  - Moving tasks between days (automatically handles completion status)
- Completed tasks shown in their completion day
- Incomplete tasks always shown in today's list

### Categories
- Organize tasks with customizable categories
- Category selection when creating/editing tasks
- Visual category grouping in the interface
- Drag & drop between categories

### Time Management
- Set deadlines for tasks
- Visual indicators for:
  - Urgent tasks (past deadline)
  - Upcoming deadlines (within 3 days)
  - Creation time for incomplete tasks
  - Completion time for completed tasks

### User Interface
- Clean, modern design
- Dark/light theme support
- Responsive layout
- Visual feedback for all interactions
- Modal dialog for editing tasks
- Drag & drop interface

## Installation

1. Clone the repository:
```bash
git clone https://github.com/brsdurkut/todo-app-cursor.git
cd todo-app-cursor
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file and add your Notion API credentials:
```
NOTION_TOKEN=your_notion_token
NOTION_DATABASE_ID=your_database_id
```

4. Run the application:
```bash
python app.py
```

## Notion Database Configuration

Your Notion database should have the following properties:
- Title (title)
- Status (checkbox)
- Description (rich_text)
- Category (select)
- Order (number)
- Deadline (date)
- CompletedAt (date)

## Technologies Used

- Python 3.7+
- Flask
- Notion API
- HTML/CSS
- JavaScript
- Font Awesome icons
- Inter font family

## Use Cases

### Personal Task Management
- Keep track of daily tasks and routines
- Set deadlines for important assignments
- Categorize tasks by project or priority
- Monitor task completion status
- Organize tasks by completion date

### Project Management
- Create and organize project milestones
- Assign tasks with specific deadlines
- Track project progress through task completion
- Maintain project documentation in Notion
- Group related tasks by category

### Academic Planning
- Manage course assignments and deadlines
- Organize study schedules
- Track research tasks and progress
- Coordinate group project tasks
- Categorize tasks by subject or priority

### Event Planning
- Create checklists for event preparations
- Set deadlines for various event tasks
- Categorize tasks by event components
- Track completed and pending tasks
- Share event planning progress with stakeholders

## License

This project is licensed under the MIT License. 