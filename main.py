import speech_recognition as sr
import pyttsx3
import json
import os
import sys
import re
import pygame
from gtts import gTTS
import tempfile
import datetime
import time
import spacy
import threading
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

# === Voice Engine Setup ===
engine = pyttsx3.init()

def speak(text, voice_gender=None):
    print("Assistant:", text)
    tts_success = False
    try:
        if voice_gender:
            voices = engine.getProperty('voices')
            selected_voice = None
            for v in voices:
                if voice_gender.lower() == "female" and getattr(v, 'gender', '').lower() == "female":
                    selected_voice = v.id
                    break
                elif voice_gender.lower() == "male" and getattr(v, 'gender', '').lower() == "male":
                    selected_voice = v.id
                    break
            if selected_voice:
                engine.setProperty('voice', selected_voice)
        engine.say(text)
        engine.runAndWait()
        tts_success = True
        if voice_gender:
            engine.setProperty('voice', engine.getProperty('voices')[0].id)
    except Exception:
        tts_success = False
    if not tts_success:
        try:
            tts = gTTS(text=text, lang='en')
            with tempfile.NamedTemporaryFile(delete=True, suffix='.mp3') as fp:
                tts.save(fp.name)
                pygame.mixer.init()
                pygame.mixer.music.load(fp.name)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    continue
        except Exception as e:
            print(f"[ERROR] Could not play sound: {e}")

# === Load or Initialize Tasks ===
TASK_FILE = "todo_data.json"

def load_tasks():
    if not os.path.exists(TASK_FILE):
        return {}
    with open(TASK_FILE, "r") as f:
        data = json.load(f)
        # Migrate old format (if any) to new format
        for k, v in data.items():
            if isinstance(v, bool):
                data[k] = {"done": v, "deadline": None, "priority": None}
        return data

def save_tasks(tasks):
    with open(TASK_FILE, "w") as f:
        json.dump(tasks, f, indent=4)

# === Load or Initialize Timetable ===
TIMETABLE_KEY = "__timetable__"

def load_timetable(tasks):
    return tasks.get(TIMETABLE_KEY, [])

def save_timetable(tasks, timetable):
    tasks[TIMETABLE_KEY] = timetable

# === Process User Input ===
nlp = spacy.load('en_core_web_sm')

