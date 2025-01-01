# Todo Application

A Flask-based todo application integrated with Notion API.

## Features

- Add, delete, and complete tasks
- Notion synchronization
- Task descriptions and deadlines
- Organize tasks by categories
- Drag-and-drop task ordering
- Dark/Light theme support

## Installation

1. Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/todo-app.git
cd todo-app
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
- Category (rich_text)
- Order (number)
- Deadline (date)

## Technologies Used

- Python 3.7+
- Flask
- Notion API
- HTML/CSS
- JavaScript

## License

This project is licensed under the MIT License. 