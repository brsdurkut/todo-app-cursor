# Notion Todo App

A Flask-based todo application that integrates with Notion API to manage tasks effectively.

## Features

- **Task Organization**:
  - "Today" section for immediate tasks
  - "This Week" section for upcoming tasks
  - Drag and drop support between sections
  - Category-based organization
  - Completed tasks view

- **Task Management**:
  - Create, edit, and delete tasks
  - Add deadlines and categories
  - Mark tasks as complete/incomplete
  - Move tasks to "Later" list
  - Drag and drop reordering

- **Categories**:
  - Create and manage categories
  - Group tasks by categories
  - Uncategorized tasks support

- **Recurring Tasks**:
  - Create recurring task templates
  - Daily, weekly, monthly patterns
  - Custom intervals support
  - Automatic task generation

- **User Interface**:
  - Clean and modern design
  - Dark/Light theme support
  - Responsive layout
  - Intuitive drag and drop
  - Category collapsing/expanding

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file with your Notion credentials:
   ```
   NOTION_TOKEN=your_integration_token
   NOTION_DATABASE_ID=your_database_id
   FLASK_SECRET_KEY=your_secret_key
   ```
4. Run the application:
   ```bash
   python app.py
   ```

## Notion Database Setup

The application requires a Notion database with the following properties:

- Title (title): Task title
- Description (rich_text): Task description
- Status (checkbox): Task completion status
- Category (select): Task category
- Deadline (date): Task due date
- Order (rich_text): Task order
- IsLater (checkbox): Later status flag
- CompletedAt (date): Completion timestamp
- IsRecurringTemplate (checkbox): Recurring task flag
- RecurrencePattern (select): Recurrence pattern
- RecurrenceInterval (number): Recurrence interval
- LastGenerated (date): Last generation date
- RecurringParentId (rich_text): Parent template reference

## Contributing

Feel free to submit issues and enhancement requests. 