def process_input(text, tasks):
    text = text.lower()
    doc = nlp(text)
    # Conversational 'add task' intent
    if any(t.lemma_ in ['add', 'create', 'remind'] for t in doc) and 'task' in text:
        # Try to extract task name and details
        task_name = None
        deadline = None
        priority = None
        category = None
        recurring = None
        for ent in doc.ents:
            if ent.label_ == 'DATE':
                deadline = ent.text
            if ent.label_ == 'TIME':
                # Could be used for deadline or timetable
                pass
        # Find the task name (after 'task' or 'to')
        if 'task' in text:
            after_task = text.split('task', 1)[-1].strip()
            if after_task:
                task_name = after_task.split(' with ')[0].split(' in ')[0].split(' for ')[0].split(' every ')[0].strip()
        if not task_name:
            # Try after 'to'
            if 'to' in text:
                task_name = text.split('to', 1)[-1].strip()
        # Recurring
        if 'every day' in text or 'daily' in text:
            recurring = 'daily'
        elif 'every week' in text or 'weekly' in text:
            recurring = 'weekly'
        # Priority
        if 'high priority' in text or 'important' in text:
            priority = 'high'
        elif 'medium priority' in text:
            priority = 'medium'
        elif 'low priority' in text:
            priority = 'low'
        # Category
        if 'placement' in text:
            category = 'placement'
        if task_name:
            # Try to parse deadline to YYYY-MM-DD if possible
            import dateutil.parser
            if deadline:
                try:
                    deadline_parsed = dateutil.parser.parse(deadline, fuzzy=True)
                    deadline = deadline_parsed.strftime('%Y-%m-%d')
                except Exception:
                    pass
            if task_name in tasks:
                return f"'{task_name}' is already in your to-do list."
            tasks[task_name] = {"done": False, "deadline": deadline, "priority": priority, "category": category, "recurring": recurring}
            msg = f"Added '{task_name}' to your to-do list."
            if deadline:
                msg += f" Deadline: {deadline}."
            if priority:
                msg += f" Priority: {priority}."
            if category:
                msg += f" Category: {category}."
            if recurring:
                msg += f" Recurring: {recurring}."
            return msg
        else:
            return "Please specify the task to add."
    # Conversational 'list tasks' intent
    if any(t.lemma_ in ['list', 'show', 'what'] for t in doc) and 'task' in text:
        if not tasks:
            return "Your to-do list is empty."
        response = "Here are your tasks:\n"
        for task, info in tasks.items():
            if not isinstance(info, dict):
                continue
            status = "done" if info["done"] else "not done"
            deadline = f", deadline: {info.get('deadline')}" if info.get("deadline") else ""
            priority = f", priority: {info.get('priority')}" if info.get("priority") else ""
            category = f", category: {info.get('category')}" if info.get("category") else ""
            recurring = f", recurring: {info.get('recurring')}" if info.get("recurring") else ""
            # Highlight overdue and due-soon tasks
            highlight = ""
            if info.get('deadline'):
                try:
                    due_date = datetime.datetime.strptime(info['deadline'], '%Y-%m-%d').date()
                    today = datetime.datetime.now().date()
                    soon = today + datetime.timedelta(days=1)
                    if not info["done"] and due_date < today:
                        highlight = " [OVERDUE]"
                    elif not info["done"] and today <= due_date <= soon:
                        highlight = " [DUE SOON]"
                except Exception:
                    pass
            response += f"- {task} [{status}{deadline}{priority}{category}{recurring}]{highlight}\n"
        return response.strip()
    # Filter tasks by deadline, priority, or category
    filter_match = re.match(r"filter tasks by (deadline|priority|category) (.+)", text)
    if filter_match:
        field = filter_match.group(1)
        value = filter_match.group(2).strip()
        results = []
        for task, info in tasks.items():
            if not isinstance(info, dict):
                continue
            if info.get(field) and value in str(info[field]).lower():
                results.append(task)
        if results:
            return f"Tasks with {field} '{value}': {', '.join(results)}."
        else:
            return f"No tasks found with {field} '{value}'."
    # Add task with deadline, priority, category, and/or recurrence
    add_match = re.match(r"add task (.+?)( with deadline (.+?))?( and priority (.+?))?( in category (.+?))?( recurring (daily|weekly))?$", text)
    if add_match:
        task_name = add_match.group(1).strip()
        deadline = add_match.group(3).strip() if add_match.group(3) else None
        priority = add_match.group(5).strip() if add_match.group(5) else None
        category = add_match.group(7).strip() if add_match.group(7) else None
        recurring = add_match.group(9).strip() if add_match.group(9) else None
        if not task_name:
            return "Please specify the task to add."
        if task_name in tasks:
            return f"'{task_name}' is already in your to-do list."
        tasks[task_name] = {"done": False, "deadline": deadline, "priority": priority, "category": category, "recurring": recurring}
        msg = f"Added '{task_name}' to your to-do list."
        if deadline:
            msg += f" Deadline: {deadline}."
        if priority:
            msg += f" Priority: {priority}."
        if category:
            msg += f" Category: {category}."
        if recurring:
            msg += f" Recurring: {recurring}."
        return msg
    # Update deadline, priority, category, or recurrence for existing task
    update_match = re.match(r"update task (.+?)( deadline to (.+?))?( priority to (.+?))?( category to (.+?))?( recurring to (daily|weekly))?$", text)
    if update_match:
        task_name = update_match.group(1).strip()
        deadline = update_match.group(3).strip() if update_match.group(3) else None
        priority = update_match.group(5).strip() if update_match.group(5) else None
        category = update_match.group(7).strip() if update_match.group(7) else None
        recurring = update_match.group(9).strip() if update_match.group(9) else None
        if task_name not in tasks:
            return f"Task '{task_name}' not found in your to-do list."
        if deadline:
            tasks[task_name]["deadline"] = deadline
        if priority:
            tasks[task_name]["priority"] = priority
        if category:
            tasks[task_name]["category"] = category
        if recurring:
            tasks[task_name]["recurring"] = recurring
        msg = f"Updated '{task_name}'."
        if deadline:
            msg += f" New deadline: {deadline}."
        if priority:
            msg += f" New priority: {priority}."
        if category:
            msg += f" New category: {category}."
        if recurring:
            msg += f" New recurrence: {recurring}."
        return msg
    if "remove task" in text or "delete task" in text:
        # Extract task name after 'remove task' or 'delete task'
        if "remove task" in text:
            task_name = text.split("remove task", 1)[-1].strip()
        else:
            task_name = text.split("delete task", 1)[-1].strip()
        if not task_name:
            return "Please specify the task to remove."
        if task_name not in tasks:
            return f"Task '{task_name}' not found in your to-do list."
        # Ask for confirmation
        speak(f"Are you sure you want to remove '{task_name}'? Say 'yes' to confirm or 'no' to cancel.")
        confirmation = listen()
        if confirmation and "yes" in confirmation.lower():
            del tasks[task_name]
            return f"Removed '{task_name}' from your to-do list."
        else:
            return f"Cancelled removing '{task_name}'."
    if "list tasks" in text or "show tasks" in text:
        if not tasks:
            return "Your to-do list is empty."
        response = "Here are your tasks:\n"
        for task, info in tasks.items():
            status = "done" if info["done"] else "not done"
            deadline = f", deadline: {info.get('deadline')}" if info.get("deadline") else ""
            priority = f", priority: {info.get('priority')}" if info.get("priority") else ""
            category = f", category: {info.get('category')}" if info.get("category") else ""
            recurring = f", recurring: {info.get('recurring')}" if info.get("recurring") else ""
            # Highlight overdue and due-soon tasks
            highlight = ""
            if info.get('deadline'):
                try:
                    due_date = datetime.datetime.strptime(info['deadline'], '%Y-%m-%d').date()
                    today = datetime.datetime.now().date()
                    soon = today + datetime.timedelta(days=1)
                    if not info["done"] and due_date < today:
                        highlight = " [OVERDUE]"
                    elif not info["done"] and today <= due_date <= soon:
                        highlight = " [DUE SOON]"
                except Exception:
                    pass
            response += f"- {task} [{status}{deadline}{priority}{category}{recurring}]{highlight}\n"
        return response.strip()
    if "edit task" in text or "rename task" in text:
        # Extract old and new task names
        if "edit task" in text:
            parts = text.split("edit task", 1)[-1].strip().split(" to ")
        else:
            parts = text.split("rename task", 1)[-1].strip().split(" to ")
        if len(parts) != 2:
            return "Please specify the old and new task names, like 'edit task old name to new name'."
        old_name, new_name = parts[0].strip(), parts[1].strip()
        if not old_name or not new_name:
            return "Both old and new task names are required."
        if old_name not in tasks:
            return f"Task '{old_name}' not found in your to-do list."
        if new_name in tasks:
            return f"Task '{new_name}' already exists in your to-do list."
        # Ask for confirmation
        speak(f"Are you sure you want to rename '{old_name}' to '{new_name}'? Say 'yes' to confirm or 'no' to cancel.")
        confirmation = listen()
        if confirmation and "yes" in confirmation.lower():
            tasks[new_name] = tasks.pop(old_name)
            return f"Renamed '{old_name}' to '{new_name}'."
        else:
            return f"Cancelled renaming '{old_name}'."
    # Timetable: add entry (accepts 'timetable' or 'time table')
    add_tt = re.match(r"add (timetable|time table) (.+?) (\d{1,2}(am|pm)) (.+)", text)
    if add_tt:
        day = add_tt.group(2).strip().capitalize()
        time = add_tt.group(3)
        activity = add_tt.group(5).strip().lower()
        timetable = load_timetable(tasks)
        timetable.append({"day": day, "time": time, "activity": activity})
        save_timetable(tasks, timetable)
        return f"Added to timetable: {day} {time} - {activity}."
    # Timetable: show all
    if "show timetable" in text or "list timetable" in text or "show time table" in text or "list time table" in text:
        timetable = load_timetable(tasks)
        if not timetable:
            return "Your timetable is empty."
        response = "Your timetable:\n"
        for entry in timetable:
            response += f"- {entry['day']} {entry['time']}: {entry['activity']}\n"
        return response.strip()
    # Timetable: update entry
    update_tt = re.match(r"update (timetable|time table) (.+?) (\d{1,2}(am|pm)) (.+)", text)
    if update_tt:
        day = update_tt.group(2).strip().capitalize()
        time = update_tt.group(3)
        activity = update_tt.group(5).strip().lower()
        timetable = load_timetable(tasks)
        updated = False
        for entry in timetable:
            if entry["day"] == day and entry["time"] == time:
                entry["activity"] = activity
                updated = True
        if updated:
            save_timetable(tasks, timetable)
            return f"Updated timetable: {day} {time} - {activity}."
        else:
            return f"No timetable entry found for {day} {time}."
    # Timetable: remove entry
    remove_tt = re.match(r"remove (timetable|time table) (.+?) (\d{1,2}(am|pm))", text)
    if remove_tt:
        day = remove_tt.group(2).strip().capitalize()
        time = remove_tt.group(3)
        timetable = load_timetable(tasks)
        new_tt = [e for e in timetable if not (e["day"] == day and e["time"] == time)]
        if len(new_tt) != len(timetable):
            save_timetable(tasks, new_tt)
            return f"Removed timetable entry for {day} {time}."
        else:
            return f"No timetable entry found for {day} {time}."
    for task, info in tasks.items():
        if task in text:
            if "completed" in text or "finished" in text or "done" in text:
                info["done"] = True
                speak(f"Marked '{task}' as done.", voice_gender="female")
                return None  # Already spoken
            elif "not completed" in text or "didn't" in text or "not done" in text:
                info["done"] = False
                speak(f"You didn’t complete '{task}' today.", voice_gender="female")
                return None  # Already spoken
    return "Sorry, I didn't find that task in your list. You can say 'add task' to add a new one."

