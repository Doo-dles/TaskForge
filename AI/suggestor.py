from sklearn.cluster import KMeans
import pandas as pd
from datetime import datetime, timedelta
from sklearn.preprocessing import LabelEncoder

def suggest_task_with_ml(user_id, cursor, top_n=3):
    cursor.execute("SELECT description, category, priority, due_datetime FROM tasks WHERE user_id = %s", (user_id,))
    tasks = cursor.fetchall()

    if not tasks:
        return ["No previous tasks to suggest."]

    df = pd.DataFrame(tasks)
    df = df.dropna(subset=['due_datetime'])
    df['due_datetime'] = pd.to_datetime(df['due_datetime'], errors='coerce')
    df = df.dropna(subset=['due_datetime'])

    # Extract features
    df['hour'] = df['due_datetime'].dt.hour

    # Encode categorical variables
    le_cat = LabelEncoder()
    le_pri = LabelEncoder()

    df['category_enc'] = le_cat.fit_transform(df['category'])
    df['priority_enc'] = le_pri.fit_transform(df['priority'])

    X = df[['category_enc', 'priority_enc', 'hour']]

    # Apply KMeans clustering
    kmeans = KMeans(n_clusters=min(top_n, len(df)), random_state=42)
    df['cluster'] = kmeans.fit_predict(X)

    now = datetime.now()
    suggestions = []

    # Loop over each cluster to build suggestions
    for cluster in df['cluster'].unique():
        cluster_df = df[df['cluster'] == cluster]
        common_cat = cluster_df['category'].mode()[0]
        common_pri = cluster_df['priority'].mode()[0]
        common_hour = cluster_df['hour'].mode()[0]

        # Convert to 12-hour format
        hour_12 = common_hour % 12
        hour_12 = 12 if hour_12 == 0 else hour_12
        am_pm = "AM" if common_hour < 12 else "PM"
        time_str = f"{hour_12} {am_pm}"

        # Calculate suggested due_datetime (today or tomorrow)
        suggested_due = now.replace(hour=common_hour, minute=0, second=0, microsecond=0)
        if suggested_due < now:
            suggested_due += timedelta(days=1)

        # Build display text
        display_text = (f"You often schedule '{common_cat}' tasks "
                        f"with priority '{common_pri}' around {time_str}. Consider adding similar tasks!")

        # Clean description for adding new task (you can customize)
        clean_description = f"{common_cat} task"

        suggestions.append({
            "category": common_cat,
            "priority": common_pri,
            "time_str": time_str,
            "display_text": display_text,
            "description": clean_description,
            "due_datetime": suggested_due.strftime("%Y-%m-%d %H:%M:%S")
        })

    return suggestions
