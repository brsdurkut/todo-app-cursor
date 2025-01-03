# Todo Application

A Flask-based todo application integrated with Notion API, featuring a modern UI with drag & drop functionality, recurring tasks, and dark/light theme support.

## Features

### Task Management
- Add, edit, delete, and complete/uncomplete tasks
- Rich task details including title, description, category, and deadline
- Mark tasks as complete/incomplete with visual feedback
- Automatic task organization by completion status
- Improved drag & drop functionality with smoother animations
- Enhanced error handling for concurrent updates
- Optimized task updates with retry mechanism

### Recurring Tasks
- Create recurring tasks with different patterns:
  - Daily
  - Weekly
  - Monthly
  - Custom intervals (e.g., every 2 weeks)
- Automatic task generation based on recurrence pattern
- Separate page for managing recurring tasks
- Background scheduler for task generation
- Category support for recurring tasks
- Improved task generation reliability

### Organization
- Tasks automatically grouped by day and category
- Drag & drop support for:
  - Moving tasks between categories
  - Moving tasks between days (automatically handles completion status)
- Completed tasks shown in their completion day
- Incomplete tasks always shown in today's list
- Enhanced category collapsing/expanding
- Improved task ordering within categories

### Categories
- Organize tasks with customizable categories
- Category selection when creating/editing tasks
- Visual category grouping in the interface
- Drag & drop between categories
- Create new categories on the fly while adding/editing tasks
- Smart category management (preserves existing categories)
- Category list in sidebar for quick reference
- Enhanced category validation

### Time Management
- Set deadlines for tasks
- Visual indicators for:
  - Urgent tasks (past deadline)
  - Upcoming deadlines (within 3 days)
  - Creation time for incomplete tasks
  - Completion time for completed tasks
- Improved date handling and timezone support
- Better deadline validation

### User Interface
- Clean, modern design with sidebar navigation
- Separate pages for tasks and recurring tasks
- Dark/light theme support with persistent preference
- Responsive layout
- Visual feedback for all interactions
- Modal dialogs for editing tasks and creating recurring tasks
- Drag & drop interface with improved animations
- Improved handling of long task titles and descriptions
- Consistent button placement and visibility
- Enhanced error messages and user feedback

### Performance & Reliability
- Optimized API calls with retry mechanism
- Improved error handling for concurrent updates
- Better state management
- Enhanced data validation
- Smoother animations and transitions
- Reduced API calls through smart caching
- Improved task synchronization

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

3. Create a `.env` file in the root directory and add your credentials:
```env
# Required
NOTION_TOKEN=your_notion_integration_token
NOTION_DATABASE_ID=your_database_id

# Optional - for additional security
FLASK_SECRET_KEY=your_secret_key_here  # Optional, defaults to a secure value if not set
```

4. Set up Notion Integration:
   1. Go to https://www.notion.so/my-integrations
   2. Click "New integration"
   3. Name your integration (e.g., "Todo App")
   4. Select the workspace where your database will live
   5. Copy the "Internal Integration Token" to your `.env` file

5. Create Notion Database:
   1. Create a new page in Notion
   2. Add a new database (full page)
   3. Add the following properties:
      - Title (title) - Default
      - Status (checkbox)
      - Description (rich_text)
      - Category (select)
      - Order (number)
      - Deadline (date)
      - CompletedAt (date)
      - IsRecurringTemplate (checkbox)
      - RecurrencePattern (select)
      - RecurrenceInterval (number)
      - LastGenerated (date)
      - RecurringParentId (rich_text)
   4. Copy the database ID from the URL:
      - URL format: `https://www.notion.so/{workspace}/{database_id}?v=...`
      - Copy the database_id part to your `.env` file

6. Connect Integration to Database:
   1. Open your database in Notion
   2. Click "..." menu in the top right
   3. Go to "Add connections"
   4. Find and select your integration
   5. Click "Confirm"

7. Run the application:
```bash
python app.py
```

8. Access the application:
   - Open http://localhost:5000 in your browser
   - Default port is 5000 unless specified otherwise

## Troubleshooting

### Common Issues

1. 403 Forbidden Error:
   - Verify your Notion token is correct
   - Ensure the integration is connected to your database
   - Check if all required properties exist in your database

2. Database Connection Issues:
   - Confirm database ID is correct
   - Ensure all required properties are present
   - Check property types match the specifications

3. Task Updates Not Working:
   - Verify your integration has write permissions
   - Check browser console for error messages
   - Ensure all required fields are properly formatted

4. Date/Time Issues:
   - Check your system timezone settings
   - Verify date formats in the database
   - Ensure proper UTC conversion

5. Concurrent Update Errors:
   - The app now includes retry mechanism
   - Wait a moment and try again
   - Check for any conflicting updates

## Technologies Used

- Python 3.7+
- Flask 3.0.0
- Flask-CORS 4.0.0
- Notion API (notion-client 2.2.1)
- APScheduler 3.10.4
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
- Create recurring tasks for regular activities

### Project Management
- Create and organize project milestones
- Assign tasks with specific deadlines
- Track project progress through task completion
- Maintain project documentation in Notion
- Group related tasks by category
- Set up recurring project meetings and reviews

### Academic Planning
- Manage course assignments and deadlines
- Organize study schedules
- Track research tasks and progress
- Coordinate group project tasks
- Categorize tasks by subject or priority
- Create recurring study sessions

### Event Planning
- Create checklists for event preparations
- Set deadlines for various event tasks
- Categorize tasks by event components
- Track completed and pending tasks
- Share event planning progress with stakeholders
- Set up recurring event maintenance tasks

## Security

The application includes several security features:
- CORS protection
- Secret key for session management
- Secure data handling
- XSS protection in templates
- Background job security
- Enhanced error handling
- Improved data validation

## License

This project is licensed under the MIT License. 