def monitor_timetable(tasks):
    speak("Timetable monitoring started. Say 'stop' or 'exit' to end.")
    notified = set()
    while True:
        now = datetime.datetime.now()
        day = now.strftime('%A').lower()
        hour = now.strftime('%I').lstrip('0')
        ampm = now.strftime('%p').lower()
        current_time = f"{hour}{ampm}"
        timetable = load_timetable(tasks)
        for entry in timetable:
            if entry['day'].lower() == day and entry['time'].lower() == current_time:
                key = (entry['day'], entry['time'], entry['activity'])
                if key not in notified:
                    speak(f"It's time for {entry['activity']}!")
                    notified.add(key)
        # Listen for stop/exit command (non-blocking)
        print("Say 'stop' or 'exit' to end monitoring, or wait for the next alert.")
        for _ in range(12):  # Check every 5 seconds for 1 minute
            user_input = listen()
            if user_input:
                if 'stop' in user_input.lower() or 'exit' in user_input.lower():
                    speak("Timetable monitoring stopped.")
                    return
            time.sleep(5)

def reset_recurring_tasks(tasks):
    now = datetime.datetime.now()
    today = now.strftime('%A').lower()
    week = now.isocalendar()[1]
    for task, info in tasks.items():
        if not isinstance(info, dict):
            continue
        recurring = info.get('recurring')
        if recurring == 'daily':
            last_reset = info.get('last_reset')
            current_date = now.strftime('%Y-%m-%d')
            if last_reset != current_date:
                info['done'] = False
                info['last_reset'] = current_date
        elif recurring == 'weekly':
            last_reset = info.get('last_reset_week')
            if last_reset != week:
                info['done'] = False
                info['last_reset_week'] = week

