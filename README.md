# Voice To-Do & Timetable Assistant for Placement Preparation

This project is a voice-controlled assistant to help you manage your placement preparation, daily tasks, and custom study timetable. It provides reminders, recurring tasks, deadline alerts, and more—all with voice interaction.

## Features
- **Add, update, remove, and list tasks** (with deadline, priority, category, and recurrence)
- **Recurring tasks** (daily or weekly, auto-reset)
- **Custom timetable** (add, update, remove, and list study sessions)
- **Voice reminders for scheduled study times**
- **Deadline and overdue alerts**
- **Search and filter tasks** (by keyword, deadline, priority, or category)
- **Voice interaction for all commands**

## Setup
1. **Install Python 3.8+**
2. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   pip install pygame gtts
   ```
3. **Run the assistant:**
   ```sh
   python main.py
   ```

## Usage
- **Add a task:**
  - `add task coding practice with deadline 2024-07-01 and priority high in category placement recurring daily`
- **List tasks:**
  - `list tasks`
- **Mark a task as done:**
  - `I have completed coding practice`
- **Add a timetable entry:**
  - `add timetable monday 7pm aptitude practice`
- **Show timetable:**
  - `show timetable`
- **Start monitoring for study reminders:**
  - `run`
- **Search/filter tasks:**
  - `search task coding`
  - `filter tasks by category placement`

## Data Storage
- All tasks and timetable entries are stored in `todo_data.json` in the project directory.

## Notes
- The assistant uses your microphone and speakers for voice interaction.
- If you have issues with system voices, the assistant will use Google Text-to-Speech (gTTS) as a fallback.
- Timetable monitoring will alert you when it’s time for a scheduled study session.

## Example Workflow
1. Add your study tasks and deadlines.
2. Set up your weekly study timetable.
3. Start the assistant and say `run` to get reminders.
4. Mark tasks as done as you complete them.
5. Use search and filter to quickly find or review tasks.

---

**Happy Placement Preparation!** 