def check_deadlines(tasks):
    now = datetime.datetime.now()
    today = now.date()
    soon = today + datetime.timedelta(days=1)
    reminders = []
    overdue = []
    for task, info in tasks.items():
        if not isinstance(info, dict):
            continue
        deadline = info.get('deadline')
        done = info.get('done')
        if deadline:
            try:
                due_date = datetime.datetime.strptime(deadline, '%Y-%m-%d').date()
                if not done and due_date < today:
                    overdue.append(task)
                elif not done and today <= due_date <= soon:
                    reminders.append((task, due_date))
            except Exception:
                continue
    return reminders, overdue

# === Listen to Microphone ===
def listen():
    try:
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            print("🎤 Listening...")
            recognizer.adjust_for_ambient_noise(source)
            audio = recognizer.listen(source)
        try:
            print("🧠 Recognizing...")
            return recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            return None
        except sr.RequestError:
            speak("API unavailable. Check your internet connection.")
            return None
    except Exception as e:
        speak(f"Microphone or audio error: {e}")
        return None

def launch_gui():
    def refresh_tasks():
        tasks = load_tasks()
        for i in tree_tasks.get_children():
            tree_tasks.delete(i)
        for task, info in tasks.items():
            if not isinstance(info, dict):
                continue
            tree_tasks.insert('', 'end', iid=task, values=(task, info.get('done'), info.get('deadline'), info.get('priority'), info.get('category'), info.get('recurring')))

    def refresh_timetable():
        tasks = load_tasks()
        timetable = load_timetable(tasks)
        for i in tree_tt.get_children():
            tree_tt.delete(i)
        for entry in timetable:
            tree_tt.insert('', 'end', values=(entry['day'], entry['time'], entry['activity']))

    def refresh_all():
        refresh_tasks()
        refresh_timetable()

    def add_task():
        task_name = simpledialog.askstring("Add Task", "Task name:")
        if not task_name:
            return
        tasks = load_tasks()
        if task_name in tasks:
            messagebox.showerror("Error", "Task already exists.")
            return
        tasks[task_name] = {"done": False, "deadline": None, "priority": None, "category": None, "recurring": None}
        save_tasks(tasks)
        refresh_tasks()

    def mark_done():
        selected = tree_tasks.selection()
        if not selected:
            return
        tasks = load_tasks()
        for task in selected:
            if task in tasks:
                tasks[task]["done"] = True
        save_tasks(tasks)
        refresh_tasks()

    def delete_task():
        selected = tree_tasks.selection()
        if not selected:
            return
        tasks = load_tasks()
        for task in selected:
            if task in tasks:
                del tasks[task]
        save_tasks(tasks)
        refresh_tasks()

    def add_tt():
        day = simpledialog.askstring("Add Timetable Entry", "Day (e.g., Monday):")
        time_ = simpledialog.askstring("Add Timetable Entry", "Time (e.g., 7pm):")
        activity = simpledialog.askstring("Add Timetable Entry", "Activity:")
        if not (day and time_ and activity):
            return
        tasks = load_tasks()
        timetable = load_timetable(tasks)
        timetable.append({"day": day, "time": time_, "activity": activity})
        save_timetable(tasks, timetable)
        save_tasks(tasks)
        refresh_timetable()

    def delete_tt():
        selected = tree_tt.selection()
        if not selected:
            return
        tasks = load_tasks()
        timetable = load_timetable(tasks)
        for item in selected:
            vals = tree_tt.item(item, 'values')
            timetable = [e for e in timetable if not (e['day'] == vals[0] and e['time'] == vals[1] and e['activity'] == vals[2])]
        save_timetable(tasks, timetable)
        save_tasks(tasks)
        refresh_timetable()

    def voice_command():
        status_var.set("Listening for command...")
        root.update()
        user_input = listen()
        if user_input is None:
            status_var.set("Sorry, I didn't catch that. Please try again.")
            return
        status_var.set(f"You said: {user_input}")
        tasks = load_tasks()
        # Check for update/refresh GUI intent
        if any(word in user_input.lower() for word in ["update the gui", "refresh the gui", "reload the gui"]):
            refresh_all()
            status_var.set("GUI updated with latest data.")
            return
        response = process_input(user_input, tasks)
        if response is not None:
            speak(response)
            status_var.set(f"Assistant: {response}")
        save_tasks(tasks)
        refresh_all()

    root = tk.Tk()
    root.title("Placement Prep Assistant - GUI")

    # Tasks Frame
    frame_tasks = ttk.LabelFrame(root, text="Tasks")
    frame_tasks.pack(fill='both', expand=True, padx=10, pady=5)
    tree_tasks = ttk.Treeview(frame_tasks, columns=("Task", "Done", "Deadline", "Priority", "Category", "Recurring"), show='headings')
    for col in ("Task", "Done", "Deadline", "Priority", "Category", "Recurring"):
        tree_tasks.heading(col, text=col)
        tree_tasks.column(col, width=100)
    tree_tasks.pack(fill='both', expand=True, side='left')
    btn_frame = ttk.Frame(frame_tasks)
    btn_frame.pack(side='right', fill='y')
    ttk.Button(btn_frame, text="Add Task", command=add_task).pack(fill='x', pady=2)
    ttk.Button(btn_frame, text="Mark Done", command=mark_done).pack(fill='x', pady=2)
    ttk.Button(btn_frame, text="Delete Task", command=delete_task).pack(fill='x', pady=2)

    # Timetable Frame
    frame_tt = ttk.LabelFrame(root, text="Timetable")
    frame_tt.pack(fill='both', expand=True, padx=10, pady=5)
    tree_tt = ttk.Treeview(frame_tt, columns=("Day", "Time", "Activity"), show='headings')
    for col in ("Day", "Time", "Activity"):
        tree_tt.heading(col, text=col)
        tree_tt.column(col, width=100)
    tree_tt.pack(fill='both', expand=True, side='left')
    btn_tt_frame = ttk.Frame(frame_tt)
    btn_tt_frame.pack(side='right', fill='y')
    ttk.Button(btn_tt_frame, text="Add Entry", command=add_tt).pack(fill='x', pady=2)
    ttk.Button(btn_tt_frame, text="Delete Entry", command=delete_tt).pack(fill='x', pady=2)

    # Voice Command Button and Status
    status_var = tk.StringVar()
    status_var.set("")
    status_label = ttk.Label(root, textvariable=status_var, foreground="blue")
    status_label.pack(fill='x', padx=10, pady=5)
    ttk.Button(root, text="Voice Command", command=voice_command).pack(fill='x', padx=10, pady=5)

    refresh_tasks()
    refresh_timetable()
    root.mainloop()

# === Main Loop ===
def main():
    try:
        tasks = load_tasks()
    except Exception as e:
        speak(f"Error loading tasks: {e}")
        tasks = {}
    reset_recurring_tasks(tasks)
    reminders, overdue = check_deadlines(tasks)
    if overdue:
        speak(f"You have overdue tasks: {', '.join(overdue)}.")
    if reminders:
        soon_tasks = ', '.join([f"{t} (due {d})" for t, d in reminders])
        speak(f"Upcoming deadlines: {soon_tasks}.")
    speak("Welcome to your voice to-do assistant.")

    while True:
        speak("Say 'add task buy groceries', 'list tasks', 'add timetable monday 7pm aptitude practice', 'run' to start monitoring, or 'exit' to quit.")
        user_input = listen()

        if user_input is None:
            speak("Sorry, I didn't catch that. Please repeat.")
            continue

        print(f"You said: {user_input}")
        
        if "exit" in user_input.lower():
            speak("Goodbye!")
            break
        if "run" == user_input.strip().lower():
            reset_recurring_tasks(tasks)
            reminders, overdue = check_deadlines(tasks)
            if overdue:
                speak(f"You have overdue tasks: {', '.join(overdue)}.")
            if reminders:
                soon_tasks = ', '.join([f"{t} (due {d})" for t, d in reminders])
                speak(f"Upcoming deadlines: {soon_tasks}.")
            monitor_timetable(tasks)
            continue

        response = process_input(user_input, tasks)
        if response is not None:
            speak(response)
        try:
            save_tasks(tasks)
        except Exception as e:
            speak(f"Error saving tasks: {e}")

if __name__ == "__main__":
    try:
        import speech_recognition
        import pyttsx3
    except ImportError as e:
        print(f"Missing dependency: {e}. Please install all required packages in requirements.txt.")
        sys.exit(1)
    # Start GUI in a separate thread
    gui_thread = threading.Thread(target=launch_gui, daemon=True)
    gui_thread.start()
    main()
